import sqlite3
import logging
from werkzeug.security import generate_password_hash
import os

logger = logging.getLogger(__name__)

# Die Schema-Version, die die aktuelle Codebasis erwartet
CURRENT_SCHEMA_VERSION = 2

def get_db_schema_version(conn):
    """Liest die Schema-Version aus der settings-Tabelle."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'schema_version'")
        result = cursor.fetchone()
        if result:
            return int(result[0])
        else:
            # Wenn kein Eintrag existiert, prüfen wir, ob die users-Tabelle existiert.
            # Wenn ja, ist es wahrscheinlich Schema 2 (oder höher, aber ohne Versionseintrag).
            # Wenn nein, ist es Schema 1.
            try:
                cursor.execute("SELECT 1 FROM users LIMIT 1")
                logger.warning("Kein 'schema_version'-Eintrag gefunden, aber 'users'-Tabelle existiert. Nehme Version 2 an.")
                # Setze die Version für die Zukunft
                set_db_schema_version(conn, 2)
                conn.commit() # Sicherstellen, dass die Version sofort geschrieben wird
                return 2
            except sqlite3.OperationalError:
                logger.warning("Kein 'schema_version'-Eintrag und keine 'users'-Tabelle gefunden. Nehme Version 1 an.")
                return 1 # Oder 0, je nachdem, wie wir zählen wollen. 1 passt hier gut.
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Schema-Version: {e}. Nehme Version 1 an.")
        return 1

def set_db_schema_version(conn, version):
    """Schreibt die Schema-Version in die settings-Tabelle."""
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                       ['schema_version', str(version)])
        logger.info(f"Datenbank Schema-Version auf {version} gesetzt.")
    except Exception as e:
        logger.error(f"Fehler beim Setzen der Schema-Version auf {version}: {e}")
        raise # Den Fehler weitergeben, damit die Migration als fehlgeschlagen gilt

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

        # 2. Standard-Benutzer hinzufügen (nur wenn Tabelle leer war/ist)
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            logger.info("Füge Standard-Benutzer hinzu...")
            try:
                 # Verwende INSERT OR IGNORE, falls doch ein Constraint verletzt wird
                cursor.execute(
                    'INSERT OR IGNORE INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, 1)',
                    ('Admin', generate_password_hash('BTZ-Scandy25'), 'admin')
                )
                cursor.execute(
                    'INSERT OR IGNORE INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, 1)',
                    ('Mitarbeiter', generate_password_hash('BTZ-BT11'), 'mitarbeiter')
                )
                cursor.execute(
                    'INSERT OR IGNORE INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, 1)',
                    ('Test', generate_password_hash('test'), 'anwender')
                )
                logger.info("Standard-Benutzerkonten hinzugefügt (oder bereits vorhanden).")
            except Exception as e_insert:
                 logger.error(f"Fehler beim Einfügen der Standardbenutzer: {e_insert}")
                 # Optional: Fehler weitergeben, wenn kritisch? Hier eher nicht.
        else:
             logger.info("'users'-Tabelle ist nicht leer, überspringe das Hinzufügen von Standard-Benutzern.")


        # 3. Homepage Notices Tabelle erstellen (IF NOT EXISTS ist sicher)
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


def run_migrations(db_path):
    """Prüft die Schema-Version und führt notwendige Migrationen aus."""
    logger.info(f"Prüfe Datenbank-Schema-Migrationen für: {db_path}")
    if not os.path.exists(db_path):
        logger.warning(f"Datenbankdatei {db_path} existiert nicht. Migrationen werden übersprungen (wird neu erstellt).")
        return

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;") # Sicherstellen, dass Foreign Keys aktiv sind

        current_version = get_db_schema_version(conn)
        logger.info(f"Aktuelle Datenbank Schema-Version: {current_version}")
        logger.info(f"Erwartete App Schema-Version: {CURRENT_SCHEMA_VERSION}")

        if current_version < CURRENT_SCHEMA_VERSION:
            logger.warning(f"Datenbank-Schema (v{current_version}) ist veraltet. Starte Migrationen...")

            # --- Migration v1 -> v2 ---
            if current_version < 2:
                if not _migrate_v1_to_v2(conn):
                    raise Exception("Migration von v1 auf v2 fehlgeschlagen!")
                current_version = 2 # Update für den Fall weiterer Migrationen

            # --- Migration v2 -> v3 (Beispiel für Zukunft) ---
            # if current_version < 3:
            #    if not _migrate_v2_to_v3(conn):
            #        raise Exception("Migration von v2 auf v3 fehlgeschlagen!")
            #    current_version = 3

            # ... weitere Migrationen hier hinzufügen ...

            conn.commit() # Änderungen speichern
            logger.info("Datenbank-Migrationen erfolgreich abgeschlossen.")
        elif current_version > CURRENT_SCHEMA_VERSION:
             logger.warning(f"Datenbank-Schema (v{current_version}) ist neuer als von der App erwartet (v{CURRENT_SCHEMA_VERSION}). Möglicherweise Inkompatibilitäten!")
        else:
            logger.info("Datenbank-Schema ist aktuell.")

    except sqlite3.Error as e:
        logger.error(f"SQLite-Fehler während der Migration: {e}", exc_info=True)
        if conn:
            conn.rollback() # Änderungen rückgängig machen bei Fehler
        raise # Fehler weitergeben, um App-Start ggf. zu verhindern
    except Exception as e:
        logger.error(f"Allgemeiner Fehler während der Migration: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            logger.info("Datenbankverbindung für Migration geschlossen.") 