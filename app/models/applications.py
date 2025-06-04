import sqlite3
import os
from pathlib import Path
from datetime import datetime
from app.models.database import Database

def create_application_tables():
    """Erstellt die notwendigen Tabellen für das Bewerbungssystem"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Tabelle für Bewerbungsvorlagen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bewerbungsvorlagen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dateiname TEXT NOT NULL,
                kategorie TEXT,
                erstellt_von TEXT NOT NULL,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ist_aktiv BOOLEAN DEFAULT 1,
                FOREIGN KEY (erstellt_von) REFERENCES users(username)
            )
        ''')
        
        # Tabelle für Bewerbungsdokumente
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bewerbungsdokumente (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vorlagen_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                beschreibung TEXT,
                dateipfad TEXT NOT NULL,
                ist_erforderlich BOOLEAN DEFAULT 1,
                erstellt_von TEXT NOT NULL,
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vorlagen_id) REFERENCES bewerbungsvorlagen(id) ON DELETE CASCADE,
                FOREIGN KEY (erstellt_von) REFERENCES users(username)
            )
        ''')
        
        # Tabelle für Bewerbungen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bewerbungen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vorlagen_id INTEGER NOT NULL,
                bewerber TEXT NOT NULL,
                status TEXT DEFAULT 'in_bearbeitung',
                erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (vorlagen_id) REFERENCES bewerbungsvorlagen(id),
                FOREIGN KEY (bewerber) REFERENCES users(username)
            )
        ''')
        
        # Tabelle für Bewerbungsdokumente Uploads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bewerbungsdokumente_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bewerbung_id INTEGER NOT NULL,
                dokument_id INTEGER NOT NULL,
                dateipfad TEXT NOT NULL,
                hochgeladen_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bewerbung_id) REFERENCES bewerbungen(id) ON DELETE CASCADE,
                FOREIGN KEY (dokument_id) REFERENCES bewerbungsdokumente(id)
            )
        ''')
        
        # Index für erstellt_von in bewerbungsvorlagen
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_bewerbungsvorlagen_erstellt_von 
            ON bewerbungsvorlagen(erstellt_von)
        ''')
        
        conn.commit()
        print("Bewerbungstabellen erfolgreich erstellt")

class Bewerbungsvorlage:
    """Klasse für die Verwaltung von Bewerbungsvorlagen"""
    
    @staticmethod
    def create(name, dateiname, kategorie=None, erstellt_von=None):
        """Erstellt eine neue Bewerbungsvorlage"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bewerbungsvorlagen (name, dateiname, kategorie, erstellt_von)
                VALUES (?, ?, ?, ?)
            ''', (name, dateiname, kategorie, erstellt_von))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_all():
        """Gibt alle aktiven Bewerbungsvorlagen zurück"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, dateiname, kategorie 
                FROM bewerbungsvorlagen 
                WHERE ist_aktiv = 1
            ''')
            return cursor.fetchall()
    
    @staticmethod
    def get_by_id(vorlagen_id):
        """Gibt eine Bewerbungsvorlage anhand ihrer ID zurück"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bewerbungsvorlagen 
                WHERE id = ? AND ist_aktiv = 1
            ''', [vorlagen_id])
            return cursor.fetchone()

class Bewerbungsdokument:
    """Klasse für die Verwaltung von Dokumentenvorlagen"""
    
    @staticmethod
    def create(vorlagen_id, name, dateipfad, beschreibung=None, ist_erforderlich=True, erstellt_von=None):
        """Erstellt eine neue Dokumentenvorlage"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bewerbungsdokumente 
                (vorlagen_id, name, beschreibung, dateipfad, ist_erforderlich, erstellt_von)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (vorlagen_id, name, beschreibung, dateipfad, ist_erforderlich, erstellt_von))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_by_vorlagen_id(vorlagen_id):
        """Gibt alle Dokumentenvorlagen für eine Bewerbungsvorlage zurück"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bewerbungsdokumente 
                WHERE vorlagen_id = ?
            ''', [vorlagen_id])
            return cursor.fetchall() 