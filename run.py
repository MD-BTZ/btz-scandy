from app import create_app
from app.models.init_db import init_users
import logging

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starte Anwendung...")
    
    # App erstellen
    app = create_app()
    
    # Datenbank-Tabellen erstellen (ohne Admin-Account)
    with app.app_context():
        try:
            init_users()  # Nur Tabelle erstellen, kein Admin-Account
            logger.info("Datenbank initialisiert")
        except Exception as e:
            logger.error(f"Fehler bei der Datenbank-Initialisierung: {e}")
    
    logger.info("Starte Entwicklungsserver...")
    app.run(debug=True)
  