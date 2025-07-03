"""
Scandy - Werkzeug- und Verbrauchsmaterialverwaltung

Dieses Modul initialisiert die Flask-Anwendung und konfiguriert alle notwendigen
Komponenten wie Datenbankverbindung, Session-Management, Blueprints und Middleware.

Hauptfunktionen:
- Flask-App-Erstellung und Konfiguration
- MongoDB-Verbindung und Index-Erstellung
- Blueprint-Registrierung
- Error-Handling und Logging
- Context-Processor für Template-Variablen
"""

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
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)

# Backup-Verzeichnisse erstellen
backup_dir = Path(__file__).parent.parent / 'backups'
backup_dir.mkdir(exist_ok=True)

def normalize_database_ids():
    """
    Normalisiert alle IDs in der Datenbank zu Strings beim Systemstart.
    Dies verhindert Probleme mit gemischten ID-Typen nach Imports.
    """
    try:
        from app.models.mongodb_database import mongodb
        from bson import ObjectId
        
        collections_to_normalize = [
            'tickets', 'users', 'tools', 'consumables', 'workers',
            'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit'
        ]
        
        total_updated = 0
        
        for collection_name in collections_to_normalize:
            try:
                documents = mongodb.find(collection_name, {})
                updated_count = 0
                
                for doc in documents:
                    doc_id = doc.get('_id')
                    
                    # Falls die ID ein ObjectId ist, konvertiere sie zu String
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)
                        
                        # Erstelle ein neues Dokument mit String-ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id
                        
                        # Lösche das alte Dokument und füge das neue ein
                        mongodb.delete_one(collection_name, {'_id': doc_id})
                        mongodb.insert_one(collection_name, new_doc)
                        
                        updated_count += 1
                
                if updated_count > 0:
                    logging.info(f"Collection {collection_name}: {updated_count} IDs normalisiert")
                total_updated += updated_count
                
            except Exception as e:
                logging.warning(f"Fehler bei ID-Normalisierung in Collection {collection_name}: {e}")
        
        if total_updated > 0:
            logging.info(f"ID-Normalisierung abgeschlossen: {total_updated} IDs in allen Collections normalisiert")
        else:
            logging.info("ID-Normalisierung: Alle IDs sind bereits normalisiert")
            
    except Exception as e:
        logging.error(f"Fehler bei ID-Normalisierung: {e}")
        # Nicht die Anwendung stoppen, nur loggen

# Flask-Login Manager konfigurieren
login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = 'auth.login'
login_manager.login_message = "Bitte melden Sie sich an, um auf diese Seite zuzugreifen."
login_manager.login_message_category = "info"

class Config:
    """Konfigurationsklasse für verschiedene Umgebungen"""
    
    @staticmethod
    def init_server():
        """Server-Initialisierung (Platzhalter)"""
        pass

    @staticmethod
    def init_client(server_url=None):
        """Client-Initialisierung (Platzhalter)"""
        pass

    @staticmethod
    def is_pythonanywhere():
        """Prüft, ob die Anwendung auf PythonAnywhere läuft"""
        # This is a placeholder implementation. You might want to implement a more robust check for PythonAnywhere
        return False

def ensure_directories_exist():
    """
    Stellt sicher, dass alle benötigten Verzeichnisse existieren.
    
    Erstellt folgende Verzeichnisse falls sie nicht existieren:
    - Backup-Verzeichnis
    - Upload-Verzeichnis
    - Temporäres Verzeichnis
    - Session-Datei-Verzeichnis
    """
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
    """
    Erstellt und konfiguriert die Flask-Anwendung.
    
    Args:
        test_config: Konfiguration für Tests (optional)
    
    Returns:
        Flask-App: Konfigurierte Flask-Anwendung
        
    Initialisiert:
    - Flask-App und Konfiguration
    - Systemnamen aus Umgebungsvariablen
    - Logger und Verzeichnisse
    - MongoDB-Verbindung und Indizes
    - Flask-Login und Session-Management
    - Blueprints und Context-Processor
    - Error-Handling und Filter
    - E-Mail-System
    """
    app = Flask(__name__)
    
    # ===== KONFIGURATION LADEN =====
    from app.config import config
    config_name = 'default' if test_config is None else test_config
    app.config.from_object(config[config_name])
    
    # ===== SYSTEMNAMEN AUS UMGEBUNGSVARIABLEN =====
    app.config['SYSTEM_NAME'] = os.environ.get('SYSTEM_NAME') or 'Scandy'
    app.config['TICKET_SYSTEM_NAME'] = os.environ.get('TICKET_SYSTEM_NAME') or 'Aufgaben'
    app.config['TOOL_SYSTEM_NAME'] = os.environ.get('TOOL_SYSTEM_NAME') or 'Werkzeuge'
    app.config['CONSUMABLE_SYSTEM_NAME'] = os.environ.get('CONSUMABLE_SYSTEM_NAME') or 'Verbrauchsgüter'
    
    # ===== LOGGER UND VERZEICHNISSE =====
    from app.utils.logger import init_app_logger
    init_app_logger(app)
    app.logger.setLevel(logging.DEBUG)
    app.logger.info("\n=== ANWENDUNGSSTART ===")
    
    ensure_directories_exist()
    
    # ===== MONGODB-INITIALISIERUNG =====
    try:
        from app.models.mongodb_models import create_mongodb_indexes
        with app.app_context():
            create_mongodb_indexes()
            logging.info("MongoDB-Indizes erstellt")
    except Exception as e:
        logging.error(f"Fehler bei MongoDB-Initialisierung: {e}")
    
    # ===== ID-NORMALISIERUNG BEIM START =====
    # Nur ausführen, wenn nicht explizit deaktiviert
    if not os.environ.get('DISABLE_ID_NORMALIZATION', 'false').lower() == 'true':
        try:
            with app.app_context():
                normalize_database_ids()
                logging.info("Datenbank-IDs normalisiert")
        except Exception as e:
            logging.error(f"Fehler bei ID-Normalisierung: {e}")
    else:
        logging.info("ID-Normalisierung beim Start deaktiviert")
    
    # ===== FLASK-LOGIN INITIALISIEREN =====
    login_manager.init_app(app)
    
    # ===== FLASK-SESSION INITIALISIEREN =====
    Session(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        """
        Lädt einen Benutzer aus der Datenbank für Flask-Login.
        
        Args:
            user_id: ID des zu ladenden Benutzers (immer ein String)
            
        Returns:
            User-Objekt oder None falls nicht gefunden
        """
        try:
            from app.models.mongodb_models import MongoDBUser
            from app.models.user import User
            from app.models.mongodb_database import mongodb
            
            print(f"load_user aufgerufen für ID: {user_id}")
            
            # Debug: Zeige alle verfügbaren User-IDs
            all_users = MongoDBUser.get_all()
            print(f"Verfügbare User-IDs: {[str(user.get('_id', 'No ID')) for user in all_users]}")
            
            # WICHTIG: user_id ist immer ein String (von Flask-Login)
            # Suche direkt in der Datenbank mit verschiedenen Methoden
            
            # Methode 1: Direkte String-Suche
            user_data = mongodb.find_one('users', {'_id': user_id})
            if user_data:
                print(f"DEBUG: User mit String-ID gefunden: {user_data.get('username')}")
                user = User(user_data)
                print(f"User geladen: {user.username}, ID: {user.id}")
                return user
            
            # Methode 2: ObjectId-Suche
            try:
                from bson import ObjectId
                obj_id = ObjectId(user_id)
                user_data = mongodb.find_one('users', {'_id': obj_id})
                if user_data:
                    print(f"DEBUG: User mit ObjectId gefunden: {user_data.get('username')}")
                    user = User(user_data)
                    print(f"User geladen: {user.username}, ID: {user.id}")
                    return user
            except Exception as e:
                print(f"DEBUG: ObjectId-Konvertierung fehlgeschlagen: {e}")
            
            # Methode 3: Fallback mit MongoDBUser.get_by_id
            user_data = MongoDBUser.get_by_id(user_id)
            if user_data:
                print(f"DEBUG: User mit MongoDBUser.get_by_id gefunden: {user_data.get('username')}")
                user = User(user_data)
                print(f"User geladen: {user.username}, ID: {user.id}")
                return user
            
            print(f"Kein User gefunden für ID: {user_id}")
            return None
        except Exception as e:
            logging.error(f"Fehler beim Laden des Benutzers {user_id}: {e}")
            return None
    
    # ===== CONTEXT PROCESSORS REGISTRIEREN =====
    register_context_processors(app)
    
    # Context Processor für Systemnamen
    @app.context_processor
    def inject_system_names():
        """Injiziert Systemnamen in alle Templates"""
        return {
            'system_name': app.config['SYSTEM_NAME'],
            'ticket_system_name': app.config['TICKET_SYSTEM_NAME'],
            'tool_system_name': app.config['TOOL_SYSTEM_NAME'],
            'consumable_system_name': app.config['CONSUMABLE_SYSTEM_NAME']
        }
    
    # ===== BLUEPRINTS REGISTRIEREN =====
    init_app(app)
    
    # ===== AUTOMATISCHES BACKUP-SYSTEM STARTEN =====
    try:
        from app.utils.auto_backup import start_auto_backup
        with app.app_context():
            start_auto_backup()
            logging.info("Automatisches Backup-System gestartet")
    except Exception as e:
        logging.error(f"Fehler beim Starten des automatischen Backup-Systems: {e}")
    
    # ===== HEALTH CHECK ROUTE =====
    @app.route('/health')
    def health_check():
        """
        Health Check für Docker Container und Monitoring.
        
        Prüft:
        - Datenbankverbindung (MongoDB Ping)
        - Anwendungsstatus
        
        Returns:
            JSON mit Status-Informationen
        """
        try:
            from app.models.mongodb_database import MongoDBDatabase
            mongodb = MongoDBDatabase()
            # Prüfe Datenbankverbindung durch einfache Abfrage
            mongodb._client.admin.command('ping')
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            }), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 503
    
    # ===== FEHLERBEHANDLUNG UND FILTER =====
    handle_errors(app)
    register_filters(app)
    
    # Register custom filters
    app.jinja_env.filters['status_color'] = status_color
    app.jinja_env.filters['priority_color'] = priority_color
    
    # ===== KOMPRIMIERUNG AKTIVIEREN =====
    Compress(app)
    
    # ===== E-MAIL-SYSTEM INITIALISIEREN =====
    try:
        from app.utils.email_utils import init_mail
        init_mail(app)
        app.logger.info("E-Mail-System initialisiert")
    except Exception as e:
        app.logger.warning(f"E-Mail-System konnte nicht initialisiert werden: {e}")
    
    # ===== CONTEXT PROCESSOR FÜR TEMPLATE-VARIABLEN =====
    @app.context_processor
    def utility_processor():
        """Injiziert Farben für Status und Prioritäten in alle Templates"""
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