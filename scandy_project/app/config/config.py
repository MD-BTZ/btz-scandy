"""
Konfigurationsmodul für Scandy - MongoDB-only
"""
import os
from pathlib import Path
import secrets

class Config:
    """Basis-Konfigurationsklasse"""
    # Basis-Verzeichnis der Anwendung
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # MongoDB Konfiguration
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://admin:scandy123@localhost:27017/')
    MONGODB_DB = os.environ.get('MONGODB_DB', 'scandy')
    MONGODB_COLLECTION_PREFIX = os.environ.get('MONGODB_COLLECTION_PREFIX', '')
    
    # Upload-Verzeichnis
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'uploads')
    
    # Backup-Verzeichnis
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    
    # Flask-Session
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(BASE_DIR, 'app', 'flask_session')
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 86400  # 24 Stunden
    
    # Sicherheit
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Server-Einstellungen
    HOST = '0.0.0.0'
    PORT = 5000
    
    # Sicherheitseinstellungen
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'

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