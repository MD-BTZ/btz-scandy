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
    
    # Sicherheit
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    
    # Server-Einstellungen
    HOST = '0.0.0.0'
    PORT = 5000

class DevelopmentConfig(Config):
    """Entwicklungs-Konfiguration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Test-Konfiguration"""
    DEBUG = True
    TESTING = True
    DATABASE = ':memory:'

class ProductionConfig(Config):
    """Produktions-Konfiguration"""
    DEBUG = False
    TESTING = False

# Konfigurationen
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 