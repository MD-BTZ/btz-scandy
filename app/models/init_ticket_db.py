import logging
import os
from app.models.ticket_db import TicketDatabase
from app.config.config import Config

logger = logging.getLogger(__name__)

def init_ticket_db():
    """Initialisiert die Ticket-Datenbank nur wenn sie noch nicht existiert"""
    try:
        logger.info("Prüfe Ticket-Datenbank...")
        current_config = Config()
        ticket_db_path = current_config.TICKET_DATABASE
        
        # Prüfe ob die Datenbank bereits existiert
        db_exists = os.path.exists(ticket_db_path)
        
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(ticket_db_path), exist_ok=True)
        
        # Erstelle TicketDatabase-Instanz
        ticket_db = TicketDatabase()
        
        if not db_exists:
            # Initialisiere das Schema nur für neue Datenbanken
            ticket_db.init_schema()
            logger.info("Neue Ticket-Datenbank erfolgreich initialisiert")
        
        return True
        
    except Exception as e:
        logger.error(f"Fehler bei der Initialisierung der Ticket-Datenbank: {str(e)}")
        raise 