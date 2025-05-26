import sqlite3
import json
from pathlib import Path
import random
from datetime import datetime, timedelta
import hashlib
import string

def generate_random_string(length=10):
    """Generiert einen zufälligen String."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_random_email():
    """Generiert eine zufällige E-Mail-Adresse."""
    domains = ['example.com', 'test.de', 'company.org']
    username = generate_random_string(8).lower()
    domain = random.choice(domains)
    return f"{username}@{domain}"

def generate_random_date(start_date=None, end_date=None):
    """Generiert ein zufälliges Datum zwischen start_date und end_date."""
    if start_date is None:
        start_date = datetime.now() - timedelta(days=365)
    if end_date is None:
        end_date = datetime.now()
    
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_days)

def generate_value_for_column(column_info):
    """Generiert einen passenden Wert für eine Spalte basierend auf ihrem Typ."""
    column_type = column_info['type'].lower()
    
    if 'int' in column_type:
        return random.randint(1, 1000)
    elif 'real' in column_type or 'float' in column_type:
        return round(random.uniform(1.0, 1000.0), 2)
    elif 'bool' in column_type:
        return random.choice([0, 1])
    elif 'date' in column_type:
        return generate_random_date().strftime('%Y-%m-%d')
    elif 'time' in column_type:
        return generate_random_date().strftime('%H:%M:%S')
    elif 'datetime' in column_type or 'timestamp' in column_type:
        return generate_random_date().strftime('%Y-%m-%d %H:%M:%S')
    else:  # TEXT oder andere String-Typen
        return generate_random_string()

def generate_password_hash(password):
    """Generiert einen SHA-256 Hash für ein Passwort."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_test_data(db_path, structure_file):
    """Generiert Beispieldaten basierend auf der Datenbankstruktur."""
    # Lade die Datenbankstruktur
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Generiere zuerst einen Admin-Benutzer
    admin_data = {
        'username': 'admin',
        'password_hash': generate_password_hash('admin123'),
        'email': 'admin@example.com',
        'firstname': 'Admin',
        'lastname': 'User',
        'role': 'admin',
        'is_active': 1,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    cursor.execute("""
        INSERT INTO users (username, password_hash, email, firstname, lastname, role, is_active, created_at, last_login)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        admin_data['username'],
        admin_data['password_hash'],
        admin_data['email'],
        admin_data['firstname'],
        admin_data['lastname'],
        admin_data['role'],
        admin_data['is_active'],
        admin_data['created_at'],
        admin_data['last_login']
    ))
    
    # Generiere normale Benutzer
    normal_users = [
        {
            'username': 'user1',
            'password_hash': generate_password_hash('user123'),
            'email': 'user1@example.com',
            'firstname': 'Normal',
            'lastname': 'User',
            'role': 'user',
            'is_active': 1,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    ]
    
    for user in normal_users:
        cursor.execute("""
            INSERT INTO users (username, password_hash, email, firstname, lastname, role, is_active, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user['username'],
            user['password_hash'],
            user['email'],
            user['firstname'],
            user['lastname'],
            user['role'],
            user['is_active'],
            user['created_at'],
            user['last_login']
        ))
    
    # Generiere Kategorien
    categories = [
        ('Werkzeuge', 'Handwerkzeuge und Elektrowerkzeuge'),
        ('Verbrauchsmaterial', 'Schrauben, Nägel, etc.'),
        ('Maschinen', 'Große Maschinen und Anlagen'),
        ('Sicherheit', 'Sicherheitsausrüstung')
    ]
    
    for name, description in categories:
        cursor.execute("""
            INSERT INTO categories (name, description)
            VALUES (?, ?)
        """, (name, description))
    
    # Generiere Standorte
    locations = [
        ('Hauptlager', 'Zentrales Lager'),
        ('Werkstatt 1', 'Hauptwerkstatt'),
        ('Werkstatt 2', 'Nebenwerkstatt'),
        ('Baustelle A', 'Aktuelle Baustelle')
    ]
    
    for name, description in locations:
        cursor.execute("""
            INSERT INTO locations (name, description)
            VALUES (?, ?)
        """, (name, description))
    
    # Generiere Abteilungen
    departments = [
        ('Produktion', 'Produktionsabteilung'),
        ('Wartung', 'Wartungsabteilung'),
        ('Logistik', 'Logistikabteilung'),
        ('Qualität', 'Qualitätssicherung')
    ]
    
    for name, description in departments:
        cursor.execute("""
            INSERT INTO departments (name, description)
            VALUES (?, ?)
        """, (name, description))
    
    # Generiere Werkzeuge
    tools = [
        ('Hammer', 'Standard-Hammer', 1, 1, 'Gut', '2024-01-01', '2024-12-31'),
        ('Schraubenzieher Set', 'Verschiedene Größen', 1, 1, 'Neu', '2024-01-01', '2024-12-31'),
        ('Bohrmaschine', 'Elektrische Bohrmaschine', 1, 1, 'Gut', '2024-01-01', '2024-12-31')
    ]
    
    for name, description, category_id, location_id, condition, purchase_date, next_maintenance in tools:
        cursor.execute("""
            INSERT INTO tools (name, description, category_id, location_id, condition, purchase_date, next_maintenance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, description, category_id, location_id, condition, purchase_date, next_maintenance))
    
    # Generiere Verbrauchsmaterial
    consumables = [
        ('Schrauben 5mm', '100 Stück', 50, 2, 1),
        ('Nägel 3cm', '500 Stück', 30, 2, 1),
        ('Schleifpapier', '10 Blatt', 20, 2, 1)
    ]
    
    for name, description, quantity, category_id, location_id in consumables:
        cursor.execute("""
            INSERT INTO consumables (name, description, quantity, category_id, location_id)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, quantity, category_id, location_id))
    
    conn.commit()
    conn.close()
    print(f"Beispieldaten wurden in {db_path} eingefügt.")

if __name__ == '__main__':
    base_path = Path('app/database')
    
    # Generiere Beispieldaten für beide Datenbanken
    generate_test_data(base_path / 'inventory.db', 'inventory_structure.json')
    generate_test_data(base_path / 'tickets.db', 'tickets_structure.json') 