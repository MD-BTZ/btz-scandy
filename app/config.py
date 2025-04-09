import os
from pathlib import Path
import sys

class Config:
    """Basis-Konfiguration"""
    
    # Bestimme Basis-Verzeichnis
    BASE_DIR = Path(__file__).parent.parent
    
    # Plattformunabhängige Pfade
    DATABASE_DIR = BASE_DIR / 'app' / 'database'
    DATABASE = str(DATABASE_DIR / 'inventory.db')
    BACKUP_DIR = BASE_DIR / 'backups'
    
    # Stelle sicher dass die Verzeichnisse existieren
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Basis-Konfiguration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    
    # Server-Konfiguration
    SERVER_MODE = False  # Standard: Client-Modus
    SERVER_URL = os.environ.get('SERVER_URL', '')  # URL des Sync-Servers
    SERVER_HOST = os.environ.get('SERVER_HOST', 'localhost')  # Server-Host
    SERVER_PORT = os.environ.get('SERVER_PORT', '5000')  # Server-Port
    SYNC_INTERVAL = 300  # Sync-Intervall in Sekunden (5 Minuten)
    CLIENT_NAME = os.environ.get('CLIENT_NAME', 'default_client')
    
    # Backup-Konfiguration
    BACKUP_INTERVAL = 86400  # Backup-Intervall in Sekunden (24 Stunden)
    
    # Upload-Konfiguration
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    @staticmethod
    def is_pythonanywhere():
        """Überprüft, ob die Anwendung auf PythonAnywhere läuft"""
        return ('PYTHONANYWHERE_SITE' in os.environ or 
                os.path.exists('/var/www') or 
                any('uwsgi' in arg.lower() for arg in sys.argv))

    @staticmethod
    def get_project_root():
        """Gibt den absoluten Pfad zum Projektverzeichnis zurück"""
        if 'PYTHONANYWHERE_SITE' in os.environ:
            return '/home/aklann/Scandy'
        return str(Path(__file__).parent.parent)

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False
    
    # Entwicklungsspezifische Einstellungen
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
    # Sicherheitseinstellungen für Produktion
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 1800  # 30 Minuten
    
    # PythonAnywhere spezifische Pfade
    DATABASE = '/home/aklann/Scandy/app/database/inventory.db'
    BACKUP_DIR = '/home/aklann/Scandy/backups'
    UPLOAD_FOLDER = '/home/aklann/Scandy/uploads'

# Konfiguration basierend auf Umgebung wählen
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig if not Config.is_pythonanywhere() else ProductionConfig
} 