from flask import Flask, jsonify, render_template, redirect, url_for, g, send_from_directory, session, request, flash, current_app
from flask_session import Session  # Session-Management
from .constants import Routes
from app.config.version import VERSION
import os
from datetime import datetime, timedelta
from app.utils.filters import register_filters, status_color, priority_color
import logging
from app.utils.error_handler import handle_errors
from flask_compress import Compress
from app.utils.auth_utils import needs_setup
from pathlib import Path
import sys
from flask_login import LoginManager, current_user
from app.utils.context_processors import register_context_processors
from app.config import Config
from app.routes import init_app

# Logger einrichten
logger = logging.getLogger(__name__)

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
    project_root = Path(current_config.BASE_DIR)

    # Liste der zu erstellenden Verzeichnisse
    directories = [
        current_config.BACKUP_DIR,
        current_config.UPLOAD_FOLDER,
        project_root / 'tmp',
        current_config.SESSION_FILE_DIR
    ]
    
    # Verzeichnisse erstellen
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Verzeichnis erstellt: {dir_path}")
        else:
            logging.info(f"Verzeichnis existiert bereits: {dir_path}")

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
    
    # MongoDB-Initialisierung
    try:
        from app.models.mongodb_models import create_mongodb_indexes
        with app.app_context():
            create_mongodb_indexes()
            logging.info("MongoDB-Indizes erstellt")
    except Exception as e:
        logging.error(f"Fehler bei MongoDB-Initialisierung: {e}")
    
    # Flask-Login initialisieren
    login_manager.init_app(app)
    
    # Flask-Session initialisieren
    Session(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            from app.models.mongodb_models import MongoDBUser
            from app.models.user import User
            
            user_data = MongoDBUser.get_by_id(user_id)
            if user_data:
                user = User(user_data)
                return user
            return None
        except Exception as e:
            logging.error(f"Fehler beim Laden des Benutzers {user_id}: {e}")
            return None
    
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
    init_app(app)
    
    # Fehlerbehandlung registrieren
    handle_errors(app)
    
    # Filter registrieren
    register_filters(app)
    
    # Register custom filters
    app.jinja_env.filters['status_color'] = status_color
    app.jinja_env.filters['priority_color'] = priority_color
    
    # Komprimierung aktivieren
    Compress(app)
    
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