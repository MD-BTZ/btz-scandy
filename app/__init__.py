from flask import Flask, jsonify, render_template, redirect, url_for, g, send_from_directory, session, request, flash
from flask_session import Session  # Session-Management
from .constants import Routes
import os
from datetime import datetime, timedelta
from app.utils.filters import register_filters
import logging
from app.models.database import Database
from app.utils.error_handler import handle_errors
from app.utils.db_schema import SchemaManager
from app.utils.color_settings import get_color_settings
from flask_compress import Compress
from app.models.settings import Settings
from app.utils.auth_utils import needs_setup
from app.models.init_db import init_users as init_database_users
from pathlib import Path
import sys
from flask_login import LoginManager
from app.models.user import User
from app.models.init_ticket_db import init_ticket_db
from app.utils.context_processors import register_context_processors

# Backup-System importieren
sys.path.append(str(Path(__file__).parent.parent))
from backup import DatabaseBackup

# Logger einrichten
logger = logging.getLogger(__name__)

login_manager = LoginManager()

__version__ = '1.0.1'

class Config:
    @staticmethod
    def init_server():
        pass

    @staticmethod
    def init_client(server_url=None):
        pass

    @staticmethod
    def is_pythonanywhere():
        # This is a placeholder implementation. You might want to implement a more robust check for PythonAnywhere
        return False

def ensure_directories_exist():
    """Stellt sicher, dass alle benötigten Verzeichnisse existieren"""
    from app.config import config
    current_config = config['default']()
    
    # Liste der zu erstellenden Verzeichnisse
    directories = [
        os.path.dirname(current_config.DATABASE),
        current_config.BACKUP_DIR,
        current_config.UPLOAD_FOLDER
    ]
    
    # Verzeichnisse erstellen
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Verzeichnis erstellt: {directory}")
        else:
            logging.info(f"Verzeichnis existiert bereits: {directory}")

def cleanup_database():
    """Bereinigt die Datenbank von ungültigen Einträgen"""
    try:
        logger.info("Führe automatische Datenbankbereinigung durch...")
        with Database.get_db() as db:
            # Finde und lösche Ausleihungen für nicht existierende Werkzeuge
            invalid_lendings = db.execute('''
                SELECT l.*, t.barcode as tool_exists
                FROM lendings l
                LEFT JOIN tools t ON l.tool_barcode = t.barcode
                WHERE t.barcode IS NULL
                AND l.returned_at IS NULL
            ''').fetchall()
            
            if invalid_lendings:
                logger.info(f"Gefundene ungültige Ausleihungen: {len(invalid_lendings)}")
                for lending in invalid_lendings:
                    logger.info(f"Ungültige Ausleihe gefunden: {dict(lending)}")
                
                db.execute('''
                    DELETE FROM lendings
                    WHERE id IN (
                        SELECT l.id
                        FROM lendings l
                        LEFT JOIN tools t ON l.tool_barcode = t.barcode
                        WHERE t.barcode IS NULL
                        AND l.returned_at IS NULL
                    )
                ''')
                db.commit()
                logger.info(f"{len(invalid_lendings)} ungültige Ausleihungen wurden gelöscht")
    except Exception as e:
        logger.error(f"Fehler bei der automatischen Datenbankbereinigung: {str(e)}")

def init_databases():
    """Initialisiert alle Datenbanken und stellt sicher, dass sie die korrekte Struktur haben"""
    try:
        logger.info("Initialisiere Datenbanken...")
        
        # Hauptdatenbank initialisieren
        logger.info("Initialisiere Hauptdatenbank...")
        from app.models.init_db import init_db
        init_db()
        init_database_users()
        
        # Ticket-Datenbank initialisieren
        logger.info("Initialisiere Ticket-Datenbank...")
        init_ticket_db()
        
        logger.info("Datenbanken erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankinitialisierung: {str(e)}")
        raise

def create_app(test_config=None):
    """Erstellt und konfiguriert die Flask-Anwendung"""
    app = Flask(__name__)
    
    # Konfiguration laden
    from app.config import config
    config_name = 'default' if test_config is None else test_config
    app.config.from_object(config[config_name])
    
    # Logger einrichten
    from app.utils.logger import init_app_logger
    init_app_logger(app)
    app.logger.info("\n=== ANWENDUNGSSTART ===")
    
    # Verzeichnisse erstellen
    ensure_directories_exist()
    
    # Datenbanken initialisieren
    init_databases()
    
    # Context Processors registrieren
    register_context_processors(app)
    
    # Blueprints registrieren
    from app.routes import (
        main, auth, admin, tools, workers, 
        consumables, lending, dashboard, history, 
        quick_scan, api, tickets
    )
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(tools.bp)
    app.register_blueprint(workers.bp)
    app.register_blueprint(consumables.bp)
    app.register_blueprint(lending.bp, url_prefix='/lending')
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(history.bp)
    app.register_blueprint(quick_scan.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(tickets.bp, url_prefix='/tickets')
    
    # Fehlerbehandlung registrieren
    handle_errors(app)
    
    # Filter registrieren
    register_filters(app)
    
    # Komprimierung aktivieren
    Compress(app)
    
    # Wenn auf Render, lade Demo-Daten
    if os.environ.get('RENDER') == 'true':
        with app.app_context():
            demo_data_lock = os.path.join(app.instance_path, 'demo_data.lock')
            if not os.path.exists(demo_data_lock):
                # Lösche vorhandene Benutzer
                with Database.get_db() as db:
                    db.execute("DELETE FROM users")
                    db.commit()
                    print("Vorhandene Benutzer gelöscht")
                
                # Erstelle Admin-Benutzer
                from app.models.init_db import init_users
                if init_users(app, 'admin'):
                    print("Admin-Benutzer für Render erstellt (admin/admin)")
                
                # Demo-Daten laden
                from app.models.demo_data import load_demo_data
                load_demo_data()
                print("Demo-Daten wurden geladen")
                
                # Erstelle Lock-Datei
                os.makedirs(app.instance_path, exist_ok=True)
                with open(demo_data_lock, 'w') as f:
                    f.write('1')
            else:
                # Versuche das letzte Backup wiederherzustellen
                backup = DatabaseBackup(app_path=Path(__file__).parent.parent)
                latest_backup = "inventory_20250110_190000.db"
                if backup.restore_backup(latest_backup):
                    print(f"Backup {latest_backup} erfolgreich wiederhergestellt")
                else:
                    print("Konnte Backup nicht wiederherstellen, initialisiere neue Datenbank")
    
    # Login-Manager initialisieren
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)
    
    return app