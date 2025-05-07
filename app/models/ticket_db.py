import sqlite3
import logging
from pathlib import Path
from app.config import config
import os

logger = logging.getLogger(__name__)

class TicketDatabase:
    """Stellt Methoden für die Interaktion mit der Ticket-Datenbank bereit."""
    
    def __init__(self):
        current_config = config['default']()
        self.db_path = current_config.TICKET_DATABASE
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def get_connection(self):
        """Erstellt eine neue Verbindung zur Ticket-Datenbank."""
        conn = sqlite3.connect(self.db_path)
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
                    created_by TEXT NOT NULL,
                    assigned_to TEXT,
                    resolution_notes TEXT,
                    last_modified_by TEXT,
                    last_modified_at TIMESTAMP,
                    category TEXT,
                    due_date TIMESTAMP,
                    estimated_time INTEGER, -- in Minuten
                    actual_time INTEGER, -- in Minuten
                    FOREIGN KEY (created_by) REFERENCES users(username),
                    FOREIGN KEY (assigned_to) REFERENCES users(username),
                    FOREIGN KEY (last_modified_by) REFERENCES users(username)
                )
            ''')
            
            # Ticket Notes Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT NOT NULL,
                    modified_at TIMESTAMP,
                    modified_by TEXT,
                    is_private BOOLEAN DEFAULT 0,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users(username),
                    FOREIGN KEY (modified_by) REFERENCES users(username)
                )
            ''')
            
            # Ticket History Tabelle für Änderungsverfolgung
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    changed_by TEXT NOT NULL,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                    FOREIGN KEY (changed_by) REFERENCES users(username)
                )
            ''')
            
            conn.commit()
            logger.info("Ticket-Datenbankschema erfolgreich initialisiert") 

    def update_ticket(self, id, status, assigned_to=None, category=None, due_date=None, 
                     estimated_time=None, actual_time=None, last_modified_by=None):
        """Aktualisiert ein Ticket mit den neuen Werten"""
        try:
            # Hole das alte Ticket für die Historie
            old_ticket = self.get_ticket(id)
            if not old_ticket:
                raise ValueError("Ticket nicht gefunden")

            # Aktualisiere das Ticket
            self.query("""
                UPDATE tickets 
                SET status = ?,
                    assigned_to = ?,
                    category = ?,
                    due_date = ?,
                    estimated_time = ?,
                    actual_time = ?,
                    last_modified_by = ?,
                    last_modified_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    resolved_at = CASE 
                        WHEN ? = 'gelöst' THEN CURRENT_TIMESTAMP 
                        ELSE NULL 
                    END
                WHERE id = ?
            """, [status, assigned_to, category, due_date, estimated_time, actual_time, 
                  last_modified_by, status, id])

            # Erstelle Historie-Einträge für geänderte Felder
            changes = []
            if old_ticket['status'] != status:
                changes.append(('status', old_ticket['status'], status))
            if old_ticket['assigned_to'] != assigned_to:
                changes.append(('assigned_to', old_ticket['assigned_to'], assigned_to))
            if old_ticket['category'] != category:
                changes.append(('category', old_ticket['category'], category))
            if old_ticket['due_date'] != due_date:
                changes.append(('due_date', old_ticket['due_date'], due_date))
            if old_ticket['estimated_time'] != estimated_time:
                changes.append(('estimated_time', old_ticket['estimated_time'], estimated_time))
            if old_ticket['actual_time'] != actual_time:
                changes.append(('actual_time', old_ticket['actual_time'], actual_time))

            # Füge Historie-Einträge hinzu
            for field_name, old_value, new_value in changes:
                self.query("""
                    INSERT INTO ticket_history 
                    (ticket_id, field_name, old_value, new_value, changed_by)
                    VALUES (?, ?, ?, ?, ?)
                """, [id, field_name, str(old_value), str(new_value), last_modified_by])

            return True
        except Exception as e:
            logging.error(f"Fehler beim Aktualisieren des Tickets: {str(e)}")
            raise

    def add_note(self, ticket_id, note, author_name, is_private=False):
        """Fügt eine neue Notiz zu einem Ticket hinzu"""
        try:
            self.query("""
                INSERT INTO ticket_notes 
                (ticket_id, note, created_by, is_private)
                VALUES (?, ?, ?, ?)
            """, [ticket_id, note, author_name, is_private])
            return True
        except Exception as e:
            logging.error(f"Fehler beim Hinzufügen der Notiz: {str(e)}")
            raise 