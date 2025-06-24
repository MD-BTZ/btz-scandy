#!/usr/bin/env python3
"""
Skript zur Initialisierung der Settings Collection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from app.utils.database_helpers import ensure_default_settings

def main():
    print("=== Initialisiere Settings Collection ===\n")
    
    try:
        # Initialisiere die Standard-Settings
        ensure_default_settings()
        print("✓ Settings Collection erfolgreich initialisiert")
        
        # Prüfe die vorhandenen Settings
        print("\n=== Vorhandene Settings ===")
        
        settings = mongodb.find('settings', {})
        for setting in settings:
            print(f"Key: {setting['key']}")
            print(f"Value: {setting['value']}")
            print()
        
        # Füge einige Standardwerte hinzu, falls die Listen leer sind
        print("=== Füge Standardwerte hinzu ===")
        
        # Standard-Kategorien
        categories_setting = mongodb.find_one('settings', {'key': 'categories'})
        if categories_setting and not categories_setting.get('value'):
            default_categories = ['Elektrowerkzeuge', 'Handwerkzeuge', 'Messwerkzeuge', 'Sicherheitsausrüstung']
            mongodb.update_one('settings', {'key': 'categories'}, {'$set': {'value': default_categories}})
            print("✓ Standard-Kategorien hinzugefügt")
        
        # Standard-Standorte
        locations_setting = mongodb.find_one('settings', {'key': 'locations'})
        if locations_setting and not locations_setting.get('value'):
            default_locations = ['Lager A', 'Lager B', 'Werkstatt', 'Büro']
            mongodb.update_one('settings', {'key': 'locations'}, {'$set': {'value': default_locations}})
            print("✓ Standard-Standorte hinzugefügt")
        
        # Standard-Abteilungen
        departments_setting = mongodb.find_one('settings', {'key': 'departments'})
        if departments_setting and not departments_setting.get('value'):
            default_departments = ['IT', 'Produktion', 'Verwaltung', 'Service']
            mongodb.update_one('settings', {'key': 'departments'}, {'$set': {'value': default_departments}})
            print("✓ Standard-Abteilungen hinzugefügt")
        
        # Standard-Ticket-Kategorien
        ticket_categories_setting = mongodb.find_one('settings', {'key': 'ticket_categories'})
        if ticket_categories_setting and not ticket_categories_setting.get('value'):
            default_ticket_categories = ['Bug', 'Feature Request', 'Support', 'Wartung']
            mongodb.update_one('settings', {'key': 'ticket_categories'}, {'$set': {'value': default_ticket_categories}})
            print("✓ Standard-Ticket-Kategorien hinzugefügt")
        
        print("\n=== Finale Settings ===")
        final_settings = mongodb.find('settings', {})
        for setting in final_settings:
            print(f"Key: {setting['key']}")
            print(f"Value: {setting['value']}")
            print()
        
        print("✓ Settings erfolgreich initialisiert!")
        
    except Exception as e:
        print(f"✗ Fehler bei der Initialisierung: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 