import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

def setup_logger(name, log_file, level=logging.INFO):
    """Richtet einen spezifischen Logger ein"""
    # Stelle sicher, dass das logs-Verzeichnis existiert
    os.makedirs('logs', exist_ok=True)
    
    # Handler erstellen
    handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=5,
        delay=True
    )
    
    # Formatter erstellen und hinzufügen
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Logger erstellen und konfigurieren
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    
    # Konsolen-Handler hinzufügen
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def init_app_logger(app):
    """Initialisiert den Haupt-Application-Logger"""
    # Stelle sicher, dass das Logs-Verzeichnis existiert
    log_dir = Path(app.root_path) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Formatter erstellen
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Entferne alle bestehenden Handler
    app.logger.handlers = []
    
    # Konsolen-Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    app.logger.addHandler(console_handler)
    
    # Datei-Handler
    file_handler = RotatingFileHandler(
        log_dir / 'app.log',
        maxBytes=1024 * 1024,
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    
    # Log-Level setzen
    app.logger.setLevel(logging.INFO)
    
    # Propagate auf False setzen, um doppelte Meldungen zu vermeiden
    app.logger.propagate = False

# Spezifische Logger initialisieren
loggers = {
    'user_actions': setup_logger('user_actions', 'logs/user_actions.log'),
    'errors': setup_logger('errors', 'logs/errors.log'),
    'database': setup_logger('database', 'logs/database.log')
} 