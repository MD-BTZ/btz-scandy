import os
import sqlite3
from datetime import datetime

def migrate_applications():
    db_path = 'app/database/tickets.db'
    
    # SQL-Skript für die Bewerbungstabellen (Basis)
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
        firmenname TEXT NOT NULL,
        position TEXT NOT NULL,
        ansprechpartner TEXT,
        anrede TEXT,
        email TEXT,
        telefon TEXT,
        adresse TEXT,
        generierter_inhalt TEXT,
        eigener_text TEXT,
        status TEXT DEFAULT 'neu',
        notizen TEXT,
        erstellt_von TEXT NOT NULL,
        erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        lebenslauf_pfad TEXT,
        zeugnisse_pfad TEXT,
        ausgabe_pfad TEXT,
        pdf_pfad TEXT,
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
        is_active INTEGER DEFAULT 1,
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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Migration ausführen (legt Tabellen an, falls sie fehlen)
        cursor.executescript(migration_sql)
        conn.commit()

        # Prüfe ob die alte Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='applications'")
        if cursor.fetchone():
            # Prüfe ob die Spalten bereits umbenannt wurden
        cursor.execute("PRAGMA table_info(applications)")
        columns = [row[1] for row in cursor.fetchall()]
            
            # Wenn die alte Spalte existiert, migriere die Daten
            if 'created_by' in columns and 'erstellt_von' not in columns:
                print("Migriere created_by zu erstellt_von...")
                cursor.execute("ALTER TABLE applications ADD COLUMN erstellt_von TEXT")
                cursor.execute("UPDATE applications SET erstellt_von = created_by")
                cursor.execute("ALTER TABLE applications DROP COLUMN created_by")
                
            if 'created_at' in columns and 'erstellt_am' not in columns:
                print("Migriere created_at zu erstellt_am...")
                cursor.execute("ALTER TABLE applications ADD COLUMN erstellt_am TIMESTAMP")
                cursor.execute("UPDATE applications SET erstellt_am = created_at")
                cursor.execute("ALTER TABLE applications DROP COLUMN created_at")
                
            if 'updated_at' in columns and 'aktualisiert_am' not in columns:
                print("Migriere updated_at zu aktualisiert_am...")
                cursor.execute("ALTER TABLE applications ADD COLUMN aktualisiert_am TIMESTAMP")
                cursor.execute("UPDATE applications SET aktualisiert_am = updated_at")
                cursor.execute("ALTER TABLE applications DROP COLUMN updated_at")
                
            if 'company_name' in columns and 'firmenname' not in columns:
                print("Migriere company_name zu firmenname...")
                cursor.execute("ALTER TABLE applications ADD COLUMN firmenname TEXT")
                cursor.execute("UPDATE applications SET firmenname = company_name")
                cursor.execute("ALTER TABLE applications DROP COLUMN company_name")
                
            if 'contact_person' in columns and 'ansprechpartner' not in columns:
                print("Migriere contact_person zu ansprechpartner...")
                cursor.execute("ALTER TABLE applications ADD COLUMN ansprechpartner TEXT")
                cursor.execute("UPDATE applications SET ansprechpartner = contact_person")
                cursor.execute("ALTER TABLE applications DROP COLUMN contact_person")
                
            if 'contact_salutation' in columns and 'anrede' not in columns:
                print("Migriere contact_salutation zu anrede...")
                cursor.execute("ALTER TABLE applications ADD COLUMN anrede TEXT")
                cursor.execute("UPDATE applications SET anrede = contact_salutation")
                cursor.execute("ALTER TABLE applications DROP COLUMN contact_salutation")
                
            if 'contact_email' in columns and 'email' not in columns:
                print("Migriere contact_email zu email...")
                cursor.execute("ALTER TABLE applications ADD COLUMN email TEXT")
                cursor.execute("UPDATE applications SET email = contact_email")
                cursor.execute("ALTER TABLE applications DROP COLUMN contact_email")
                
            if 'contact_phone' in columns and 'telefon' not in columns:
                print("Migriere contact_phone zu telefon...")
                cursor.execute("ALTER TABLE applications ADD COLUMN telefon TEXT")
                cursor.execute("UPDATE applications SET telefon = contact_phone")
                cursor.execute("ALTER TABLE applications DROP COLUMN contact_phone")
                
            if 'address' in columns and 'adresse' not in columns:
                print("Migriere address zu adresse...")
                cursor.execute("ALTER TABLE applications ADD COLUMN adresse TEXT")
                cursor.execute("UPDATE applications SET adresse = address")
                cursor.execute("ALTER TABLE applications DROP COLUMN address")
                
            if 'generated_content' in columns and 'generierter_inhalt' not in columns:
                print("Migriere generated_content zu generierter_inhalt...")
                cursor.execute("ALTER TABLE applications ADD COLUMN generierter_inhalt TEXT")
                cursor.execute("UPDATE applications SET generierter_inhalt = generated_content")
                cursor.execute("ALTER TABLE applications DROP COLUMN generated_content")
                
            if 'custom_text' in columns and 'eigener_text' not in columns:
                print("Migriere custom_text zu eigener_text...")
                cursor.execute("ALTER TABLE applications ADD COLUMN eigener_text TEXT")
                cursor.execute("UPDATE applications SET eigener_text = custom_text")
                cursor.execute("ALTER TABLE applications DROP COLUMN custom_text")
                
            if 'notes' in columns and 'notizen' not in columns:
                print("Migriere notes zu notizen...")
                cursor.execute("ALTER TABLE applications ADD COLUMN notizen TEXT")
                cursor.execute("UPDATE applications SET notizen = notes")
                cursor.execute("ALTER TABLE applications DROP COLUMN notes")
                
            if 'cv_path' in columns and 'lebenslauf_pfad' not in columns:
                print("Migriere cv_path zu lebenslauf_pfad...")
                cursor.execute("ALTER TABLE applications ADD COLUMN lebenslauf_pfad TEXT")
                cursor.execute("UPDATE applications SET lebenslauf_pfad = cv_path")
                cursor.execute("ALTER TABLE applications DROP COLUMN cv_path")
                
            if 'certificate_paths' in columns and 'zeugnisse_pfad' not in columns:
                print("Migriere certificate_paths zu zeugnisse_pfad...")
                cursor.execute("ALTER TABLE applications ADD COLUMN zeugnisse_pfad TEXT")
                cursor.execute("UPDATE applications SET zeugnisse_pfad = certificate_paths")
                cursor.execute("ALTER TABLE applications DROP COLUMN certificate_paths")
                
            if 'output_path' in columns and 'ausgabe_pfad' not in columns:
                print("Migriere output_path zu ausgabe_pfad...")
                cursor.execute("ALTER TABLE applications ADD COLUMN ausgabe_pfad TEXT")
                cursor.execute("UPDATE applications SET ausgabe_pfad = output_path")
                cursor.execute("ALTER TABLE applications DROP COLUMN output_path")
                
            if 'pdf_path' in columns and 'pdf_pfad' not in columns:
                print("Migriere pdf_path zu pdf_pfad...")
                cursor.execute("ALTER TABLE applications ADD COLUMN pdf_pfad TEXT")
                cursor.execute("UPDATE applications SET pdf_pfad = pdf_path")
                cursor.execute("ALTER TABLE applications DROP COLUMN pdf_path")

        conn.commit()
        print("Bewerbungstabellen erfolgreich erstellt und migriert")
    except sqlite3.OperationalError as e:
        print(f"Fehler bei der Migration: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()
    return True

if __name__ == '__main__':
    migrate_applications() 