import sqlite3
from pathlib import Path
from datetime import datetime

def get_table_schema(db_path, table_name):
    """Holt das Schema einer Tabelle aus der SQLite-Datenbank."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Hole Spalteninformationen
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    # Hole Indizes
    cursor.execute(f"PRAGMA index_list({table_name});")
    indexes = cursor.fetchall()
    
    # Hole Foreign Keys
    cursor.execute(f"PRAGMA foreign_key_list({table_name});")
    foreign_keys = cursor.fetchall()
    
    conn.close()
    
    return {
        'columns': columns,
        'indexes': indexes,
        'foreign_keys': foreign_keys
    }

def analyze_database(db_path):
    """Analysiert eine komplette SQLite-Datenbank."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Hole alle Tabellennamen
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    db_structure = {}
    for table in tables:
        table_name = table[0]
        db_structure[table_name] = get_table_schema(db_path, table_name)
    
    conn.close()
    return db_structure

def write_schema_to_file(db_path, output_file):
    """Schreibt die Datenbankstruktur in eine Textdatei."""
    db_structure = analyze_database(db_path)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Datenbank: {db_path}\n")
        f.write(f"Analysezeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for table_name, table_info in db_structure.items():
            f.write(f"Tabelle: {table_name}\n")
            f.write("-" * 40 + "\n")
            
            # Spalten
            f.write("\nSpalten:\n")
            for col in table_info['columns']:
                col_id, name, type_, not_null, default_val, pk = col
                f.write(f"  - {name} ({type_})")
                if pk:
                    f.write(" PRIMARY KEY")
                if not_null:
                    f.write(" NOT NULL")
                if default_val:
                    f.write(f" DEFAULT {default_val}")
                f.write("\n")
            
            # Indizes
            if table_info['indexes']:
                f.write("\nIndizes:\n")
                for idx in table_info['indexes']:
                    # SQLite gibt 5 Werte zurück: seq, name, unique, origin, partial
                    seq, name, unique, origin, partial = idx
                    f.write(f"  - {name} {'(UNIQUE)' if unique else ''}\n")
            
            # Foreign Keys
            if table_info['foreign_keys']:
                f.write("\nForeign Keys:\n")
                for fk in table_info['foreign_keys']:
                    fk_id, seq, table, from_col, to_col, on_update, on_delete, match = fk
                    f.write(f"  - {from_col} -> {table}.{to_col}\n")
            
            f.write("\n" + "=" * 80 + "\n\n")

def main():
    base_path = Path('app/database')
    
    # Analysiere beide Datenbanken
    write_schema_to_file(base_path / 'inventory.db', 'inventory_schema.txt')
    write_schema_to_file(base_path / 'tickets.db', 'tickets_schema.txt')
    
    print("Datenbankstrukturen wurden in die folgenden Dateien geschrieben:")
    print("- inventory_schema.txt")
    print("- tickets_schema.txt")

if __name__ == '__main__':
    main() 