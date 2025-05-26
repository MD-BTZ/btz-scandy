import sqlite3
import re
from pathlib import Path
from datetime import datetime, timedelta
import random
import hashlib

def parse_schema_file(schema_file):
    """Parst die Schema-Textdatei und gibt ein Dict mit Tabellen und Spalten zurück."""
    tables = {}
    current_table = None
    with open(schema_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('Tabelle:'):
                current_table = line.split(':', 1)[1].strip()
                tables[current_table] = []
            elif line.startswith('-') or not line:
                continue
            elif line.startswith('-'):
                continue
            elif line.startswith('Spalten:'):
                continue
            elif line.startswith('Indizes:') or line.startswith('Foreign Keys:') or line.startswith('='):
                continue
            elif line.startswith('*'):
                continue
            elif current_table and line.startswith('-') is False:
                # Spalte parsen
                match = re.match(r'-\s*(\w+)\s*\(([^)]+)\)', line)
                if match:
                    colname, coltype = match.groups()
                    tables[current_table].append((colname, coltype))
    return tables

def random_string(length=8):
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=length))

def random_email():
    return f"{random_string(6)}@example.com"

def random_date():
    start = datetime.now() - timedelta(days=365)
    end = datetime.now()
    return (start + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d')

def random_datetime():
    start = datetime.now() - timedelta(days=365)
    end = datetime.now()
    return (start + timedelta(days=random.randint(0, 365), seconds=random.randint(0, 86400))).strftime('%Y-%m-%d %H:%M:%S')

def random_value(colname, coltype):
    coltype = coltype.lower()
    if 'int' in coltype:
        return random.randint(1, 100)
    elif 'char' in coltype or 'text' in coltype:
        if 'email' in colname:
            return random_email()
        elif 'name' in colname:
            return random_string(10)
        elif 'password' in colname:
            return hashlib.sha256(random_string(10).encode()).hexdigest()
        else:
            return random_string(12)
    elif 'date' in coltype and 'time' not in coltype:
        return random_date()
    elif 'time' in coltype:
        return random_datetime()
    elif 'bool' in coltype:
        return random.choice([0, 1])
    elif 'real' in coltype or 'float' in coltype:
        return round(random.uniform(1, 1000), 2)
    else:
        return random_string(8)

def fill_db(db_path, schema_file, num_rows=10):
    tables = parse_schema_file(schema_file)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for table, columns in tables.items():
        # Primärschlüssel-Spalten überspringen
        filtered_cols = [col for col in columns if col[0] != 'id']
        if not filtered_cols:
            continue
        for _ in range(num_rows):
            colnames = [col[0] for col in filtered_cols]
            values = [random_value(col[0], col[1]) for col in filtered_cols]
            placeholders = ','.join(['?'] * len(values))
            try:
                cursor.execute(f"INSERT INTO {table} ({', '.join(colnames)}) VALUES ({placeholders})", values)
            except Exception as e:
                print(f"Fehler beim Einfügen in {table}: {e}")
    conn.commit()
    conn.close()
    print(f"Testdaten für {db_path} eingefügt.")

def main():
    base_path = Path('app/database')
    fill_db(base_path / 'inventory.db', 'inventory_schema.txt', num_rows=10)
    fill_db(base_path / 'tickets.db', 'tickets_schema.txt', num_rows=10)

if __name__ == '__main__':
    main() 