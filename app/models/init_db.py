import sqlite3
from werkzeug.security import generate_password_hash
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def init_db():
    """Initialisiert die Hauptdatenbank (inventory.db)"""
    # Hole die Konfiguration
    from app.config import config
    current_config = config['default']()
    
    # Verwende den korrekten Pfad aus der Config
    db_path = current_config.DATABASE
    
    # Stelle sicher, dass das Verzeichnis existiert
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    logger.info(f"Initialisiere Datenbank in: {db_path}")
    
    with sqlite3.connect(db_path) as conn:
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
                sync_status TEXT DEFAULT 'pending'
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                deleted_at TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                max_bestand INTEGER,
                lieferant TEXT,
                bestellnummer TEXT,
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
        
        # Homepage Notices Tabelle
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
        
        # Initiale Hinweise einfügen, falls die Tabelle leer ist
        cursor.execute('SELECT COUNT(*) FROM homepage_notices')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO homepage_notices (title, content, priority)
                VALUES 
                    ('Willkommen', 'Willkommen im Scandy-System. Hier können Sie Werkzeuge und Verbrauchsmaterialien verwalten.', 1),
                    ('Hinweis', 'Bitte melden Sie sich an, um das System zu nutzen.', 2)
            ''')
        
        logger.info("Datenbank-Tabellen wurden erfolgreich erstellt")
        
        conn.commit()

def init_users(app=None):
    """Initialisiert die Benutzerdatenbank und erstellt die Benutzer-Accounts"""
    # Hole die Konfiguration
    from app.config import config
    current_config = config['default']()
    
    # Verwende den korrekten Pfad aus der Config
    db_dir = os.path.dirname(current_config.DATABASE)
    db_path = os.path.join(db_dir, 'users.db')
    
    # Stelle sicher, dass das Verzeichnis existiert
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    logger.info(f"Initialisiere Benutzerdatenbank in: {db_path}")
    
    with sqlite3.connect(db_path) as conn:
        # Erstelle users Tabelle
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 1
        )''')
        
        # Prüfe ob bereits Benutzer existieren
        if not conn.execute('SELECT 1 FROM users').fetchone():
            # Erstelle die Benutzer-Accounts (alle als Admin)
            conn.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)',
                ('Admin', generate_password_hash('BTZ-Scandy25'))
            )
            conn.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)', 
                ('TechnikMA', generate_password_hash('BTZ-Admin25'))
            )
            conn.execute(
                'INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)',
                ('TechnikTN', generate_password_hash('BTZ-TN'))
            )
            
            logger.info("Standard-Benutzerkonten wurden erstellt")
            
        conn.commit()

if __name__ == '__main__':
    init_db()
    init_users() 