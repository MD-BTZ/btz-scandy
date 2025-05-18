import sqlite3
import logging
from pathlib import Path
from app.config import config
from app.models.ticket_db import TicketDatabase
from app.models.database import Database

logger = logging.getLogger(__name__)

def migrate_users():
    """Migriert alle User von inventory.db nach tickets.db"""
    try:
        # Lade alle User aus inventory.db
        users = Database.query("SELECT * FROM users")
        logger.info(f"Gefundene User in inventory.db: {len(users)}")

        # TicketDatabase-Instanz für Ziel-DB
        ticket_db = TicketDatabase()

        # Migriere jeden User
        for user in users:
            # Prüfe ob User bereits existiert
            existing = ticket_db.query(
                "SELECT id FROM users WHERE username = ?", 
                [user['username']], 
                one=True
            )
            
            if existing:
                logger.info(f"User {user['username']} existiert bereits in tickets.db")
                continue

            # Füge User in tickets.db ein
            sql = """INSERT INTO users 
                    (username, email, password_hash, role, is_active, firstname, lastname, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
            
            ticket_db.query(sql, [
                user['username'],
                user.get('email'),
                user['password_hash'],
                user['role'],
                user.get('is_active', 1),
                user.get('firstname'),
                user.get('lastname'),
                user.get('created_at')
            ])
            logger.info(f"User {user['username']} erfolgreich migriert")

        logger.info("User-Migration abgeschlossen")

    except Exception as e:
        logger.error(f"Fehler bei der User-Migration: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    migrate_users() 