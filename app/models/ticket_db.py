import sqlite3
import logging
from pathlib import Path
from app.config import config
import os
import stat
from datetime import datetime

logger = logging.getLogger(__name__)

class TicketDatabase:
    """Stellt Methoden für die Interaktion mit der Ticket-Datenbank bereit."""
    
    _initialized = False  # Klassen-Variable für Initialisierungsstatus
    
    def __init__(self):
        current_config = config['default']()
        self.db_path = current_config.TICKET_DATABASE
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Überprüfe und korrigiere die Berechtigungen
        self._check_and_fix_permissions()
        # Initialisiere das Schema nur wenn noch nicht initialisiert
        if not TicketDatabase._initialized:
            try:
                self.init_schema()
                TicketDatabase._initialized = True
                logger.info("Datenbankschema erfolgreich initialisiert")
            except Exception as e:
                logger.error(f"Fehler beim Initialisieren des Datenbankschemas: {str(e)}")
                raise
        
    def _check_and_fix_permissions(self):
        """Überprüft und korrigiert die Berechtigungen der Datenbankdatei"""
        try:
            if os.path.exists(self.db_path):
                # Aktuelle Berechtigungen abrufen
                current_perms = stat.S_IMODE(os.lstat(self.db_path).st_mode)
                # Gewünschte Berechtigungen: 664 (rw-rw-r--)
                desired_perms = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
                
                if current_perms != desired_perms:
                    logger.info(f"Korrigiere Berechtigungen für {self.db_path}")
                    os.chmod(self.db_path, desired_perms)
                    logger.info("Berechtigungen erfolgreich korrigiert")
            else:
                logger.info(f"Datenbank {self.db_path} existiert noch nicht")
        except Exception as e:
            logger.error(f"Fehler beim Überprüfen/Korrigieren der Berechtigungen: {str(e)}")
        
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
            
    def _insert_default_data(self):
        """Fügt Standarddaten in die Datenbank ein"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Füge nur die Standardeinstellungen ein
            settings = [
                ('theme', 'light', 'Farbschema der Anwendung'),
                ('language', 'de', 'Sprache der Anwendung'),
                ('items_per_page', '25', 'Anzahl der Einträge pro Seite'),
                ('color_primary', '#007bff', 'Primäre Farbe'),
                ('color_secondary', '#6c757d', 'Sekundäre Farbe'),
                ('color_success', '#28a745', 'Erfolgsfarbe'),
                ('color_danger', '#dc3545', 'Fehlerfarbe'),
                ('color_warning', '#ffc107', 'Warnfarbe'),
                ('color_info', '#17a2b8', 'Infofarbe'),
                ('label_tools_name', 'Werkzeuge', 'Anzeigename für Werkzeuge'),
                ('label_tools_icon', 'fas fa-tools', 'Icon für Werkzeuge'),
                ('label_consumables_name', 'Verbrauchsmaterial', 'Anzeigename für Verbrauchsmaterial'),
                ('label_consumables_icon', 'fas fa-box-open', 'Icon für Verbrauchsmaterial')
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            ''', settings)
            
            conn.commit()
            logger.info("Standardeinstellungen erfolgreich eingefügt")

    def init_schema(self):
        """Initialisiert das Datenbankschema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Schema Version Tabelle (muss zuerst erstellt werden)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Users Tabelle (muss vor Tickets erstellt werden wegen Foreign Keys)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    firstname TEXT,
                    lastname TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            # Settings Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Categories Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Locations Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Departments Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP
                )
            ''')
            
            # Tools Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'verfügbar',
                    category TEXT,
                    location TEXT,
                    last_maintenance DATE,
                    next_maintenance DATE,
                    maintenance_interval INTEGER,
                    last_checked TIMESTAMP,
                    supplier TEXT,
                    reorder_point INTEGER,
                    notes TEXT,
                    deleted BOOLEAN DEFAULT 0,
                    deleted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Workers Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT NOT NULL UNIQUE,
                    firstname TEXT NOT NULL,
                    lastname TEXT NOT NULL,
                    department TEXT,
                    email TEXT,
                    phone TEXT,
                    notes TEXT,
                    deleted BOOLEAN DEFAULT 0,
                    deleted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Consumables Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consumables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT,
                    quantity INTEGER DEFAULT 0,
                    min_quantity INTEGER DEFAULT 0,
                    category TEXT,
                    location TEXT,
                    unit TEXT,
                    supplier TEXT,
                    reorder_point INTEGER,
                    notes TEXT,
                    deleted BOOLEAN DEFAULT 0,
                    deleted_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Lendings Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lendings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_barcode TEXT NOT NULL,
                    worker_barcode TEXT NOT NULL,
                    lent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    returned_at TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tool_barcode) REFERENCES tools(barcode),
                    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
                )
            ''')
            
            # Consumable Usages Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS consumable_usages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumable_barcode TEXT NOT NULL,
                    worker_barcode TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
                    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
                )
            ''')
            
            # Tickets Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'offen',
                    priority TEXT DEFAULT 'normal',
                    created_by TEXT NOT NULL,
                    assigned_to TEXT,
                    category TEXT,
                    due_date TIMESTAMP,
                    estimated_time INTEGER,
                    actual_time INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolution_notes TEXT,
                    response TEXT,
                    last_modified_by TEXT,
                    last_modified_at TIMESTAMP,
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
                    created_by TEXT NOT NULL,
                    is_private BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users(username)
                )
            ''')
            
            # Ticket Messages Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                    FOREIGN KEY (sender) REFERENCES users(username)
                )
            ''')
            
            # Ticket History Tabelle
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
            
            # System Logs Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT
                )
            ''')
            
            # Access Settings Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access_settings (
                    route TEXT PRIMARY KEY,
                    is_public BOOLEAN DEFAULT 0,
                    description TEXT
                )
            ''')
            
            # Timesheets Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS timesheets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    kw INTEGER NOT NULL,
                    montag_start TEXT,
                    montag_end TEXT,
                    montag_tasks TEXT,
                    dienstag_start TEXT,
                    dienstag_end TEXT,
                    dienstag_tasks TEXT,
                    mittwoch_start TEXT,
                    mittwoch_end TEXT,
                    mittwoch_tasks TEXT,
                    donnerstag_start TEXT,
                    donnerstag_end TEXT,
                    donnerstag_tasks TEXT,
                    freitag_start TEXT,
                    freitag_end TEXT,
                    freitag_tasks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            conn.commit()
            logger.info("Datenbankschema erfolgreich initialisiert")
            
            # Füge Standarddaten ein
            self._insert_default_data()

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

    def get_ticket_messages(self, ticket_id):
        """Holt alle Nachrichten für ein Ticket"""
        try:
            messages = self.query("""
                SELECT *
                FROM ticket_messages
                WHERE ticket_id = ?
                ORDER BY created_at ASC
            """, [ticket_id])
            return messages
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Ticket-Nachrichten: {str(e)}")
            return []

    def get_ticket_notes(self, ticket_id):
        """Holt alle Notizen für ein Ticket"""
        try:
            notes = self.query("""
                SELECT *
                FROM ticket_notes
                WHERE ticket_id = ?
                ORDER BY created_at DESC
            """, [ticket_id])
            return notes
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Ticket-Notizen: {str(e)}")
            return []

    def get_ticket_history(self, ticket_id):
        """Holt die Historie eines Tickets"""
        try:
            history = self.query("""
                SELECT *
                FROM ticket_history
                WHERE ticket_id = ?
                ORDER BY changed_at DESC
            """, [ticket_id])
            return history
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der Ticket-Historie: {str(e)}")
            return []

    def add_ticket_message(self, ticket_id, message, sender, is_admin=False):
        """Fügt eine neue Nachricht zu einem Ticket hinzu"""
        try:
            self.query("""
                INSERT INTO ticket_messages 
                (ticket_id, message, sender, is_admin, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, [ticket_id, message, sender, is_admin])
            
            # Aktualisiere das updated_at Feld des Tickets
            self.query("""
                UPDATE tickets
                SET updated_at = datetime('now')
                WHERE id = ?
            """, [ticket_id])
            
            return True
        except Exception as e:
            logging.error(f"Fehler beim Hinzufügen der Ticket-Nachricht: {str(e)}")
            raise

    def create_ticket(self, title, description, created_by, priority='normal', category=None, due_date=None, estimated_time=None):
        """Erstellt ein neues Ticket"""
        try:
            # Füge das Ticket ein
            self.query("""
                INSERT INTO tickets 
                (title, description, status, priority, created_by, category, due_date, estimated_time, created_at, updated_at)
                VALUES (?, ?, 'offen', ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, [title, description, priority, created_by, category, due_date, estimated_time])
            
            # Hole die ID des neuen Tickets
            ticket_id = self.query("SELECT last_insert_rowid() as id", one=True)['id']
            
            return ticket_id
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            raise

    def get_ticket(self, ticket_id):
        """Holt ein einzelnes Ticket aus der Datenbank."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT *
                FROM tickets
                WHERE id = ?
            """, [ticket_id])
            ticket = cursor.fetchone()
            
            if ticket:
                # Konvertiere das Row-Objekt in ein Dictionary
                ticket_dict = dict(ticket)
                
                # Konvertiere Datumsfelder
                date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
                for field in date_fields:
                    if field in ticket_dict and ticket_dict[field]:
                        try:
                            ticket_dict[field] = datetime.strptime(ticket_dict[field], '%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            ticket_dict[field] = None
                
                return ticket_dict
            
            return None

    def _create_tables(self):
        """Erstellt die notwendigen Tabellen, falls sie nicht existieren."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Erstelle die Tabellen
            cursor.executescript('''
                -- Kategorien Tabelle
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP
                );

                -- Standorte Tabelle
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP
                );

                -- Abteilungen Tabelle
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP
                );

                -- Einstellungen Tabelle
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Benutzer Tabelle
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
            ''')
            conn.commit() 