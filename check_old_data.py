#!/usr/bin/env python3
"""
Skript zum Überprüfen der ursprünglichen Daten in den Collections
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb

def main():
    print("=== Überprüfe ursprüngliche Collections ===\n")
    
    try:
        # Prüfe Kategorien-Collection
        print("1. Kategorien-Collection:")
        categories = list(mongodb.find('categories', {}))
        print(f"   Anzahl: {len(categories)}")
        for cat in categories:
            print(f"   - {cat.get('name', 'Unbekannt')} (ID: {cat.get('_id')})")
        print()
        
        # Prüfe Standorte-Collection
        print("2. Standorte-Collection:")
        locations = list(mongodb.find('locations', {}))
        print(f"   Anzahl: {len(locations)}")
        for loc in locations:
            print(f"   - {loc.get('name', 'Unbekannt')} (ID: {loc.get('_id')})")
        print()
        
        # Prüfe Abteilungen-Collection
        print("3. Abteilungen-Collection:")
        departments = list(mongodb.find('departments', {}))
        print(f"   Anzahl: {len(departments)}")
        for dept in departments:
            print(f"   - {dept.get('name', 'Unbekannt')} (ID: {dept.get('_id')})")
        print()
        
        # Prüfe Settings-Collection
        print("4. Settings-Collection:")
        settings = list(mongodb.find('settings', {}))
        print(f"   Anzahl: {len(settings)}")
        for setting in settings:
            print(f"   - {setting.get('key', 'Unbekannt')}: {setting.get('value', 'Kein Wert')}")
        print()
        
    except Exception as e:
        print(f"✗ Fehler bei der Überprüfung: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 