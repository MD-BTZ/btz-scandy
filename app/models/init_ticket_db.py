import logging
import os
from app.models.ticket_db import TicketDatabase
from app.config.config import Config
from app.models.migrations import run_ticket_db_migrations

logger = logging.getLogger(__name__)

def init_ticket_db():
    """Initialisiert die Ticket-Datenbank nur wenn sie noch nicht existiert"""
    try:
        logger.info("Prüfe Ticket-Datenbank...")
        current_config = Config()
        ticket_db_path = current_config.TICKET_DATABASE
        
        # Prüfe ob die Datenbank bereits existiert
        if os.path.exists(ticket_db_path):
            logger.info("Ticket-Datenbank existiert bereits")
            return
            
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(ticket_db_path), exist_ok=True)
        
        # Erstelle TicketDatabase-Instanz
        ticket_db = TicketDatabase()
        
        # Initialisiere das Schema
        ticket_db.init_schema()
        
        # Führe Migrationen durch
        run_ticket_db_migrations(ticket_db_path)
        
        # Setze die Schema-Version
        with ticket_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO schema_version (version)
                VALUES (1)
            """)
            conn.commit()
        
        logger.info("Ticket-Datenbank erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung der Ticket-Datenbank: {str(e)}")
        raise 