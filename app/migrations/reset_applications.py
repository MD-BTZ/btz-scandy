import os
import sqlite3
from datetime import datetime

def reset_applications_tables():
    db_path = 'app/database/tickets.db'
    
    # SQL-Skript zum Löschen und Neuerstellen der Tabellen
    reset_sql = """
    -- Lösche existierende Tabellen
    DROP TABLE IF EXISTS application_responses;
    DROP TABLE IF EXISTS application_documents;
    DROP TABLE IF EXISTS applications;
    DROP TABLE IF EXISTS application_templates;
    """
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.executescript(reset_sql)
            conn.commit()
            print("Tabellen wurden zurückgesetzt.")
            
            # Führe die Migration aus
            from app.migrations.migrate_applications import migrate_applications
            migrate_applications()
            
    except Exception as e:
        print(f"Fehler beim Zurücksetzen der Tabellen: {str(e)}")
        raise

if __name__ == "__main__":
    reset_applications_tables() 