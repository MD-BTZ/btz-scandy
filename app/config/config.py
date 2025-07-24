"""
Konfigurationsmodul für Scandy - MongoDB-only
"""
import os
from pathlib import Path
import secrets
from datetime import datetime

class Config:
    """Basis-Konfigurationsklasse"""
    # Basis-Verzeichnis der Anwendung
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # MongoDB Konfiguration
    MONGODB_URI = os.environ.get('MONGODB_URI')
    MONGODB_DB = os.environ.get('MONGODB_DB', 'scandy')
    MONGODB_COLLECTION_PREFIX = os.environ.get('MONGODB_COLLECTION_PREFIX', '')
    
    # Upload-Verzeichnis
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'uploads')
    
    # Backup-Verzeichnis
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    
    # Flask-Session
    SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')
    SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', os.path.join(BASE_DIR, 'app', 'flask_session'))
    SESSION_PERMANENT = os.environ.get('SESSION_PERMANENT', 'True').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '86400'))  # 24 Stunden
    
    # Sicherheit
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Server-Einstellungen
    HOST = '0.0.0.0'
    PORT = 5000
    
    # Static Files Konfiguration (für LXC-Container)
    STATIC_FOLDER = os.path.join(BASE_DIR, 'app', 'static')
    STATIC_URL_PATH = '/static'
    
    # LXC-spezifische Einstellungen
    LXC_MODE = os.environ.get('LXC_MODE', 'false').lower() == 'true'
    if LXC_MODE:
        # Deaktiviere HTTPS für LXC-Container
        SESSION_COOKIE_SECURE = False
        REMEMBER_COOKIE_SECURE = False
    
    # Base URL für E-Mails und externe Links
    BASE_URL = os.environ.get('BASE_URL')
    if not BASE_URL:
        # Automatische Erkennung der externen IP
        import socket
        try:
            # Hole die externe IP-Adresse (nicht die Docker-interne)
            # Verwende eine öffentliche DNS-Abfrage um die externe IP zu bekommen
            import requests
            try:
                # Versuche die externe IP über einen öffentlichen Service zu bekommen
                response = requests.get('https://api.ipify.org', timeout=3)
                if response.status_code == 200:
                    external_ip = response.text.strip()
                    BASE_URL = f"http://{external_ip}:{PORT}"
                else:
                    raise Exception("Konnte externe IP nicht abrufen")
            except:
                # Fallback: Verwende die lokale IP-Adresse
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                BASE_URL = f"http://{local_ip}:{PORT}"
        except:
            # Fallback auf localhost
            BASE_URL = f"http://localhost:{PORT}"
    
    # Sicherheitseinstellungen
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = os.environ.get('REMEMBER_COOKIE_SECURE', 'True').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    # Datumsformat-Konfiguration (Deutsch)
    DATE_FORMAT = '%d.%m.%Y'
    TIME_FORMAT = '%H:%M'
    DATETIME_FORMAT = '%d.%m.%Y %H:%M'
    DATETIME_FULL_FORMAT = '%d.%m.%Y %H:%M:%S'
    
    # Locale-Konfiguration
    LOCALE = 'de_DE'
    TIMEZONE = 'Europe/Berlin'
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    @staticmethod
    def format_datetime(dt, format_type='datetime'):
        """Formatiert ein Datum im deutschen Format"""
        if not dt:
            return ''
        
        if isinstance(dt, str):
            try:
                # Versuche verschiedene Eingabeformate
                for fmt in ['%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M', '%Y-%m-%d']:
                    try:
                        dt = datetime.strptime(dt, fmt)
                        break
                    except ValueError:
                        continue
            except:
                return dt
        
        formats = {
            'date': Config.DATE_FORMAT,
            'time': Config.TIME_FORMAT,
            'datetime': Config.DATETIME_FORMAT,
            'datetime_full': Config.DATETIME_FULL_FORMAT
        }
        
        return dt.strftime(formats.get(format_type, Config.DATETIME_FORMAT))
    
    @staticmethod
    def parse_datetime(date_string, format_type='datetime'):
        """Parst ein Datum aus deutschem Format"""
        if not date_string:
            return None
        
        formats = {
            'date': Config.DATE_FORMAT,
            'time': Config.TIME_FORMAT,
            'datetime': Config.DATETIME_FORMAT,
            'datetime_full': Config.DATETIME_FULL_FORMAT
        }
        
        try:
            return datetime.strptime(date_string, formats.get(format_type, Config.DATETIME_FORMAT))
        except ValueError:
            return None

class DevelopmentConfig(Config):
    """Entwicklungs-Konfiguration"""
    DEBUG = True
    TESTING = False
    SECRET_KEY = 'dev-key-not-for-production'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = False  # Erlaubt JavaScript-Zugriff für Debugging

class TestingConfig(Config):
    """Test-Konfiguration"""
    DEBUG = True
    TESTING = True
    SECRET_KEY = 'test-key-not-for-production'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    # MongoDB für Tests
    MONGODB_DB = 'scandy_test'

class ProductionConfig(Config):
    """Produktions-Konfiguration"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        # Produktionsspezifische Initialisierung
        if not app.config['SECRET_KEY']:
            app.config['SECRET_KEY'] = secrets.token_hex(32)

# Konfigurationen
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 