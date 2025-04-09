import sqlite3
from werkzeug.security import generate_password_hash
import os
from app.config import Config

def init_users(app=None):
    """Initialisiert die Benutzerdatenbank und erstellt die Benutzer-Accounts"""
    db_path = os.path.join(Config.DATABASE_DIR, 'users.db')
    
    # Stelle sicher, dass das Verzeichnis existiert
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        # Erstelle users Tabelle (vereinfacht)
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
            
        conn.commit()

if __name__ == '__main__':
    init_users() 