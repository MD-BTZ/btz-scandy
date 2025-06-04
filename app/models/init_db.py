import sqlite3
from werkzeug.security import generate_password_hash
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DATABASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'inventory.db'))

def init_db():
    """Initialisiert die Hauptdatenbank (inventory.db) - Basis-Tabellen."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP
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
                category TEXT,
                location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
                FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
            )
        ''')
        
        # Settings Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT
            )
        ''')
        
        # History Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                user_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tool Status Changes Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_status_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_barcode TEXT NOT NULL,
                old_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                reason TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tool_barcode) REFERENCES tools(barcode)
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
        
        # Consumable Lendings Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consumable_lendings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consumable_barcode TEXT NOT NULL,
                worker_barcode TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                lending_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                return_time TIMESTAMP,
                FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
                FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
            )
        ''')
        
        # Departments Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP
            )
        ''')
        
        # Homepage Notices Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS homepage_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        logger.info("Basis-Datenbank-Tabellen wurden erstellt (falls nicht vorhanden)")
        
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankinitialisierung: {e}")
        conn.rollback()
    finally:
        conn.close()

def migrate_schema(self):
    """Migriert das Datenbankschema."""
    try:
        from app.models.ticket_migrations import run_migrations
        return run_migrations(self.db_path)
    except Exception as e:
        logger.error(f"Migration konnte nicht ausgeführt werden: {e}")
        return False

if __name__ == '__main__':
    logger.warning("init_db.py direkt ausgeführt - Initialisiere nur Basis-DB.")
    init_db()
    logger.warning("Manuelle Ausführung beendet. Für Migrationen bitte die App starten.") 