import sqlite3
import os

def check_database():
    db_path = 'app/database/tickets.db'
    print(f"Prüfe Datenbank unter: {os.path.abspath(db_path)}")
    
    if not os.path.exists(db_path):
        print(f"Fehler: Datenbank {db_path} existiert nicht!")
        return
        
    try:
        print("Versuche Verbindung zur Datenbank herzustellen...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Liste alle Tabellen auf
        print("\nVerfügbare Tabellen in der Datenbank:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")
        
        # Prüfe Schema der auftrag_details Tabelle
        print("\nPrüfe auftrag_details Tabelle...")
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='auftrag_details'")
        result = cursor.fetchone()
        
        if result:
            print("\nSchema der auftrag_details Tabelle:")
            print(result[0])
        else:
            print("\nFehler: auftrag_details Tabelle existiert nicht!")
            
        # Prüfe ob die Tabelle Daten enthält
        try:
            cursor.execute("SELECT COUNT(*) FROM auftrag_details")
            count = cursor.fetchone()[0]
            print(f"\nAnzahl der Einträge in auftrag_details: {count}")
        except sqlite3.OperationalError as e:
            print(f"\nFehler beim Zählen der Einträge: {e}")
        
        # Prüfe die Spalten der Tabelle
        try:
            cursor.execute("PRAGMA table_info(auftrag_details)")
            columns = cursor.fetchall()
            print("\nSpalten der auftrag_details Tabelle:")
            for col in columns:
                print(f"- {col[1]} ({col[2]})")
        except sqlite3.OperationalError as e:
            print(f"\nFehler beim Lesen der Spalten: {e}")
            
    except sqlite3.Error as e:
        print(f"SQLite Fehler: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_database()