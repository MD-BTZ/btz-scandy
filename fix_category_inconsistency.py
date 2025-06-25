#!/usr/bin/env python3
"""
Skript zum Beheben von Kategorien-Inkonsistenzen in der Scandy-Datenbank
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb

def fix_category_inconsistency():
    """Behebt Inkonsistenzen zwischen Kategorien in den Settings und den tatsächlich verwendeten Kategorien"""
    try:
        print("=== Behebe Kategorien-Inkonsistenz ===\n")
        
        # Sammle alle verwendeten Kategorien aus den Daten
        used_categories = set()
        used_locations = set()
        used_departments = set()
        
        # Aus Werkzeugen
        print("1. Analysiere Werkzeuge...")
        tools = list(mongodb.find('tools', {}))
        for tool in tools:
            if tool.get('category'):
                used_categories.add(tool['category'])
            if tool.get('location'):
                used_locations.add(tool['location'])
        print(f"   Gefundene Kategorien: {list(used_categories)}")
        print(f"   Gefundene Standorte: {list(used_locations)}")
        
        # Aus Verbrauchsgütern
        print("\n2. Analysiere Verbrauchsgüter...")
        consumables = list(mongodb.find('consumables', {}))
        for consumable in consumables:
            if consumable.get('category'):
                used_categories.add(consumable['category'])
            if consumable.get('location'):
                used_locations.add(consumable['location'])
        print(f"   Gefundene Kategorien: {list(used_categories)}")
        print(f"   Gefundene Standorte: {list(used_locations)}")
        
        # Aus Mitarbeitern (Abteilungen)
        print("\n3. Analysiere Mitarbeiter...")
        workers = list(mongodb.find('workers', {}))
        for worker in workers:
            if worker.get('department'):
                used_departments.add(worker['department'])
        print(f"   Gefundene Abteilungen: {list(used_departments)}")
        
        # Aktualisiere die Settings
        print("\n4. Aktualisiere Settings...")
        
        # Kategorien
        if used_categories:
            categories_list = list(used_categories)
            mongodb.update_one('settings', 
                             {'key': 'categories'}, 
                             {'$set': {'value': categories_list}}, 
                             upsert=True)
            print(f"   ✓ Kategorien aktualisiert: {categories_list}")
        else:
            print("   ⚠️ Keine Kategorien gefunden")
        
        # Standorte
        if used_locations:
            locations_list = list(used_locations)
            mongodb.update_one('settings', 
                             {'key': 'locations'}, 
                             {'$set': {'value': locations_list}}, 
                             upsert=True)
            print(f"   ✓ Standorte aktualisiert: {locations_list}")
        else:
            print("   ⚠️ Keine Standorte gefunden")
        
        # Abteilungen
        if used_departments:
            departments_list = list(used_departments)
            mongodb.update_one('settings', 
                             {'key': 'departments'}, 
                             {'$set': {'value': departments_list}}, 
                             upsert=True)
            print(f"   ✓ Abteilungen aktualisiert: {departments_list}")
        else:
            print("   ⚠️ Keine Abteilungen gefunden")
        
        print("\n=== Kategorien-Inkonsistenz behoben! ===")
        
    except Exception as e:
        print(f"✗ Fehler beim Beheben der Kategorien-Inkonsistenz: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_category_inconsistency() 