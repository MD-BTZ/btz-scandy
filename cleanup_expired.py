#!/usr/bin/env python3
"""
Automatische Bereinigung abgelaufener Benutzer und Jobs

Dieses Script kann als Cron-Job ausgeführt werden, um regelmäßig abgelaufene Daten zu bereinigen.
"""

import os
import sys
import logging
from datetime import datetime

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Flask-App importieren
from app import create_app
from app.services.cleanup_service import CleanupService

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cleanup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Hauptfunktion für die automatische Bereinigung"""
    try:
        logger.info("Starte automatische Bereinigung abgelaufener Daten...")
        
        # Flask-App erstellen
        app = create_app()
        
        with app.app_context():
            # Cleanup ausführen
            results = CleanupService.cleanup_all()
            
            if 'error' in results:
                logger.error(f"Fehler bei der Bereinigung: {results['error']}")
                return 1
            
            # Ergebnisse loggen
            user_count = results['users']['deleted_count']
            job_count = results['jobs']['deleted_count']
            total_count = results['total']['deleted_count']
            
            logger.info(f"Bereinigung abgeschlossen:")
            logger.info(f"  - {user_count} abgelaufene Benutzer gelöscht")
            logger.info(f"  - {job_count} abgelaufene Jobs gelöscht")
            logger.info(f"  - Insgesamt {total_count} Einträge bereinigt")
            
            if total_count > 0:
                logger.info("Bereinigung erfolgreich abgeschlossen")
            else:
                logger.info("Keine abgelaufenen Daten gefunden")
            
            return 0
            
    except Exception as e:
        logger.error(f"Kritischer Fehler bei der Bereinigung: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 