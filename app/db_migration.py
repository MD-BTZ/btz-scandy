import sqlite3
import os

# HINWEIS: Dieses Skript ist für den Standalone-Aufruf gedacht (python app/db_migration.py)
# und verwendet daher eine eigene DB-Verbindungsfunktion.

def get_db_connection():
    """Stellt eine Verbindung zur Haupt-Inventardatenbank her.

    Konstruiert den Pfad relativ zum Skript-Speicherort.
    WARNUNG: Nicht für den Gebrauch innerhalb der laufenden Flask-App gedacht!
    """
    # Korrekter Pfad zur Datenbank im app/database Ordner
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'inventory.db')
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Fehler beim Verbinden zur DB in Migration: {e}")
        raise

def migrate_database():
    """Führt sequenzielle Schema-Änderungen an der inventory.db durch.

    Enthält ALTER TABLE und CREATE TABLE Anweisungen.
    Verwendet try-except Blöcke um idempotente Ausführung zu ermöglichen
    (d.h. mehrfacher Aufruf sollte keine Fehler verursachen, wenn Änderungen schon bestehen).
    """
    conn = None # Initialisiere conn für finally Block
    try:
        conn = get_db_connection()
        if conn is None: return # Beende, wenn Verbindung fehlschlägt

        print("Starting database migration...")

        # --- Migrationsschritte --- 
        # Jeder Schritt sollte in einem try/except sqlite3.OperationalError Block sein,
        # um Fehler bei bereits existierenden Spalten/Tabellen abzufangen.

        # Beispiel: Erstelle consumable_lendings Tabelle
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consumable_lendings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumable_barcode TEXT NOT NULL,
                    worker_barcode TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    lending_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    return_time TIMESTAMP, -- Spalte wird später hinzugefügt/geprüft
                    FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
                    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
                )
            ''')
            print("Checked/Created consumable_lendings table")
        except sqlite3.Error as e:
            print(f"Error step [Create consumable_lendings]: {e}")

        # Beispiel: Füge return_time zu consumable_lendings hinzu
        try:
            conn.execute('''
                ALTER TABLE consumable_lendings
                ADD COLUMN return_time TIMESTAMP
            ''')
            print("Added return_time to consumable_lendings")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("return_time column already exists in consumable_lendings")
            else: print(f"Error step [Alter consumable_lendings]: {e}")

        # Beispiel: Füge modified_at zu consumables hinzu
        try:
            conn.execute('''
                ALTER TABLE consumables
                ADD COLUMN modified_at TIMESTAMP
            ''')
            print("Added modified_at to consumables")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("modified_at column already exists in consumables")
            else: print(f"Error step [Alter consumables add modified_at]: {e}")

        # Beispiel: Füge modified_at zu tools hinzu
        try:
            conn.execute('''
                ALTER TABLE tools
                ADD COLUMN modified_at TIMESTAMP
            ''')
            print("Added modified_at to tools")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("modified_at column already exists in tools")
            else: print(f"Error step [Alter tools add modified_at]: {e}")

        # --- Weitere Migrationsschritte hier einfügen --- 
        # (Die vorherigen Blöcke für history, system_logs, max_bestand etc. wurden 
        # entfernt oder können hier nach Bedarf wieder eingefügt werden, 
        # wenn diese Tabellen/Spalten doch benötigt werden)

        conn.commit()
        print("Database migration finished.")

    except Exception as e:
        print(f"General error during migration: {str(e)}")

    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

# Die Funktionen add_system_logs_table und add_image_columns sind wahrscheinlich veraltet
# oder sollten in migrate_database integriert werden, wenn benötigt.

if __name__ == "__main__":
    print("Starting migration script...")
    migrate_database()
    print("Migration script completed!")