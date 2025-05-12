import sqlite3
import logging
from werkzeug.security import generate_password_hash
import os
import time

logger = logging.getLogger(__name__)

# Die Schema-Version, die die aktuelle Codebasis erwartet
CURRENT_SCHEMA_VERSION = 2

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

                conn.commit()
                logger.info("Datenbank-Migrationen erfolgreich abgeschlossen.")
            elif current_version > CURRENT_SCHEMA_VERSION:
                logger.warning(f"Datenbank-Schema (v{current_version}) ist neuer als von der App erwartet (v{CURRENT_SCHEMA_VERSION}). Möglicherweise Inkompatibilitäten!")
            else:
                logger.info("Datenbank-Schema ist aktuell.")

            break  # Erfolgreich, keine weiteren Versuche nötig

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                logger.warning(f"Datenbank ist gesperrt (Versuch {attempt + 1}/{max_retries}). Warte {retry_delay} Sekunden...")
                if conn:
                    conn.close()
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponentielles Backoff
                continue
            raise
        except Exception as e:
            logger.error(f"Fehler während der Migration: {e}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
                logger.info("Datenbankverbindung für Migration geschlossen.") 