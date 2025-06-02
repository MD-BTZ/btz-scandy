import sqlite3
import logging
from werkzeug.security import generate_password_hash
import os
import time

logger = logging.getLogger(__name__)

# Die Schema-Version, die die aktuelle Codebasis erwartet
CURRENT_SCHEMA_VERSION = 5

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
        if result and str(result[0]).strip().isdigit():
            return int(result[0])
        # Wenn keine schema_version Tabelle existiert, prüfen wir die settings Tabelle
        cursor.execute("SELECT value FROM settings WHERE key = 'schema_version'")
        result = cursor.fetchone()
        if result and str(result[0]).strip().isdigit():
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

def _migrate_ticket_db(conn):
    """Erstellt die Ticket-Datenbank mit allen notwendigen Tabellen"""
    try:
        # Erstelle die Tabellen
        conn.execute("""
            CREATE TABLE IF NOT EXISTS application_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                category TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS application_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                document_type TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                company_name TEXT NOT NULL,
                position TEXT NOT NULL,
                contact_person TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                address TEXT,
                generated_content TEXT,
                status TEXT DEFAULT 'created',
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cv_path TEXT,
                certificate_paths TEXT,
                output_path TEXT,
                FOREIGN KEY (template_id) REFERENCES application_templates(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS application_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                response_type TEXT NOT NULL,
                response_date DATE,
                content TEXT,
                next_steps TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id)
            )
        """)

        conn.commit()
        return True

    except Exception as e:
        logging.error(f"Fehler bei der Datenbankinitialisierung: {str(e)}")
        return False

def run_migrations(db_path):
    """Führt alle notwendigen Migrationen für die Ticket-Datenbank durch"""
    try:
        logger.info(f"Starte Migration für {db_path}")
        
        # Prüfe ob die Datenbank existiert
        if not os.path.exists(db_path):
            logger.info("Datenbank existiert nicht, erstelle neue Datenbank")
            _migrate_ticket_db(db_path)
            return
            
        # Hole aktuelle Schema-Version
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_version")
            current_version = cursor.fetchone()[0] or 0
            logger.info(f"Aktuelle Schema-Version: {current_version}")
            
        # Führe Migrationen basierend auf Version durch
        if current_version < 1:
            logger.info("Führe Migration von v1 zu v2 durch")
            _migrate_v1_to_v2(db_path)
        if current_version < 2:
            logger.info("Führe Migration von v2 zu v3 durch")
            _migrate_v2_to_v3(db_path)
        if current_version < 3:
            logger.info("Führe Migration von v3 zu v4 durch")
            _migrate_v3_to_v4(db_path)
            
        logger.info("Migration erfolgreich abgeschlossen")
        
    except Exception as e:
        logger.error(f"Fehler bei der Migration: {str(e)}")
        raise

def run_ticket_db_migrations():
    """Führt Migrationen für die Ticket-Datenbank durch."""
    ticket_db_path = os.path.join('app', 'database', 'tickets.db')
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
            _migrate_ticket_db(conn)
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

if __name__ == '__main__':
    run_ticket_db_migrations() 