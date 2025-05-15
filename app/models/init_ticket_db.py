import logging
from app.models.ticket_db import TicketDatabase
from app.config.config import Config
from app.models.migrations import run_ticket_db_migrations

logger = logging.getLogger(__name__)

def init_ticket_db():
    """Initialisiert die Ticket-Datenbank"""
    try:
        logger.info("Initialisiere Ticket-Datenbank...")
        current_config = Config()
        ticket_db_path = current_config.TICKET_DATABASE
        
        # Führe Migrationen durch
        run_ticket_db_migrations(ticket_db_path)
        
        # Initialisiere das Schema
        ticket_db = TicketDatabase()
        ticket_db.init_schema()
        
        logger.info("Ticket-Datenbank erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung der Ticket-Datenbank: {str(e)}")
        raise 