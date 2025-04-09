import sqlite3
from datetime import datetime

def check_database(db_path):
    print(f"\nAnalysiere Datenbank: {db_path}")
    print("=" * 50)
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Alle Tabellen auflisten
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"{table_name}:")
            
            # Spalteninformationen abrufen
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # Anzahl der Einträge
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  Anzahl Einträge: {count}\n")
            
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Fehler beim Analysieren der Datenbank: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    check_database("app/database/inventory.db")
    check_database("instance/scandy.db") 