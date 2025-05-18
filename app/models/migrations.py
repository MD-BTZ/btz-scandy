import sqlite3
import logging
from werkzeug.security import generate_password_hash
import os
import time

logger = logging.getLogger(__name__)

# Die Schema-Version, die die aktuelle Codebasis erwartet
CURRENT_SCHEMA_VERSION = 4

def get_db_connection(db_path, timeout=30):
    """Erstellt eine Datenbankverbindung mit Timeout."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_db_schema_version(conn):
    """Liest die Schema-Version aus der settings-Tabelle."""
    try:
        cursor = conn.cursor()
        
        # Zuerst prüfen wir die schema_version Tabelle
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        result = cursor.fetchone()
        if result:
            return int(result[0])
            
        # Wenn keine schema_version Tabelle existiert, prüfen wir die settings Tabelle
        cursor.execute("SELECT value FROM settings WHERE key = 'schema_version'")
        result = cursor.fetchone()
        if result:
            return int(result[0])
            
        # Wenn kein Eintrag existiert, prüfen wir, ob die users-Tabelle existiert
        try:
            cursor.execute("SELECT 1 FROM users LIMIT 1")
            logger.warning("Kein Schema-Versionseintrag gefunden, aber 'users'-Tabelle existiert. Nehme Version 2 an.")
            return 2
        except sqlite3.OperationalError:
            logger.warning("Kein Schema-Versionseintrag und keine 'users'-Tabelle gefunden. Nehme Version 1 an.")
            return 1
            
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Schema-Version: {e}. Nehme Version 1 an.")
        return 1

def set_db_schema_version(conn, version):
    """Schreibt die Schema-Version in beide Tabellen."""
    try:
        cursor = conn.cursor()
        
        # In settings Tabelle
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                       ['schema_version', str(version)])
                      
        # In schema_version Tabelle
        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                      [version])
                      
        logger.info(f"Datenbank Schema-Version auf {version} gesetzt.")
    except Exception as e:
        logger.error(f"Fehler beim Setzen der Schema-Version auf {version}: {e}")
        raise

def _migrate_v1_to_v2(conn):
    """Migration von Schema-Version 1 auf 2. Fügt users und homepage_notices hinzu."""
    logger.info("Führe Migration von Schema v1 auf v2 durch...")
    cursor = conn.cursor()

    try:
        # 1. Users-Tabelle erstellen (IF NOT EXISTS ist sicher)
        logger.info("Erstelle 'users'-Tabelle (falls nicht vorhanden)...")
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'mitarbeiter', 'anwender')),
            is_active INTEGER DEFAULT 1
        )''')

        # 2. Homepage Notices Tabelle erstellen (IF NOT EXISTS ist sicher)
        logger.info("Erstelle 'homepage_notices'-Tabelle (falls nicht vorhanden)...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS homepage_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 4. Initiale Hinweise einfügen (nur wenn Tabelle leer war/ist)
        cursor.execute('SELECT COUNT(*) FROM homepage_notices')
        if cursor.fetchone()[0] == 0:
            logger.info("Füge Standard-Hinweise hinzu...")
            cursor.execute('''
                INSERT INTO homepage_notices (title, content, priority)
                VALUES
                    ('Willkommen', 'Willkommen im Scandy-System. Hier können Sie Werkzeuge und Verbrauchsmaterialien verwalten.', 1),
                    ('Hinweis', 'Bitte melden Sie sich an, um das System zu nutzen.', 2)
            ''')
        else:
            logger.info("'homepage_notices'-Tabelle ist nicht leer, überspringe das Hinzufügen von Standard-Hinweisen.")

        # 5. Schema-Version aktualisieren
        set_db_schema_version(conn, 2)

        logger.info("Migration von v1 auf v2 erfolgreich abgeschlossen.")
        return True

    except Exception as e:
        logger.error(f"Fehler während der Migration von v1 auf v2: {e}", exc_info=True)
        return False

def _migrate_v2_to_v3(conn):
    """Migration von Schema-Version 2 auf 3. Aktualisiert die description für Kategorien und Standorte."""
    logger.info("Führe Migration von Schema v2 auf v3 durch...")
    cursor = conn.cursor()

    try:
        # Aktualisiere die description für bestehende Kategorien
        cursor.execute('''
            UPDATE settings 
            SET description = 'both'
            WHERE key LIKE 'category_%'
            AND key NOT LIKE '%_tools'
            AND key NOT LIKE '%_consumables'
            AND description IS NULL
        ''')

        # Aktualisiere die description für bestehende Standorte
        cursor.execute('''
            UPDATE settings 
            SET description = 'both'
            WHERE key LIKE 'location_%'
            AND key NOT LIKE '%_tools'
            AND key NOT LIKE '%_consumables'
            AND description IS NULL
        ''')

        # Füge die neue Schema-Version hinzu
        cursor.execute('''
            INSERT INTO schema_version (version)
            VALUES (3)
        ''')

        conn.commit()
        logger.info("Migration von Schema v2 auf v3 erfolgreich abgeschlossen.")
    except Exception as e:
        logger.error(f"Fehler bei der Migration von Schema v2 auf v3: {e}")
        conn.rollback()
        raise

def _migrate_v3_to_v4(conn):
    """Migration von Version 3 auf Version 4"""
    try:
        cursor = conn.cursor()
        
        # Prüfe ob die alte Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consumable_usage'")
        if cursor.fetchone():
            # Benenne die Tabelle um
            cursor.execute("ALTER TABLE consumable_usage RENAME TO consumable_usages")
            logger.info("Tabelle consumable_usage zu consumable_usages umbenannt")
        
        # Füge modified_at Spalte hinzu, falls sie noch nicht existiert
        try:
            cursor.execute('ALTER TABLE consumable_usages ADD COLUMN modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            cursor.execute('UPDATE consumable_usages SET modified_at = used_at WHERE modified_at IS NULL')
            logger.info("modified_at Spalte zur consumable_usages Tabelle hinzugefügt")
        except Exception as e:
            logger.info(f"modified_at Spalte existiert bereits oder konnte nicht hinzugefügt werden: {e}")
        
        # Aktualisiere die Schema-Version
        set_db_schema_version(conn, 4)
        logger.info("Schema-Version auf 4 aktualisiert")
        
        return True
    except Exception as e:
        logger.error(f"Fehler bei Migration v3->v4: {e}")
        return False

def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def _migrate_ticket_db(conn):
    """Migration der Ticket-Datenbank auf Version 3."""
    logger.info("Führe Migration der Ticket-Datenbank auf Version 3 durch...")
    cursor = conn.cursor()

    try:
        # Prüfe ob schema_version Tabelle existiert
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Hole aktuelle Version
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        result = cursor.fetchone()
        current_version = result[0] if result else 0

        if current_version < 3:
            # Füge neue Spalten zur tickets Tabelle hinzu, nur wenn sie noch nicht existieren
            if not _column_exists(cursor, "tickets", "last_modified_by"):
                cursor.execute("ALTER TABLE tickets ADD COLUMN last_modified_by TEXT;")
            if not _column_exists(cursor, "tickets", "last_modified_at"):
                cursor.execute("ALTER TABLE tickets ADD COLUMN last_modified_at TIMESTAMP;")
            if not _column_exists(cursor, "tickets", "category"):
                cursor.execute("ALTER TABLE tickets ADD COLUMN category TEXT;")
            if not _column_exists(cursor, "tickets", "due_date"):
                cursor.execute("ALTER TABLE tickets ADD COLUMN due_date TIMESTAMP;")
            if not _column_exists(cursor, "tickets", "estimated_time"):
                cursor.execute("ALTER TABLE tickets ADD COLUMN estimated_time INTEGER;")
            if not _column_exists(cursor, "tickets", "actual_time"):
                cursor.execute("ALTER TABLE tickets ADD COLUMN actual_time INTEGER;")
            if not _column_exists(cursor, "tickets", "response"):
                cursor.execute("ALTER TABLE tickets ADD COLUMN response TEXT;")

            # Füge neue Spalten zur ticket_notes Tabelle hinzu, nur wenn sie noch nicht existieren
            if not _column_exists(cursor, "ticket_notes", "modified_at"):
                cursor.execute("ALTER TABLE ticket_notes ADD COLUMN modified_at TIMESTAMP;")
            if not _column_exists(cursor, "ticket_notes", "modified_by"):
                cursor.execute("ALTER TABLE ticket_notes ADD COLUMN modified_by TEXT;")
            if not _column_exists(cursor, "ticket_notes", "is_private"):
                cursor.execute("ALTER TABLE ticket_notes ADD COLUMN is_private BOOLEAN DEFAULT 0;")

            # Erstelle ticket_messages Tabelle
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

            # Erstelle ticket_history Tabelle
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

            # Aktualisiere Schema-Version
            cursor.execute("INSERT INTO schema_version (version) VALUES (3)")
            conn.commit()
            logger.info("Ticket-Datenbank erfolgreich auf Version 3 migriert")
            return True

        logger.info("Ticket-Datenbank ist bereits auf Version 3")
        return True

    except Exception as e:
        logger.error(f"Fehler bei der Ticket-Datenbank-Migration: {str(e)}")
        conn.rollback()
        return False

def run_migrations(db_path):
    """Prüft die Schema-Version und führt notwendige Migrationen aus."""
    logger.info(f"Prüfe Datenbank-Schema-Migrationen für: {db_path}")
    if not os.path.exists(db_path):
        logger.warning(f"Datenbankdatei {db_path} existiert nicht. Migrationen werden übersprungen (wird neu erstellt).")
        return

    conn = None
    max_retries = 3
    retry_delay = 1  # Sekunden

    for attempt in range(max_retries):
        try:
            conn = get_db_connection(db_path)
            current_version = get_db_schema_version(conn)
            logger.info(f"Aktuelle Datenbank Schema-Version: {current_version}")
            logger.info(f"Erwartete App Schema-Version: {CURRENT_SCHEMA_VERSION}")

            if current_version < CURRENT_SCHEMA_VERSION:
                logger.warning(f"Datenbank-Schema (v{current_version}) ist veraltet. Starte Migrationen...")

                # --- Migration v1 -> v2 ---
                if current_version < 2:
                    if not _migrate_v1_to_v2(conn):
                        raise Exception("Migration von v1 auf v2 fehlgeschlagen!")
                    current_version = 2

                # --- Migration v2 -> v3 ---
                if current_version < 3:
                    if not _migrate_v2_to_v3(conn):
                        raise Exception("Migration von v2 auf v3 fehlgeschlagen!")
                    current_version = 3

                # --- Migration v3 -> v4 ---
                if current_version < 4:
                    if not _migrate_v3_to_v4(conn):
                        raise Exception("Migration von v3 auf v4 fehlgeschlagen!")
                    current_version = 4

                conn.commit()
                logger.info("Datenbank-Migrationen erfolgreich abgeschlossen.")
            elif current_version > CURRENT_SCHEMA_VERSION:
                logger.warning(f"Datenbank-Schema (v{current_version}) ist neuer als von der App erwartet (v{CURRENT_SCHEMA_VERSION}). Möglicherweise Inkompatibilitäten!")
            else:
                logger.info("Datenbank-Schema ist aktuell.")

            break  # Erfolgreich, keine weiteren Versuche nötig

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"Datenbank ist gesperrt. Versuche {attempt + 1} von {max_retries}...")
                    time.sleep(retry_delay)
                    continue
            logger.error(f"Fehler bei der Datenbank-Migration: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()

def run_ticket_db_migrations(ticket_db_path):
    """Führt Migrationen für die Ticket-Datenbank durch."""
    logger.info(f"Prüfe Ticket-Datenbank-Migrationen für: {ticket_db_path}")
    if not os.path.exists(ticket_db_path):
        logger.warning(f"Ticket-Datenbankdatei {ticket_db_path} existiert nicht. Migrationen werden übersprungen (wird neu erstellt).")
        return

    conn = None
    max_retries = 3
    retry_delay = 1  # Sekunden

    for attempt in range(max_retries):
        try:
            conn = get_db_connection(ticket_db_path)
            if not _migrate_ticket_db(conn):
                raise Exception("Ticket-Datenbank-Migration fehlgeschlagen!")
            break  # Erfolgreich, keine weiteren Versuche nötig

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"Ticket-Datenbank ist gesperrt. Versuche {attempt + 1} von {max_retries}...")
                    time.sleep(retry_delay)
                    continue
            logger.error(f"Fehler bei der Ticket-Datenbank-Migration: {str(e)}")
            raise
        finally:
            if conn:
                conn.close() 