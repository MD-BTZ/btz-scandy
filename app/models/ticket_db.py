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
    
    def __init__(self, db_path=None):
        """Initialisiert die Ticket-Datenbank"""
        if db_path is None:
            from app.config import Config
            self.db_path = os.path.join(Config.BASE_DIR, 'app', 'database', 'tickets.db')
        else:
            self.db_path = db_path
        self.migrate_schema()  # Migration immer beim Initialisieren prüfen
        logger.info(f"Verwendeter Ticket-Datenbankpfad: {os.path.abspath(self.db_path)}")
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Überprüfe und korrigiere die Berechtigungen
        self._check_and_fix_permissions()
        # Initialisiere das Schema nur wenn noch nicht initialisiert
        if not TicketDatabase._initialized:
            try:
                self.init_schema()
                self.migrate_schema()
                TicketDatabase._initialized = True
                logger.info("Datenbankschema erfolgreich initialisiert und migriert")
            except Exception as e:
                logger.error(f"Fehler beim Initialisieren/Migrieren des Datenbankschemas: {str(e)}")
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
        """Gibt eine Datenbankverbindung zurück"""
        return sqlite3.connect(self.db_path)
        
    def query(self, sql, params=None, one=False):
        """Führt eine SQL-Abfrage aus und gibt die Ergebnisse als Dictionary zurück"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    logging.info(f"SQL Query: {sql} mit Parametern: {params}")
                    cursor.execute(sql, params)
                else:
                    logging.info(f"SQL Query: {sql}")
                    cursor.execute(sql)
                # Für INSERT, UPDATE, DELETE Operationen
                if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                    conn.commit()
                    affected_rows = cursor.rowcount
                    logging.info(f"SQL Operation erfolgreich. Betroffene Zeilen: {affected_rows}")
                    return affected_rows
                # Für SELECT Operationen
                results = cursor.fetchall()
                if one:
                    if not results:
                        return None
                    # Für COUNT-Abfragen
                    if sql.strip().upper().startswith('SELECT COUNT'):
                        return {'cnt': results[0][0]}
                    result = dict(zip([col[0] for col in cursor.description], results[0]))
                    logging.info(f"SELECT Ergebnis (one=True): {result}")
                    return result
                # Für normale SELECT-Abfragen
                results = [dict(zip([col[0] for col in cursor.description], row)) for row in results]
                logging.info(f"SELECT Ergebnisse: {results}")
                return results
        except Exception as e:
            logging.error(f"SQL Fehler: {str(e)}")
            logging.error(f"SQL Query: {sql}")
            if params:
                logging.error(f"Parameter: {params}")
            raise
            
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
            
            # Ticket-Kategorien Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
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
            
            # Auftrag Details Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auftrag_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    auftrag_an TEXT,
                    bereich TEXT,
                    auftraggeber_intern BOOLEAN DEFAULT 1,
                    auftraggeber_extern BOOLEAN DEFAULT 0,
                    auftraggeber_name TEXT,
                    kontakt TEXT,
                    auftragsbeschreibung TEXT,
                    ausgefuehrte_arbeiten TEXT,
                    arbeitsstunden REAL,
                    leistungskategorie TEXT,
                    fertigstellungstermin TEXT,
                    gesamtsumme REAL DEFAULT 0,
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
                )
            ''')
            
            # Auftrag Material Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auftrag_material (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    material TEXT,
                    menge REAL,
                    einzelpreis REAL,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
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
            
            # Ticket Assignments Tabelle
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                    UNIQUE(ticket_id, username)
                )
            ''')
            
            conn.commit()
            logger.info("Datenbankschema erfolgreich initialisiert")

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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tickets 
                    (title, description, status, priority, created_by, category, due_date, estimated_time, created_at, updated_at)
                    VALUES (?, ?, 'offen', ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, [title, description, priority, created_by, category, due_date, estimated_time])
                ticket_id = cursor.lastrowid
                conn.commit()
                return ticket_id
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            raise

    def get_ticket(self, ticket_id):
        """Gibt ein Ticket anhand seiner ID zurück."""
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
                ticket_dict = dict(zip([col[0] for col in cursor.description], ticket))
                
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

    def add_auftrag_details(self, ticket_id, **kwargs):
        """Fügt einen neuen Auftrag-Details-Datensatz für ein Ticket hinzu oder aktualisiert einen bestehenden."""
        try:
            # Validiere und bereite die Daten vor
            data = {
                'bereich': str(kwargs.get('bereich', '')).strip(),
                'auftraggeber_intern': 1 if kwargs.get('auftraggeber_intern') in [True, 1, '1', 'true', 'True'] else 0,
                'auftraggeber_extern': 1 if kwargs.get('auftraggeber_extern') in [True, 1, '1', 'true', 'True'] else 0,
                'auftraggeber_name': str(kwargs.get('auftraggeber_name', '')).strip(),
                'kontakt': str(kwargs.get('kontakt', '')).strip(),
                'auftragsbeschreibung': str(kwargs.get('auftragsbeschreibung', '')).strip(),
                'ausgefuehrte_arbeiten': str(kwargs.get('ausgefuehrte_arbeiten', '')).strip(),
                'arbeitsstunden': str(kwargs.get('arbeitsstunden', '')).strip(),
                'leistungskategorie': str(kwargs.get('leistungskategorie', '')).strip(),
                'fertigstellungstermin': str(kwargs.get('fertigstellungstermin', '')).strip(),
                'gesamtsumme': float(kwargs.get('gesamtsumme', 0))
            }
            
            logger.info(f"Vorbereitete Daten für Ticket {ticket_id}: {data}")
            
            # Prüfe ob bereits ein Eintrag existiert
            existing = self.get_auftrag_details(ticket_id)
            
            if existing:
                # Wenn ein Eintrag existiert, aktualisiere ihn
                self.update_auftrag_details(ticket_id, **data)
                logger.info(f"Auftragsdetails für Ticket {ticket_id} aktualisiert")
            else:
                # Wenn kein Eintrag existiert, füge einen neuen hinzu
                felder = list(data.keys())
                werte = list(data.values())
                logger.info(f"add_auftrag_details: ticket_id={ticket_id}, werte={werte}")
                sql = f"""
                    INSERT INTO auftrag_details (
                        ticket_id, {', '.join(felder)}
                    ) VALUES (
                        ?, {', '.join(['?']*len(felder))}
                    )
                """
                self.query(sql, [ticket_id] + werte)
                logger.info(f"Neue Auftragsdetails für Ticket {ticket_id} hinzugefügt")
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen/Aktualisieren der Auftragsdetails: {str(e)}")
            raise

    def update_auftrag_details(self, ticket_id, **kwargs):
        """Aktualisiert nur die übergebenen Felder der Auftrag-Details für ein Ticket. Legt einen neuen Eintrag an, falls keiner existiert."""
        try:
            # Hole aktuelle Auftragsdetails
            current_details = self.get_auftrag_details(ticket_id)
            
            # Bereite die Werte für das Update vor
            update_values = []
            for key in ['bereich', 'auftraggeber_intern', 'auftraggeber_extern', 'auftraggeber_name', 
                       'kontakt', 'auftragsbeschreibung', 'ausgefuehrte_arbeiten', 'arbeitsstunden', 
                       'leistungskategorie', 'fertigstellungstermin', 'gesamtsumme']:
                if key in kwargs:
                    value = kwargs[key]
                    if isinstance(value, bool):
                        value = 1 if value else 0
                    update_values.append(value)
                else:
                    update_values.append(current_details.get(key, ''))
            
            # Füge ticket_id am Ende hinzu
            update_values.append(ticket_id)
            
            logging.info(f"update_auftrag_details: ticket_id={ticket_id}, werte={update_values}")
            
            # Führe das Update durch
            query = """
                UPDATE auftrag_details 
                SET bereich = ?, 
                    auftraggeber_intern = ?, 
                    auftraggeber_extern = ?, 
                    auftraggeber_name = ?, 
                    kontakt = ?, 
                    auftragsbeschreibung = ?, 
                    ausgefuehrte_arbeiten = ?, 
                    arbeitsstunden = ?, 
                    leistungskategorie = ?, 
                    fertigstellungstermin = ?,
                    gesamtsumme = ?
                WHERE ticket_id = ?
            """
            affected = self.query(query, update_values)
            logging.info(f"Auftragsdetails für Ticket {ticket_id} erfolgreich aktualisiert, betroffene Zeilen: {affected}")
            
            # Wenn kein Eintrag aktualisiert wurde, lege einen neuen an
            if affected == 0:
                logger.info(f"Kein Eintrag für ticket_id={ticket_id} vorhanden, lege neuen Eintrag an.")
                felder = ['bereich', 'auftraggeber_intern', 'auftraggeber_extern', 'auftraggeber_name',
                          'kontakt', 'auftragsbeschreibung', 'ausgefuehrte_arbeiten', 'arbeitsstunden',
                          'leistungskategorie', 'fertigstellungstermin', 'gesamtsumme']
                if current_details:
                    werte = [kwargs.get(f, current_details.get(f, '')) for f in felder]
                else:
                    werte = [kwargs.get(f, '') for f in felder]
                sql = f"""
                    INSERT INTO auftrag_details (
                        ticket_id, {', '.join(felder)}
                    ) VALUES (
                        ?, {', '.join(['?']*len(felder))}
                    )
                """
                self.query(sql, [ticket_id] + werte)
                logger.info(f"Neuer Eintrag in auftrag_details für ticket_id={ticket_id} angelegt.")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Aktualisieren der Auftragsdetails für Ticket {ticket_id}: {str(e)}")
            return False

    def get_auftrag_details(self, ticket_id):
        """Gibt die Auftrag-Details für ein Ticket zurück (oder None)."""
        try:
            sql = """
                SELECT 
                    id, 
                    ticket_id, 
                    COALESCE(bereich, '') as bereich,
                    CASE 
                        WHEN auftraggeber_intern = 1 THEN 1 
                        ELSE 0 
                    END as auftraggeber_intern,
                    CASE 
                        WHEN auftraggeber_extern = 1 THEN 1 
                        ELSE 0 
                    END as auftraggeber_extern,
                    COALESCE(auftraggeber_name, '') as auftraggeber_name,
                    COALESCE(kontakt, '') as kontakt,
                    COALESCE(auftragsbeschreibung, '') as auftragsbeschreibung,
                    COALESCE(ausgefuehrte_arbeiten, '') as ausgefuehrte_arbeiten,
                    COALESCE(arbeitsstunden, '') as arbeitsstunden,
                    COALESCE(leistungskategorie, '') as leistungskategorie,
                    COALESCE(fertigstellungstermin, '') as fertigstellungstermin,
                    COALESCE(gesamtsumme, 0) as gesamtsumme,
                    erstellt_am
                FROM auftrag_details 
                WHERE ticket_id = ?
            """
            result = self.query(sql, [ticket_id], one=True)
            
            if result:
                # Konvertiere die Boolean-Werte
                result = dict(result)
                result['auftraggeber_intern'] = bool(result['auftraggeber_intern'])
                result['auftraggeber_extern'] = bool(result['auftraggeber_extern'])
                
                # Stelle sicher, dass alle String-Felder nicht None sind
                string_fields = ['bereich', 'auftraggeber_name', 'kontakt', 'auftragsbeschreibung', 
                               'ausgefuehrte_arbeiten', 'arbeitsstunden', 'leistungskategorie', 
                               'fertigstellungstermin']
                for field in string_fields:
                    if result[field] is None:
                        result[field] = ''
                
                logger.info(f"get_auftrag_details: ticket_id={ticket_id}, result={result}")
                return result
            return None
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Auftragsdetails: {str(e)}")
            return None

    def add_auftrag_material(self, ticket_id, material, menge, einzelpreis):
        """Fügt eine Materialposition zu einem Ticket hinzu."""
        sql = """
            INSERT INTO auftrag_material (ticket_id, material, menge, einzelpreis)
            VALUES (?, ?, ?, ?)
        """
        self.query(sql, [ticket_id, material, menge, einzelpreis])

    def get_auftrag_material(self, ticket_id):
        """Gibt alle Materialpositionen für ein Ticket zurück."""
        sql = "SELECT * FROM auftrag_material WHERE ticket_id = ?"
        return self.query(sql, [ticket_id])

    def delete_auftrag_material(self, material_id):
        """Löscht eine Materialposition anhand ihrer ID."""
        sql = "DELETE FROM auftrag_material WHERE id = ?"
        self.query(sql, [material_id])

    def update_auftrag_material(self, ticket_id, material_list):
        """Aktualisiert die Materialliste für ein Ticket"""
        try:
            # Lösche alte Materialeinträge
            self.query("DELETE FROM auftrag_material WHERE ticket_id = ?", [ticket_id])
            
            # Füge neue Materialeinträge hinzu
            for material in material_list:
                if material.get('material') and material.get('menge') and material.get('einzelpreis'):
                    self.add_auftrag_material(
                        ticket_id=ticket_id,
                        material=material['material'],
                        menge=float(material['menge']),
                        einzelpreis=float(material['einzelpreis'])
                    )
            
            return True
        except Exception as e:
            logging.error(f"Fehler beim Aktualisieren der Materialliste: {str(e)}")
            raise e

    def migrate_schema(self):
        """Führt einfache Migrationen durch (legt fehlende Tabellen an)."""
        # Importiere das neue Migrationsskript und führe es aus
        try:
            from migrate_full_schema import migrate_full_schema, TICKETS_SCHEMA
            migrate_full_schema(self.db_path, TICKETS_SCHEMA)
        except Exception as e:
            print(f"Migration konnte nicht ausgeführt werden: {e}")
        # ... bisheriger Code ... 

    def get_ticket_assignments(self, ticket_id):
        """Holt alle zugewiesenen Nutzer für ein Ticket."""
        return self.query(
            """
            SELECT username
            FROM ticket_assignments
            WHERE ticket_id = ?
            ORDER BY username
            """,
            [ticket_id]
        )

    def set_ticket_assignments(self, ticket_id, usernames):
        """Setzt die Zuweisungen für ein Ticket."""
        try:
            # Lösche alte Zuweisungen
            self.query("DELETE FROM ticket_assignments WHERE ticket_id = ?", [ticket_id])
            
            # Füge neue Zuweisungen hinzu
            for username in usernames:
                self.query("""
                    INSERT INTO ticket_assignments (ticket_id, username)
                    VALUES (?, ?)
                """, [ticket_id, username])
            
            return True
        except Exception as e:
            logging.error(f"Fehler beim Setzen der Ticket-Zuweisungen: {str(e)}")
            return False

    def delete_ticket_assignments(self, ticket_id):
        """Löscht alle Zuweisungen für ein Ticket."""
        self.query("DELETE FROM ticket_assignments WHERE ticket_id = ?", [ticket_id])

    @staticmethod
    def create_tables():
        """Erstellt die notwendigen Tabellen, falls sie nicht existieren."""
        with Database.get_db() as db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS ticket_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                    UNIQUE(ticket_id, username)
                )
            ''')
            db.commit() 