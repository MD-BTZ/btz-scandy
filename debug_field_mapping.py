#!/usr/bin/env python3
"""
Debug-Skript für Feldzuordnung zwischen Tools und Workers
"""
import sys
import os

# Füge das app-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.models.mongodb_database import mongodb
    
    print("=== FELDZUORDNUNG DEBUG ===")
    
    # 1. Überprüfe Tools
    print("\n1. TOOLS - Aktuelle Felder:")
    tools = mongodb.find('tools', {'deleted': {'$ne': True}}, limit=5)
    
    if tools:
        # Zeige alle verfügbaren Felder des ersten Tools
        first_tool = tools[0]
        print(f"Verfügbare Felder: {list(first_tool.keys())}")
        
        print("\nErste 5 Tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  Tool {i}:")
            print(f"    Name: {tool.get('name', 'N/A')}")
            print(f"    Barcode: {tool.get('barcode', 'N/A')}")
            print(f"    Category: {tool.get('category', 'N/A')}")
            print(f"    Department: {tool.get('department', 'N/A')}")
            print(f"    Location: {tool.get('location', 'N/A')}")
            print(f"    Description: {tool.get('description', 'N/A')}")
            print()
    else:
        print("Keine Tools gefunden")
    
    # 2. Überprüfe Workers
    print("\n2. WORKERS - Aktuelle Felder:")
    workers = mongodb.find('workers', {'deleted': {'$ne': True}}, limit=5)
    
    if workers:
        # Zeige alle verfügbaren Felder des ersten Workers
        first_worker = workers[0]
        print(f"Verfügbare Felder: {list(first_worker.keys())}")
        
        print("\nErste 5 Workers:")
        for i, worker in enumerate(workers, 1):
            print(f"  Worker {i}:")
            print(f"    Name: {worker.get('firstname', 'N/A')} {worker.get('lastname', 'N/A')}")
            print(f"    Barcode: {worker.get('barcode', 'N/A')}")
            print(f"    Department: {worker.get('department', 'N/A')}")
            print(f"    Category: {worker.get('category', 'N/A')}")
            print(f"    Email: {worker.get('email', 'N/A')}")
            print()
    else:
        print("Keine Workers gefunden")
    
    # 3. Überprüfe alle eindeutigen Werte für Category und Department
    print("\n3. EINDEUTIGE WERTE:")
    
    # Tools - Category
    tool_categories = set()
    for tool in mongodb.find('tools', {'deleted': {'$ne': True}, 'category': {'$exists': True, '$ne': None, '$ne': ''}}):
        tool_categories.add(tool.get('category'))
    print(f"Tool Categories: {sorted(list(tool_categories))}")
    
    # Tools - Department
    tool_departments = set()
    for tool in mongodb.find('tools', {'deleted': {'$ne': True}, 'department': {'$exists': True, '$ne': None, '$ne': ''}}):
        tool_departments.add(tool.get('department'))
    print(f"Tool Departments: {sorted(list(tool_departments))}")
    
    # Workers - Department
    worker_departments = set()
    for worker in mongodb.find('workers', {'deleted': {'$ne': True}, 'department': {'$exists': True, '$ne': None, '$ne': ''}}):
        worker_departments.add(worker.get('department'))
    print(f"Worker Departments: {sorted(list(worker_departments))}")
    
    # Workers - Category
    worker_categories = set()
    for worker in mongodb.find('workers', {'deleted': {'$ne': True}, 'category': {'$exists': True, '$ne': None, '$ne': ''}}):
        worker_categories.add(worker.get('category'))
    print(f"Worker Categories: {sorted(list(worker_categories))}")
    
    # 4. Überprüfe auf mögliche Verwechslungen
    print("\n4. MÖGLICHE VERWECHSLUNGEN:")
    
    # Prüfe ob Tool-Categories Worker-Departments enthalten
    tool_cat_worker_dept_overlap = tool_categories.intersection(worker_departments)
    if tool_cat_worker_dept_overlap:
        print(f"⚠️  Tool Categories enthalten Worker Departments: {tool_cat_worker_dept_overlap}")
    
    # Prüfe ob Worker-Categories Tool-Departments enthalten
    worker_cat_tool_dept_overlap = worker_categories.intersection(tool_departments)
    if worker_cat_tool_dept_overlap:
        print(f"⚠️  Worker Categories enthalten Tool Departments: {worker_cat_tool_dept_overlap}")
    
    # Prüfe ob Tool-Departments Worker-Departments enthalten
    tool_dept_worker_dept_overlap = tool_departments.intersection(worker_departments)
    if tool_dept_worker_dept_overlap:
        print(f"ℹ️  Tool Departments und Worker Departments überschneiden sich: {tool_dept_worker_dept_overlap}")
    
    # 5. Überprüfe Settings für Kategorien und Abteilungen
    print("\n5. SYSTEM-EINSTELLUNGEN:")
    
    # Kategorien aus Settings
    categories_setting = mongodb.find_one('settings', {'key': 'categories'})
    if categories_setting:
        print(f"System Categories: {categories_setting.get('value', [])}")
    else:
        print("System Categories: Nicht gefunden")
    
    # Abteilungen aus Settings
    departments_setting = mongodb.find_one('settings', {'key': 'departments'})
    if departments_setting:
        print(f"System Departments: {departments_setting.get('value', [])}")
    else:
        print("System Departments: Nicht gefunden")
    
    print("\n=== DEBUG ABGESCHLOSSEN ===")
    
except ImportError as e:
    print(f"Import-Fehler: {e}")
    print("Stelle sicher, dass alle Abhängigkeiten installiert sind.")
except Exception as e:
    print(f"Unerwarteter Fehler: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}") 