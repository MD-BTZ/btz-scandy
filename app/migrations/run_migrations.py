import logging
from app.migrations.migrate_users import migrate_users
from app import create_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Führt alle Migrationen aus"""
    try:
        # Erstelle Flask App und Context
        app = create_app()
        with app.app_context():
            logger.info("Starte User-Migration...")
            migrate_users()
            logger.info("Alle Migrationen erfolgreich abgeschlossen")
    except Exception as e:
        logger.error(f"Fehler bei der Migration: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    run_migrations() 