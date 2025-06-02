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
            CREATE TABLE IF NOT EXISTS application_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                template_content TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Tabelle für Dokumentenvorlagen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS application_document_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                name TEXT NOT NULL,
                document_type TEXT,
                file_name TEXT,
                file_path TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (template_id) REFERENCES application_templates(id)
            )
        ''')
        
        # Tabelle für Bewerbungen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                company_name TEXT NOT NULL,
                position TEXT NOT NULL,
                contact_person TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                address TEXT,
                generated_content TEXT,
                custom_block TEXT,
                status TEXT DEFAULT 'created',
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cv_path TEXT,
                certificate_paths TEXT,
                FOREIGN KEY (template_id) REFERENCES application_templates(id)
            )
        ''')
        
        # Tabelle für Bewerbungsdokumente
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS application_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                document_type TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id)
            )
        ''')
        
        # Tabelle für Bewerbungsantworten
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS application_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                response_type TEXT,
                response_date TIMESTAMP,
                content TEXT,
                next_steps TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id)
            )
        ''')
        
        conn.commit()
        print("Bewerbungstabellen erfolgreich erstellt")

class ApplicationTemplate:
    """Klasse für die Verwaltung von Bewerbungsvorlagen"""
    
    @staticmethod
    def create(name, description=None):
        """Erstellt eine neue Bewerbungsvorlage"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO application_templates (name, template_content)
                VALUES (?, ?)
            ''', (name, description))
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
                SELECT id, name, category 
                FROM application_templates 
                WHERE is_active = 1
            ''')
            return cursor.fetchall()
    
    @staticmethod
    def get_by_id(template_id):
        """Gibt eine Bewerbungsvorlage anhand ihrer ID zurück"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM application_templates 
                WHERE id = ? AND is_active = 1
            ''', [template_id])
            return cursor.fetchone()

class ApplicationDocumentTemplate:
    """Klasse für die Verwaltung von Dokumentenvorlagen"""
    
    @staticmethod
    def create(template_id, name, file_path, description=None, is_required=True):
        """Erstellt eine neue Dokumentenvorlage"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO application_document_templates 
                (template_id, name, document_type, file_name, file_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (template_id, name, description, os.path.basename(file_path), file_path))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_by_template_id(template_id):
        """Gibt alle Dokumentenvorlagen für eine Bewerbungsvorlage zurück"""
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'tickets.db')
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM application_document_templates 
                WHERE template_id = ? AND is_active = 1
            ''', [template_id])
            return cursor.fetchall() 