import sqlite3
import json
from pathlib import Path

def get_table_structure(db_path):
    """Analysiert die Struktur aller Tabellen in einer SQLite-Datenbank."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Hole alle Tabellennamen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    db_structure = {}
    
    for table in tables:
        table_name = table[0]
        
        # Hole Spalteninformationen
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Hole Indizes
        cursor.execute(f"PRAGMA index_list({table_name});")
        indexes = cursor.fetchall()
        
        # Hole Foreign Keys
        cursor.execute(f"PRAGMA foreign_key_list({table_name});")
        foreign_keys = cursor.fetchall()
        
        db_structure[table_name] = {
            'columns': [
                {
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default_value': col[4],
                    'is_primary_key': bool(col[5])
                }
                for col in columns
            ],
            'indexes': [
                {
                    'name': idx[1],
                    'unique': bool(idx[2])
                }
                for idx in indexes
            ],
            'foreign_keys': [
                {
                    'id': fk[0],
                    'seq': fk[1],
                    'table': fk[2],
                    'from': fk[3],
                    'to': fk[4],
                    'on_update': fk[5],
                    'on_delete': fk[6],
                    'match': fk[7]
                }
                for fk in foreign_keys
            ]
        }
    
    conn.close()
    return db_structure

def analyze_databases():
    """Analysiert beide Datenbanken und speichert die Struktur in JSON-Dateien."""
    base_path = Path('app/database')
    
    # Analysiere beide Datenbanken
    inventory_structure = get_table_structure(base_path / 'inventory.db')
    tickets_structure = get_table_structure(base_path / 'tickets.db')
    
    # Speichere die Strukturen in JSON-Dateien
    with open('inventory_structure.json', 'w', encoding='utf-8') as f:
        json.dump(inventory_structure, f, indent=2, ensure_ascii=False)
    
    with open('tickets_structure.json', 'w', encoding='utf-8') as f:
        json.dump(tickets_structure, f, indent=2, ensure_ascii=False)
    
    print("Datenbankstrukturen wurden in JSON-Dateien gespeichert:")
    print("- inventory_structure.json")
    print("- tickets_structure.json")

if __name__ == '__main__':
    analyze_databases() 