import sqlite3
import logging
from werkzeug.security import generate_password_hash
import os
import time

logger = logging.getLogger(__name__)

# Die Schema-Version, die die aktuelle Codebasis erwartet
CURRENT_SCHEMA_VERSION = 10

def get_db_connection(db_path, timeout=30):
    """Erstellt eine Datenbankverbindung mit Timeout."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_db_schema_version(conn):
    """Holt die aktuelle Schema-Version aus der Datenbank."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(version) FROM schema_version")
        version = cursor.fetchone()[0]
        return version if version is not None else 0
    except sqlite3.OperationalError:
        return 0

def initialize_schema(db_path):
    """Initialisiert das Datenbankschema."""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Führe das initiale Schema aus
            with open('app/migrations/init_schema.sql', 'r') as f:
                sql = f.read()
                cursor.executescript(sql)
            
            conn.commit()
            logger.info("Datenbankschema erfolgreich initialisiert")
            return True
            
    except Exception as e:
        logger.error(f"Fehler bei der Schema-Initialisierung: {str(e)}")
        return False

def run_migrations(db_path):
    """Führt die Schema-Initialisierung durch."""
    try:
        logger.info(f"Starte Schema-Initialisierung für {db_path}")
        
        # Prüfe ob die Datenbank existiert
        if not os.path.exists(db_path):
            logger.info("Datenbank existiert nicht, erstelle neue Datenbank")
            return initialize_schema(db_path)
            
        # Hole aktuelle Schema-Version
        with get_db_connection(db_path) as conn:
            current_version = get_db_schema_version(conn)
            logger.info(f"Aktuelle Schema-Version: {current_version}")
            
            # Wenn die Version nicht aktuell ist, initialisiere neu
            if current_version < CURRENT_SCHEMA_VERSION:
                logger.info("Schema ist nicht aktuell, führe Neuinitialisierung durch")
                return initialize_schema(db_path)
            
        logger.info("Schema ist bereits aktuell")
        return True
        
    except Exception as e:
        logger.error(f"Fehler bei der Schema-Initialisierung: {str(e)}")
        raise

if __name__ == '__main__':
    ticket_db_path = os.path.join('app', 'database', 'tickets.db')
    run_migrations(ticket_db_path) 