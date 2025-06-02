import os
import sqlite3
from datetime import datetime

def migrate_applications():
    db_path = 'app/database/tickets.db'
    
    # SQL-Skript für die Bewerbungstabellen
    migration_sql = """
    -- Erstelle die application_templates Tabelle
    CREATE TABLE IF NOT EXISTS application_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        file_path TEXT,
        file_name TEXT,
        category TEXT,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    );

    -- Erstelle die applications Tabelle
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
    );

    -- Erstelle die application_documents Tabelle
    CREATE TABLE IF NOT EXISTS application_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        document_type TEXT,
        created_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id)
    );

    -- Erstelle die application_responses Tabelle
    CREATE TABLE IF NOT EXISTS application_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER,
        response_type TEXT,
        response_date TIMESTAMP,
        content TEXT,
        next_steps TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES applications(id)
    );
    """
    
    print(f"Starte Migration für {db_path}")
    
    # Verbindung zur Datenbank herstellen
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Migration ausführen
        cursor.executescript(migration_sql)
        conn.commit()
        print("Bewerbungstabellen erfolgreich erstellt")
        
    except sqlite3.OperationalError as e:
        print(f"Fehler bei der Migration: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()
    
    return True

if __name__ == '__main__':
    migrate_applications() 