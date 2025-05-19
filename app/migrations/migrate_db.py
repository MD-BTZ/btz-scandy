import os
import sqlite3
import shutil
from datetime import datetime
from flask import current_app

def migrate_database():
    # Pfade definieren
    old_db_path = 'app/database/inventory.db'
    new_db_path = 'instance/inventory_new.db'
    backup_dir = 'instance'
    
    # Backup erstellen
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'inventory_backup_{timestamp}.db')
    
    print(f"Erstelle Backup unter {backup_path}...")
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(old_db_path, backup_path)
    
    print("Starte Migration...")
    
    # SQL-Skript einlesen
    with open('app/migrations/migrate_to_new_structure.sql', 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Verbindung zur alten Datenbank herstellen
    conn = sqlite3.connect(old_db_path)
    cursor = conn.cursor()
    
    try:
        # Migration ausführen
        cursor.executescript(migration_sql)
        conn.commit()
        
        # Verbindung schließen
        conn.close()
        
        # Neue Datenbank aktivieren
        if os.path.exists(new_db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.rename(old_db_path, f'{old_db_path}.{timestamp}.old')
            os.rename(new_db_path, old_db_path)
            print("Migration erfolgreich abgeschlossen!")
            print(f"Die alte Datenbank wurde unter {old_db_path}.{timestamp}.old gesichert.")
            
    except sqlite3.OperationalError as e:
        print(f"Fehler bei der Migration: {str(e)}")
        conn.close()
        if os.path.exists(new_db_path):
            os.remove(new_db_path)
        print("Migration fehlgeschlagen - die alte Datenbank bleibt unverändert.")
        return False
        
    return True

if __name__ == '__main__':
    migrate_database() 