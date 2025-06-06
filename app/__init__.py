from flask import Flask, redirect, url_for, session, request, current_app, g
from flask_login import current_user
from flask_session import Session
from flask_compress import Compress
from flask_login import LoginManager
from pathlib import Path
import os
import sys
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Local imports
from app.config import Config
from app.models import Database, BaseModel, Tool, Worker
from app.models.user import User
from app.models.settings import Settings
from app.models.init_db import init_db
from app.models.init_ticket_db import init_ticket_db
from app.models.ticket_migrations import run_migrations
from app.utils.error_handler import handle_errors
from app.utils.filters import register_filters
from app.utils.db_schema import SchemaManager
from app.utils.auth_utils import needs_setup
from app.utils.context_processors import register_context_processors
from app.utils.auto_migrate import auto_migrate_and_check
from app.utils.schema_validator import validate_and_migrate_databases
from app.routes import init_app

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

# Initialize Flask extensions
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = 'auth.login'
login_manager.login_message = "Bitte melden Sie sich an, um auf diese Seite zuzugreifen."
login_manager.login_message_category = "info"

# Initialize other extensions
db = Database.get_instance()

# Configuration is now in app/config.py

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
        os.path.join(current_config.BASE_DIR, 'app', 'tmp') # tmp-Verzeichnis explizit
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
        
        # Initialisiere und migriere beide Datenbanken
        logger.info("Initialisiere und migriere Datenbanken...")
        from app.models.ticket_migrations import run_migrations
        
        # Initialisiere Hauptdatenbank
        if not run_migrations(inventory_db_path):
            logger.error("Fehler bei der Initialisierung der Hauptdatenbank")
            return False
        logger.info("Hauptdatenbank erfolgreich initialisiert")
        
        # Initialisiere Ticket-Datenbank
        if not run_migrations(tickets_db_path):
            logger.error("Fehler bei der Initialisierung der Ticket-Datenbank")
            return False
        logger.info("Ticket-Datenbank erfolgreich initialisiert")
        
        return True
        
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankinitialisierung: {str(e)}")
        return False

def create_app(test_config=None, db_path: Optional[str] = None):
    """Erstellt und konfiguriert die Flask-Anwendung
    
    Args:
        test_config: Konfiguration für Tests
        db_path: Optionaler Pfad zur Datenbankdatei
    """
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
    
    # Datenbankpfad konfigurieren
    if db_path is None:
        db_path = os.path.join(app.config['BASE_DIR'], 'app', 'database', 'inventory.db')
    
    # Datenbank initialisieren
    db = Database.get_instance(db_path=db_path)
    
    # TEMP_FOLDER setzen
    app.config['TEMP_FOLDER'] = os.path.join(app.config['BASE_DIR'], 'app', 'tmp')
    
    # Logger einrichten
    from app.utils.logger import init_app_logger
    init_app_logger(app)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("\n=== ANWENDUNGSSTART ===")
    
    # Verzeichnisse erstellen
    ensure_directories_exist()
    
    # Datenbanken nur einmal beim Start initialisieren
    if not hasattr(app, '_database_initialized'):
        try:
            # Migrations durchführen
            from migrations.apply_migration import main as run_migrations
            if run_migrations() != 0:
                logging.error("Fehler bei der Datenbankmigration. Bitte überprüfen Sie die Logs.")
            
            # Alte Initialisierung für Abwärtskompatibilität
            if not initialize_and_migrate_databases():
                logging.warning("Alte Datenbankinitialisierung fehlgeschlagen. Fortfahren mit neuer Struktur.")
            
            app._database_initialized = True
        except Exception as e:
            logging.error(f"Fehler bei der Datenbankinitialisierung: {str(e)}")
            raise
    
    # Flask-Login initialisieren
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        # Verwende das neue User-Modell mit der Basisklasse
        return User.get_by_id(user_id)
    
    # Context Processors registrieren
    register_context_processors(app)
    
    # Context Processor für Systemnamen und Datenbank
    @app.context_processor
    def inject_globals():
        """Fügt globale Variablen zu allen Templates hinzu"""
        return {
            'system_name': app.config['SYSTEM_NAME'],
            'ticket_system_name': app.config['TICKET_SYSTEM_NAME'],
            'tool_system_name': app.config['TOOL_SYSTEM_NAME'],
            'consumable_system_name': app.config['CONSUMABLE_SYSTEM_NAME'],
            'db': db  # Füge die Datenbankinstanz zu den Templates hinzu
        }
    
    # Blueprints registrieren
    from app.routes import (
        main, auth, admin, tools, workers, 
        consumables, lending, dashboard, history, 
        quick_scan, api, tickets, setup, backup, applications, profile
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
    app.register_blueprint(applications.bp)
    app.register_blueprint(profile.bp)
    
    # Fehlerbehandlung registrieren
    handle_errors(app)
    
    # Filter registrieren
    register_filters(app)
    
    # Komprimierung aktivieren
    Compress(app)
    
    # Demo-Daten laden, wenn gewünscht
    if os.environ.get('LOAD_DEMO_DATA', 'false').lower() == 'true':
        with app.app_context():
            demo_data_lock = os.path.join(app.instance_path, 'demo_data.lock')
            if not os.path.exists(demo_data_lock):
                try:
                    print("Lade Demo-Daten...")
                    
                    # Lösche vorhandene Daten
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        # Lösche in umgekehrter Reihenfolge der Abhängigkeiten
                        cursor.execute("DELETE FROM lendings")
                        cursor.execute("DELETE FROM tools")
                        cursor.execute("DELETE FROM workers")
                        cursor.execute("DELETE FROM users WHERE is_admin = 0")  # Behalte Admin-Benutzer
                        conn.commit()
                    
                    # Lade Demo-Daten
                    from app.models.demo_data import load_demo_data
                    load_demo_data()
                    
                    # Erstelle Lock-Datei
                    os.makedirs(app.instance_path, exist_ok=True)
                    with open(demo_data_lock, 'w') as f:
                        f.write('1')
                        
                    print("Demo-Daten erfolgreich geladen")
                    
                except Exception as e:
                    print(f"Fehler beim Laden der Demo-Daten: {str(e)}")
                    raise
    
    # Context Processor für Template-Variablen
    @app.context_processor
    def utility_processor():
        # Initialize with default values
        unfilled_days = 0
        
        # Check if we have a valid user context
        try:
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and hasattr(current_user, 'is_mitarbeiter') and current_user.is_mitarbeiter:
                today = datetime.now()
                # Use the ticket database for timesheet queries
                tickets_db_path = os.path.join(current_app.config.get('BASE_DIR', ''), 'app', 'database', 'tickets.db')
                if os.path.exists(tickets_db_path):
                    with sqlite3.connect(tickets_db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        timesheets = conn.execute('''
                            SELECT * FROM timesheets 
                            WHERE user_id = ?
                        ''', [current_user.id]).fetchall()
                        
                        for ts in timesheets:
                            try:
                                # Calculate week start
                                week_start = datetime.fromisocalendar(ts['year'], ts['kw'], 1)  # 1 = Monday
                                days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
                                
                                for i, day in enumerate(days):
                                    try:
                                        # Calculate the date for the current day
                                        current_day = week_start + timedelta(days=i)
                                        
                                        # Only check past days
                                        if current_day.date() < today.date():
                                            # Use direct key access for SQLite Row objects
                                            start_key = f'{day}_start'
                                            end_key = f'{day}_end'
                                            tasks_key = f'{day}_tasks'
                                            
                                            # Check if keys exist in the row before accessing
                                            has_times = (start_key in ts and ts[start_key]) or (end_key in ts and ts[end_key])
                                            has_tasks = tasks_key in ts and ts[tasks_key]
                                            
                                            if not (has_times and has_tasks):
                                                unfilled_days += 1
                                    except Exception as day_error:
                                        logging.error(f"Error processing day {day}: {str(day_error)}")
                                        continue
                            except Exception as ts_error:
                                logging.error(f"Error processing timesheet: {str(ts_error)}")
                                continue
        except Exception as e:
            logging.error(f"Error in utility_processor: {str(e)}")
            unfilled_days = 0

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
            },
            'unfilled_timesheet_days': unfilled_days
        }

    return app