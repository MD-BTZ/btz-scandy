#!/usr/bin/env python3
"""
Debug-Skript für Datenbankabfragen
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import MongoDB
from app.models.mongodb_models import MongoDBTool

def debug_database():
    """Debug-Funktion für Datenbankabfragen"""
    mongodb = MongoDB()
    
    print("=== DATENBANK DEBUG ===")
    
    # 1. Tools überprüfen
    print("\n--- TOOLS ---")
    tools = list(mongodb.find('tools', {}))
    print(f"Anzahl Tools insgesamt: {len(tools)}")
    
    if tools:
        print("Erste 3 Tools:")
        for i, tool in enumerate(tools[:3]):
            print(f"  {i+1}. ID: {tool.get('_id')}, Name: {tool.get('name')}, Status: {tool.get('status')}, Deleted: {tool.get('deleted')}")
    
    # Tools ohne deleted=True
    active_tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
    print(f"Tools ohne deleted=True: {len(active_tools)}")
    
    # Tools nach Status
    for status in ['available', 'verfügbar', 'lent', 'ausgeliehen', 'defect', 'defekt']:
        count = mongodb.count_documents('tools', {'deleted': {'$ne': True}, 'status': status})
        print(f"  Status '{status}': {count}")
    
    # Tools ohne Status
    no_status = mongodb.count_documents('tools', {'deleted': {'$ne': True}, 'status': {'$exists': False}})
    print(f"  Ohne Status: {no_status}")
    
    # 2. Consumables überprüfen
    print("\n--- CONSUMABLES ---")
    consumables = list(mongodb.find('consumables', {}))
    print(f"Anzahl Consumables insgesamt: {len(consumables)}")
    
    if consumables:
        print("Erste 3 Consumables:")
        for i, consumable in enumerate(consumables[:3]):
            print(f"  {i+1}. ID: {consumable.get('_id')}, Name: {consumable.get('name')}, Quantity: {consumable.get('quantity')}, Min: {consumable.get('min_quantity')}, Deleted: {consumable.get('deleted')}")
    
    active_consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
    print(f"Consumables ohne deleted=True: {len(active_consumables)}")
    
    # 3. Workers überprüfen
    print("\n--- WORKERS ---")
    workers = list(mongodb.find('workers', {}))
    print(f"Anzahl Workers insgesamt: {len(workers)}")
    
    if workers:
        print("Erste 3 Workers:")
        for i, worker in enumerate(workers[:3]):
            print(f"  {i+1}. ID: {worker.get('_id')}, Name: {worker.get('firstname')} {worker.get('lastname')}, Department: {worker.get('department')}, Deleted: {worker.get('deleted')}")
    
    active_workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}))
    print(f"Workers ohne deleted=True: {len(active_workers)}")
    
    # 4. Lendings überprüfen
    print("\n--- LENDINGS ---")
    lendings = list(mongodb.find('lendings', {}))
    print(f"Anzahl Lendings insgesamt: {len(lendings)}")
    
    active_lendings = list(mongodb.find('lendings', {'returned_at': {'$exists': False}}))
    print(f"Aktive Lendings (ohne returned_at): {len(active_lendings)}")
    
    # 5. Test der get_statistics Methode
    print("\n--- GET_STATISTICS TEST ---")
    try:
        stats = MongoDBTool.get_statistics()
        print("Tool Stats:", stats['tool_stats'])
        print("Consumable Stats:", stats['consumable_stats'])
        print("Worker Stats:", stats['worker_stats'])
        print("Current Lendings:", stats['current_lendings'])
    except Exception as e:
        print(f"Fehler in get_statistics: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_database() 