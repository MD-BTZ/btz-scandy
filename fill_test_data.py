#!/usr/bin/env python3
import sqlite3
import datetime
from werkzeug.security import generate_password_hash
import random

def get_db_connection(db_path):
    """Erstellt eine Datenbankverbindung"""
    return sqlite3.connect(db_path)

def generate_worker_data(count):
    """Generiert Testdaten für Mitarbeiter"""
    firstnames = ['Max', 'Anna', 'Peter', 'Maria', 'Thomas', 'Julia', 'Michael', 'Sarah', 'Andreas', 'Lisa']
    lastnames = ['Müller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner', 'Becker', 'Hoffmann', 'Schulz']
    departments = ['Produktion', 'Wartung', 'Verwaltung', 'Entwicklung', 'Qualitätssicherung', 'Logistik']
    
    workers = []
    for i in range(count):
        barcode = f'W{i+1:03d}'
        firstname = random.choice(firstnames)
        lastname = random.choice(lastnames)
        department = random.choice(departments)
        email = f'{firstname.lower()}.{lastname.lower()}@example.com'
        phone = f'0{random.randint(100,999)}-{random.randint(1000000,9999999)}'
        workers.append((barcode, firstname, lastname, department, email, phone))
    return workers

def generate_tool_data(count):
    """Generiert Testdaten für Werkzeuge"""
    categories = ['Werkzeuge', 'Elektronik', 'Sicherheit', 'Messtechnik', 'Handwerkzeug', 'Elektrowerkzeuge']
    locations = ['Lager A', 'Lager B', 'Werkstatt', 'Büro', 'Produktion', 'Entwicklung']
    statuses = ['verfügbar', 'in_wartung', 'ausgeliehen', 'defekt']
    
    tools = []
    for i in range(count):
        barcode = f'T{i+1:03d}'
        category = random.choice(categories)
        location = random.choice(locations)
        status = random.choice(statuses)
        
        if category == 'Werkzeuge':
            name = f'Schraubenzieher Set {i+1}'
            description = f'Verschiedene Schraubenzieher im Set {i+1}'
        elif category == 'Elektronik':
            name = f'Multimeter {i+1}'
            description = f'Digitales Multimeter Modell {i+1}'
        elif category == 'Sicherheit':
            name = f'Sicherheitsausrüstung Set {i+1}'
            description = f'Komplettes Sicherheitsset {i+1}'
        elif category == 'Messtechnik':
            name = f'Messgerät {i+1}'
            description = f'Präzisionsmessgerät {i+1}'
        elif category == 'Handwerkzeug':
            name = f'Handwerkzeug Set {i+1}'
            description = f'Verschiedene Handwerkzeuge im Set {i+1}'
        else:
            name = f'Elektrowerkzeug {i+1}'
            description = f'Professionelles Elektrowerkzeug {i+1}'
            
        last_maintenance = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 180))
        next_maintenance = last_maintenance + datetime.timedelta(days=random.randint(30, 90))
        maintenance_interval = random.randint(30, 90)
        last_checked = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30))
        supplier = f'Lieferant {random.randint(1,5)}'
        reorder_point = random.randint(1, 5)
        notes = f'Notizen für {name}'
        
        tools.append((barcode, name, description, status, category, location, 
                     last_maintenance.strftime('%Y-%m-%d'), 
                     next_maintenance.strftime('%Y-%m-%d'),
                     maintenance_interval,
                     last_checked.strftime('%Y-%m-%d %H:%M:%S'),
                     supplier, reorder_point, notes))
    return tools

def fill_ticket_db(db_path):
    """Befüllt die Ticket-Datenbank mit Testdaten"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Test-Benutzer (30 aktive Benutzer)
    users = []
    for i in range(30):
        username = f'user{i+1}'
        password = f'user{i+1}123'
        firstname = f'Vorname{i+1}'
        lastname = f'Nachname{i+1}'
        email = f'user{i+1}@example.com'
        role = 'admin' if i == 0 else 'manager' if i < 5 else 'user'
        users.append((username, generate_password_hash(password), email, firstname, lastname, role))
    
    cursor.executemany('''
        INSERT INTO users (username, password_hash, email, firstname, lastname, role)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', users)

    # Ticket-Kategorien
    ticket_categories = [
        ('Wartung',),
        ('Reparatur',),
        ('Installation',),
        ('Beratung',),
        ('Kalibrierung',),
        ('Schulung',),
        ('Notfall',)
    ]
    cursor.executemany('''
        INSERT INTO ticket_categories (name)
        VALUES (?)
    ''', ticket_categories)

    # Kategorien
    categories = [
        ('Werkzeuge', 'Verschiedene Werkzeuge und Geräte'),
        ('Elektronik', 'Elektronische Geräte und Komponenten'),
        ('Verbrauchsmaterial', 'Verbrauchsmaterialien und Ersatzteile'),
        ('Sicherheit', 'Sicherheitsausrüstung und -materialien'),
        ('Messtechnik', 'Messgeräte und Kalibrierung'),
        ('Handwerkzeug', 'Handwerkzeuge und Sets'),
        ('Elektrowerkzeuge', 'Elektrische Werkzeuge und Maschinen')
    ]
    cursor.executemany('''
        INSERT INTO categories (name, description)
        VALUES (?, ?)
    ''', categories)

    # Standorte
    locations = [
        ('Lager A', 'Hauptlager'),
        ('Lager B', 'Ersatzlager'),
        ('Werkstatt', 'Hauptwerkstatt'),
        ('Büro', 'Verwaltungsbereich'),
        ('Produktion', 'Produktionsbereich'),
        ('Entwicklung', 'Entwicklungsabteilung'),
        ('Qualitätssicherung', 'QS-Bereich')
    ]
    cursor.executemany('''
        INSERT INTO locations (name, description)
        VALUES (?, ?)
    ''', locations)

    # Abteilungen
    departments = [
        ('Produktion', 'Produktionsabteilung'),
        ('Wartung', 'Wartungsabteilung'),
        ('Verwaltung', 'Verwaltungsabteilung'),
        ('Entwicklung', 'Entwicklungsabteilung'),
        ('Qualitätssicherung', 'QS-Abteilung'),
        ('Logistik', 'Logistikabteilung'),
        ('Einkauf', 'Einkaufsabteilung')
    ]
    cursor.executemany('''
        INSERT INTO departments (name, description)
        VALUES (?, ?)
    ''', departments)

    # Tickets (50 Tickets)
    current_time = datetime.datetime.now()
    tickets = []
    for i in range(50):
        title = f'Ticket {i+1}'
        description = f'Beschreibung für Ticket {i+1}'
        status = random.choice(['offen', 'in_bearbeitung', 'abgeschlossen'])
        priority = random.choice(['niedrig', 'normal', 'hoch', 'dringend'])
        created_by = f'user{random.randint(1,30)}'
        assigned_to = f'user{random.randint(1,30)}'
        category = random.choice(['Wartung', 'Reparatur', 'Installation', 'Beratung', 'Kalibrierung', 'Schulung', 'Notfall'])
        due_date = current_time + datetime.timedelta(days=random.randint(1,30))
        tickets.append((title, description, status, priority, created_by, assigned_to, category, due_date))
    
    cursor.executemany('''
        INSERT INTO tickets (title, description, status, priority, created_by, assigned_to, category, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', tickets)

    # Auftrag Details
    auftrag_details = []
    for i in range(50):
        ticket_id = i + 1
        auftrag_an = random.choice(['Werkstatt', 'Lager A', 'Lager B', 'Produktion', 'Entwicklung'])
        bereich = random.choice(['Elektronik', 'Werkzeuge', 'Sicherheit', 'Messtechnik'])
        auftraggeber_intern = random.choice([0, 1])
        auftraggeber_extern = 1 if not auftraggeber_intern else 0
        auftraggeber_name = f'Auftraggeber {i+1}'
        kontakt = f'kontakt{i+1}@example.com'
        auftragsbeschreibung = f'Beschreibung für Auftrag {i+1}'
        ausgefuehrte_arbeiten = f'Durchgeführte Arbeiten für Auftrag {i+1}'
        arbeitsstunden = round(random.uniform(1.0, 8.0), 1)
        leistungskategorie = random.choice(['Wartung', 'Reparatur', 'Installation', 'Beratung'])
        fertigstellungstermin = (current_time + datetime.timedelta(days=random.randint(1,30))).strftime('%Y-%m-%d')
        auftrag_details.append((ticket_id, auftrag_an, bereich, auftraggeber_intern, auftraggeber_extern,
                              auftraggeber_name, kontakt, auftragsbeschreibung, ausgefuehrte_arbeiten,
                              arbeitsstunden, leistungskategorie, fertigstellungstermin))
    
    cursor.executemany('''
        INSERT INTO auftrag_details (ticket_id, auftrag_an, bereich, auftraggeber_intern, auftraggeber_extern, 
            auftraggeber_name, kontakt, auftragsbeschreibung, ausgefuehrte_arbeiten, arbeitsstunden, 
            leistungskategorie, fertigstellungstermin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', auftrag_details)

    # Auftrag Material
    auftrag_material = []
    materials = ['Schrauben', 'Kabel', 'Ersatzteile', 'Werkzeuge', 'Materialien']
    for i in range(50):
        ticket_id = i + 1
        material = random.choice(materials)
        menge = random.randint(1, 10)
        einzelpreis = round(random.uniform(10.0, 1000.0), 2)
        auftrag_material.append((ticket_id, material, menge, einzelpreis))
    
    cursor.executemany('''
        INSERT INTO auftrag_material (ticket_id, material, menge, einzelpreis)
        VALUES (?, ?, ?, ?)
    ''', auftrag_material)

    # Ticket Notes
    ticket_notes = []
    for i in range(50):
        ticket_id = i + 1
        note = f'Notiz für Ticket {i+1}'
        created_by = f'user{random.randint(1,30)}'
        is_private = random.choice([0, 1])
        ticket_notes.append((ticket_id, note, created_by, is_private))
    
    cursor.executemany('''
        INSERT INTO ticket_notes (ticket_id, note, created_by, is_private)
        VALUES (?, ?, ?, ?)
    ''', ticket_notes)

    # System Logs
    logs = [
        ('INFO', 'System gestartet', 'System erfolgreich initialisiert'),
        ('WARNING', 'Niedriger Bestand', 'Schrauben M3 unter Mindestbestand'),
        ('ERROR', 'Datenbankfehler', 'Verbindungsfehler bei Backup'),
        ('INFO', 'Backup erstellt', 'Tägliches Backup erfolgreich erstellt'),
        ('WARNING', 'Wartung fällig', 'Wartung für Multimeter T002 fällig'),
        ('ERROR', 'Datenbankfehler', 'Verbindungsfehler bei Synchronisation')
    ]
    cursor.executemany('''
        INSERT INTO system_logs (level, message, details)
        VALUES (?, ?, ?)
    ''', logs)

    # Einstellungen
    settings = [
        ('company_name', 'Test GmbH', 'Name des Unternehmens'),
        ('maintenance_interval', '30', 'Wartungsintervall in Tagen'),
        ('backup_enabled', 'true', 'Automatisches Backup aktiviert'),
        ('sync_interval', '60', 'Synchronisierungsintervall in Minuten'),
        ('max_tickets_per_user', '10', 'Maximale Anzahl offener Tickets pro Benutzer'),
        ('default_priority', 'normal', 'Standard-Priorität für neue Tickets'),
        ('notification_enabled', 'true', 'E-Mail-Benachrichtigungen aktiviert')
    ]
    cursor.executemany('''
        INSERT INTO settings (key, value, description)
        VALUES (?, ?, ?)
    ''', settings)

    conn.commit()
    conn.close()

def fill_inventory_db(db_path):
    """Befüllt die Inventory-Datenbank mit Testdaten"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Werkzeuge (100 Werkzeuge)
    tools = generate_tool_data(100)
    cursor.executemany('''
        INSERT INTO tools (barcode, name, description, status, category, location, 
                         last_maintenance, next_maintenance, maintenance_interval,
                         last_checked, supplier, reorder_point, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', tools)

    # Mitarbeiter (150 Mitarbeiter)
    workers = generate_worker_data(150)
    cursor.executemany('''
        INSERT INTO workers (barcode, firstname, lastname, department, email, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', workers)

    # Ausleihen (200 Ausleihen)
    current_time = datetime.datetime.now()
    lendings = []
    for i in range(200):
        tool_barcode = f'T{random.randint(1,100):03d}'
        worker_barcode = f'W{random.randint(1,150):03d}'
        lent_at = current_time - datetime.timedelta(days=random.randint(0,30))
        returned_at = None if random.random() > 0.7 else lent_at + datetime.timedelta(days=random.randint(1,14))
        notes = f'Ausgeliehen für Projekt {random.randint(1,10)}'
        lendings.append((tool_barcode, worker_barcode, lent_at, returned_at, notes))
    
    cursor.executemany('''
        INSERT INTO lendings (tool_barcode, worker_barcode, lent_at, returned_at, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', lendings)

    # Verbrauchsmaterial
    consumables = []
    for i in range(50):
        barcode = f'C{i+1:03d}'
        category = random.choice(['Verbrauchsmaterial', 'Elektronik', 'Sicherheit', 'Werkzeuge'])
        location = random.choice(['Lager A', 'Lager B', 'Werkstatt', 'Produktion'])
        unit = random.choice(['Stück', 'Packung', 'Dose', 'Meter', 'Kilogramm'])
        
        if category == 'Verbrauchsmaterial':
            name = f'Schrauben M{random.randint(2,6)}'
            description = f'{name} 100er Pack'
            quantity = random.randint(50, 500)
            min_quantity = 20
        elif category == 'Elektronik':
            name = f'Kabel {random.randint(1,5)}m'
            description = f'Netzwerkkabel {name}'
            quantity = random.randint(10, 100)
            min_quantity = 5
        elif category == 'Sicherheit':
            name = f'Sicherheitsausrüstung {i+1}'
            description = f'Sicherheitsausrüstung Set {i+1}'
            quantity = random.randint(5, 20)
            min_quantity = 2
        else:
            name = f'Werkzeug {i+1}'
            description = f'Ersatzwerkzeug {i+1}'
            quantity = random.randint(1, 10)
            min_quantity = 1
            
        supplier = f'Lieferant {random.randint(1,5)}'
        reorder_point = min_quantity
        notes = f'Notizen für {name}'
        
        consumables.append((barcode, name, description, quantity, min_quantity, category, location, unit,
                          supplier, reorder_point, notes))
    
    cursor.executemany('''
        INSERT INTO consumables (barcode, name, description, quantity, min_quantity, category, location, unit,
                               supplier, reorder_point, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', consumables)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Befülle die Ticket-Datenbank
    fill_ticket_db('app/database/tickets.db')
    print("Ticket-Datenbank wurde mit Testdaten befüllt.")

    # Befülle die Inventory-Datenbank
    fill_inventory_db('app/database/inventory.db')
    print("Inventory-Datenbank wurde mit Testdaten befüllt.") 