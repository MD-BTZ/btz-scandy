#!/usr/bin/env python3
"""
Testskript für MongoDB-Integration (MongoDB-only)
"""
import os
import sys

# Umgebungsvariablen setzen
os.environ['MONGODB_URI'] = 'mongodb://admin:scandy123@localhost:27017/'
os.environ['MONGODB_DB'] = 'scandy'
os.environ['SECRET_KEY'] = 'test-secret-key'

print("=== MongoDB Test für Scandy (MongoDB-only) ===")
print(f"MONGODB_URI: {os.environ.get('MONGODB_URI')}")
print(f"MONGODB_DB: {os.environ.get('MONGODB_DB')}")

try:
    # Flask-App erstellen
    from app import create_app
    app = create_app()
    print("✓ Flask-App erfolgreich erstellt")
    
    # MongoDB-Verbindung testen
    from app.models.mongodb_database import mongodb
    print("✓ MongoDB-Verbindung hergestellt")
    
    # Indizes erstellen
    from app.models.mongodb_models import create_mongodb_indexes
    create_mongodb_indexes()
    print("✓ MongoDB-Indizes erstellt")
    
    # MongoDB-Modelle testen
    from app.models.mongodb_models import (
        MongoDBTool, MongoDBWorker, MongoDBConsumable, 
        MongoDBLending, MongoDBConsumableUsage
    )
    print("✓ MongoDB-Modelle geladen")
    
    # Test-Daten erstellen
    print("\n=== Test-Daten erstellen ===")
    
    # Test-Werkzeug
    tool_data = {
        'barcode': 'TEST001',
        'name': 'Test-Hammer',
        'description': 'Ein Test-Werkzeug',
        'status': 'verfügbar',
        'category': 'Handwerkzeug',
        'location': 'Lager A'
    }
    
    tool_id = MongoDBTool.create(tool_data)
    print(f"✓ Test-Werkzeug erstellt: {tool_id}")
    
    # Test-Mitarbeiter
    worker_data = {
        'barcode': 'WORK001',
        'firstname': 'Max',
        'lastname': 'Mustermann',
        'department': 'IT',
        'email': 'max@test.de'
    }
    
    worker_id = MongoDBWorker.create(worker_data)
    print(f"✓ Test-Mitarbeiter erstellt: {worker_id}")
    
    # Test-Verbrauchsmaterial
    consumable_data = {
        'barcode': 'CONS001',
        'name': 'Test-Schrauben',
        'description': 'M4 Schrauben',
        'quantity': 100,
        'min_quantity': 10,
        'category': 'Befestigung',
        'location': 'Lager B',
        'unit': 'Stück'
    }
    
    consumable_id = MongoDBConsumable.create(consumable_data)
    print(f"✓ Test-Verbrauchsmaterial erstellt: {consumable_id}")
    
    # Daten abrufen
    print("\n=== Daten abrufen ===")
    
    tools = MongoDBTool.get_all_active()
    print(f"✓ Werkzeuge abgerufen: {len(tools)} gefunden")
    
    workers = MongoDBWorker.get_all_active()
    print(f"✓ Mitarbeiter abgerufen: {len(workers)} gefunden")
    
    consumables = MongoDBConsumable.get_all_active()
    print(f"✓ Verbrauchsmaterialien abgerufen: {len(consumables)} gefunden")
    
    # Zähler testen
    print("\n=== Zähler testen ===")
    
    tool_count = MongoDBTool.count_active()
    worker_count = MongoDBWorker.count_active()
    consumable_count = MongoDBConsumable.count_active()
    
    print(f"✓ Aktive Werkzeuge: {tool_count}")
    print(f"✓ Aktive Mitarbeiter: {worker_count}")
    print(f"✓ Aktive Verbrauchsmaterialien: {consumable_count}")
    
    # Erweiterte Funktionen testen
    print("\n=== Erweiterte Funktionen testen ===")
    
    tools_with_status = MongoDBTool.get_all_with_status()
    print(f"✓ Werkzeuge mit Status: {len(tools_with_status)} gefunden")
    
    workers_with_lendings = MongoDBWorker.get_all_with_lendings()
    print(f"✓ Mitarbeiter mit Ausleihen: {len(workers_with_lendings)} gefunden")
    
    consumables_with_status = MongoDBConsumable.get_all()
    print(f"✓ Verbrauchsmaterialien mit Status: {len(consumables_with_status)} gefunden")
    
    print("\n=== MongoDB Test erfolgreich! ===")
    print("Scandy läuft jetzt vollständig mit MongoDB.")
    print("Starten Sie die Anwendung mit: python -m flask run")
    
except Exception as e:
    print(f"✗ Fehler beim MongoDB-Test: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 