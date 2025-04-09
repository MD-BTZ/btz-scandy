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

# Backup-System importieren
sys.path.append(str(Path(__file__).parent.parent))
from backup import DatabaseBackup

# Logger einrichten
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

login_manager = LoginManager()

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

def create_app(test_config=None):
    """Erstellt und konfiguriert die Flask-Anwendung"""
    app = Flask(__name__, 
                static_folder='static',
                static_url_path='/static')
    
    # Basis-Konfiguration
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key-123'),
        SESSION_TYPE='filesystem'
    )
    
    # Session-Konfiguration
    Session(app)
    
    # Konfiguration laden
    if test_config is None:
        app.config.from_object(Config())
    else:
        app.config.update(test_config)
    
    # Logger einrichten
    from app.utils.logger import init_app_logger
    init_app_logger(app)
    app.logger.info("\n=== ANWENDUNGSSTART ===")
    
    # Verzeichnisse erstellen falls nicht vorhanden
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.instance_path, 'uploads'), exist_ok=True)
    
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
    
    # Stelle sicher, dass alle Verzeichnisse existieren
    ensure_directories_exist()
    
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
    
    # Datenbank initialisieren
    with app.app_context():
        # Stelle sicher, dass die Datenbank existiert
        app.logger.info("\n=== DATENBANK-INITIALISIERUNG ===")
        if not Database.ensure_db_exists():
            app.logger.error("Datenbank konnte nicht initialisiert werden")
            raise Exception("Datenbank-Initialisierung fehlgeschlagen")
        
        # Zeige Datenbankinhalt
        app.logger.info("\n=== AKTUELLER DATENBANKINHALT ===")
        Database.print_database_contents()
        
        # Benutzer initialisieren
        init_database_users(app)
        
        # Automatische Datenbankbereinigung durchführen
        cleanup_database()
    
    # Login-Manager initialisieren
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)
    
    return app