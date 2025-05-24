"""
Konfigurationsmodul für Scandy
"""
import os
from pathlib import Path

class Config:
    """Basis-Konfigurationsklasse"""
    # Basis-Verzeichnis der Anwendung
    BASE_DIR = Path(__file__).parent.parent.parent
    
    # Datenbank-Verzeichnis
    DATABASE_DIR = os.path.join(BASE_DIR, 'app', 'database')
    
    # Datenbank-Pfade
    DATABASE = os.path.join(DATABASE_DIR, 'inventory.db')
    TICKET_DATABASE = os.path.join(DATABASE_DIR, 'tickets.db')
    
    # Upload-Verzeichnis
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'uploads')
    
    # Backup-Verzeichnis
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    
    # Flask-Session
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(BASE_DIR, 'app', 'database', 'flask_session')
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 86400  # 24 Stunden
    
    # Sicherheit
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY muss in der Produktion gesetzt sein!")
    
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

class TestingConfig(Config):
    """Test-Konfiguration"""
    DEBUG = True
    TESTING = True
    DATABASE = ':memory:'
    SECRET_KEY = 'test-key-not-for-production'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Produktions-Konfiguration"""
    DEBUG = False
    TESTING = False
    
    @classmethod
    def init_app(cls, app):
        # Produktionsspezifische Initialisierung
        if not app.config['SECRET_KEY']:
            raise ValueError("SECRET_KEY muss in der Produktion gesetzt sein!")

# Konfigurationen
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 