from flask import Flask, jsonify, render_template, redirect, url_for, g, send_from_directory, session, request, flash
from flask_session import Session  # Session-Management
from .constants import Routes
from app.config.version import VERSION
import os
from datetime import datetime, timedelta
from app.utils.filters import register_filters
import logging
from app.models.database import Database
from app.utils.error_handler import handle_errors
from app.utils.db_schema import SchemaManager
from flask_compress import Compress
from app.models.settings import Settings
from app.utils.auth_utils import needs_setup
from app.models.init_db import init_db
from pathlib import Path
import sys
from flask_login import LoginManager
from app.models.user import User
from app.models.init_ticket_db import init_ticket_db
from app.utils.context_processors import register_context_processors
from app.routes import auth, tools, consumables, workers, setup, backup
from app.config import Config
from app.routes import init_app
import sqlite3

# Backup-System importieren
sys.path.append(str(Path(__file__).parent.parent))
from backup import DatabaseBackup

# Logger einrichten
logger = logging.getLogger(__name__)

# Backup-Manager initialisieren
backup_manager = DatabaseBackup(str(Path(__file__).parent.parent))

# Backup-Verzeichnisse erstellen
backup_dir = Path(__file__).parent.parent / 'backups'
backup_dir.mkdir(exist_ok=True)

login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = 'auth.login'
login_manager.login_message = "Bitte melden Sie sich an, um auf diese Seite zuzugreifen."
login_manager.login_message_category = "info"

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
    project_root = Path(current_config.DATABASE).parent.parent # Annahme: DB ist in app/database/

    # Liste der zu erstellenden Verzeichnisse
    directories = [
        os.path.dirname(current_config.DATABASE),
        current_config.BACKUP_DIR,
        current_config.UPLOAD_FOLDER,
        project_root / 'tmp' # Hinzugefügt
    ]
    
    # Verzeichnisse erstellen
    for directory in directories:
        dir_path = Path(directory) # Sicherstellen, dass es ein Path-Objekt ist
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True) # parents=True hinzugefügt
            logging.info(f"Verzeichnis erstellt: {dir_path}")
        else:
            logging.info(f"Verzeichnis existiert bereits: {dir_path}")

def cleanup_database():
    """Führt regelmäßige Wartungsaufgaben für die Datenbank durch"""
    try:
        # Konfiguration laden
        from app.config import config
        current_config = config['default']
        
        db_path = os.path.join(current_config.BASE_DIR, 'app', 'database', 'inventory.db')
        
        # Führe Bereinigungen in einer Transaktion durch
        with sqlite3.connect(db_path) as db:
            cursor = db.cursor()
            
            # Lösche ungültige Ausleihen
            cursor.execute('''
                DELETE FROM lendings 
                WHERE tool_barcode NOT IN (SELECT barcode FROM tools WHERE deleted = 0)
                OR worker_barcode NOT IN (SELECT barcode FROM workers WHERE deleted = 0)
            ''')
            
            # Lösche verwaiste Verbrauchsmaterial-Einträge
            cursor.execute('''
                DELETE FROM consumable_usages 
                WHERE consumable_barcode NOT IN (SELECT barcode FROM consumables WHERE deleted = 0)
                OR worker_barcode NOT IN (SELECT barcode FROM workers WHERE deleted = 0)
            ''')
            
            # Lösche alte gelöschte Einträge
            cursor.execute('''
                DELETE FROM tools 
                WHERE deleted = 1 AND deleted_at < datetime('now', '-1 year')
            ''')
            
            cursor.execute('''
                DELETE FROM workers 
                WHERE deleted = 1 AND deleted_at < datetime('now', '-1 year')
            ''')
            
            cursor.execute('''
                DELETE FROM consumables 
                WHERE deleted = 1 AND deleted_at < datetime('now', '-1 year')
            ''')
            
            db.commit()
            logger.info("Datenbankbereinigung erfolgreich durchgeführt")
        
        # Führe VACUUM außerhalb der Transaktion durch
        with sqlite3.connect(db_path) as db:
            cursor = db.cursor()
            cursor.execute('VACUUM')
            logger.info("Datenbank-VACUUM erfolgreich durchgeführt")
            
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankbereinigung: {str(e)}")
        if 'db' in locals():
            db.rollback()

def initialize_and_migrate_databases():
    """Initialisiert die Datenbanken nur beim ersten Start"""
    try:
        # Konfiguration laden
        from app.config import config
        current_config = config['default']
        
        # Definiere Datenbankpfade
        inventory_db_path = os.path.join(current_config.BASE_DIR, 'app', 'database', 'inventory.db')
        tickets_db_path = os.path.join(current_config.BASE_DIR, 'app', 'database', 'tickets.db')
        
        # Stelle sicher, dass die Verzeichnisse existieren
        os.makedirs(os.path.dirname(inventory_db_path), exist_ok=True)
        os.makedirs(os.path.dirname(tickets_db_path), exist_ok=True)
        
        # Initialisiere Hauptdatenbank
        logger.info("Initialisiere Hauptdatenbank...")
        schema_manager = SchemaManager(inventory_db_path)
        if not schema_manager.initialize():
            logger.error("Fehler bei der Initialisierung der Hauptdatenbank")
            return False
        logger.info("Hauptdatenbank erfolgreich initialisiert")
        
        # Initialisiere Ticket-Datenbank
        logger.info("Initialisiere Ticket-Datenbank...")
        from app.models.init_ticket_db import init_ticket_db
        init_ticket_db()
        logger.info("Ticket-Datenbank erfolgreich initialisiert")
        
        return True
        
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankinitialisierung: {str(e)}")
        return False

def create_app(test_config=None):
    """Erstellt und konfiguriert die Flask-Anwendung"""
    app = Flask(__name__)
    
    # Konfiguration laden
    from app.config import config
    config_name = 'default' if test_config is None else test_config
    app.config.from_object(config[config_name])
    
    # Systemnamen direkt setzen
    app.config['SYSTEM_NAME'] = os.environ.get('SYSTEM_NAME') or 'Scandy'
    app.config['TICKET_SYSTEM_NAME'] = os.environ.get('TICKET_SYSTEM_NAME') or 'Aufgaben'
    app.config['TOOL_SYSTEM_NAME'] = os.environ.get('TOOL_SYSTEM_NAME') or 'Werkzeuge'
    app.config['CONSUMABLE_SYSTEM_NAME'] = os.environ.get('CONSUMABLE_SYSTEM_NAME') or 'Verbrauchsgüter'
    
    # Logger einrichten
    from app.utils.logger import init_app_logger
    init_app_logger(app)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("\n=== ANWENDUNGSSTART ===")
    
    # Verzeichnisse erstellen
    ensure_directories_exist()
    
    # Datenbanken nur einmal beim Start initialisieren
    if not hasattr(app, '_database_initialized'):
        initialize_and_migrate_databases()
        app._database_initialized = True
    
    # Flask-Login initialisieren
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)
    
    # Context Processors registrieren
    register_context_processors(app)
    
    # Context Processor für Systemnamen
    @app.context_processor
    def inject_system_names():
        return {
            'system_name': app.config['SYSTEM_NAME'],
            'ticket_system_name': app.config['TICKET_SYSTEM_NAME'],
            'tool_system_name': app.config['TOOL_SYSTEM_NAME'],
            'consumable_system_name': app.config['CONSUMABLE_SYSTEM_NAME']
        }
    
    # Blueprints registrieren
    from app.routes import (
        main, auth, admin, tools, workers, 
        consumables, lending, dashboard, history, 
        quick_scan, api, tickets, setup, backup
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
    app.register_blueprint(setup.bp)
    app.register_blueprint(backup.bp)
    
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
    
    # Context Processor für Template-Variablen
    @app.context_processor
    def utility_processor():
        return {
            'status_colors': {
                'offen': 'danger',
                'in_bearbeitung': 'warning',
                'wartet_auf_antwort': 'info',
                'gelöst': 'success',
                'geschlossen': 'secondary'
            },
            'priority_colors': {
                'niedrig': 'info',
                'normal': 'primary',
                'hoch': 'warning',
                'kritisch': 'error'
            }
        }

    return app