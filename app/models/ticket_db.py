import sqlite3
import logging
from pathlib import Path
from app.config import Config

logger = logging.getLogger(__name__)

class TicketDatabase:
    """Stellt Methoden für die Interaktion mit der Ticket-Datenbank bereit."""
    
    def __init__(self):
        self.db_path = Path(Config.DATABASE_DIR) / 'tickets.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    def get_connection(self):
        """Erstellt eine neue Verbindung zur Datenbank"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
        
    def query(self, sql, params=None, one=False):
        """Führt eine SQL-Abfrage aus und gibt die Ergebnisse als Dictionary zurück"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Für INSERT, UPDATE, DELETE Operationen
            if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
                return cursor.rowcount
            
            # Für SELECT Operationen
            results = cursor.fetchall()
            if one:
                return dict(results[0]) if results else None
            return [dict(row) for row in results]
            
    def init_schema(self):
        """Initialisiert das Datenbankschema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tickets Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'offen',
                    priority TEXT DEFAULT 'normal',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    created_by TEXT,
                    assigned_to TEXT,
                    resolution_notes TEXT
                )
            ''')
            
            # Ticket Notes Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            ''')
            
            conn.commit()
            logger.info("Ticket-Datenbankschema erfolgreich initialisiert") 