import logging
from app.models.ticket_db import TicketDatabase
from app.config.config import Config

logger = logging.getLogger(__name__)

def init_ticket_db():
    """Initialisiert die Ticket-Datenbank"""
    try:
        logger.info("Initialisiere Ticket-Datenbank...")
        ticket_db = TicketDatabase()
        ticket_db.init_schema()
        logger.info("Ticket-Datenbank erfolgreich initialisiert")
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung der Ticket-Datenbank: {str(e)}")
        raise 