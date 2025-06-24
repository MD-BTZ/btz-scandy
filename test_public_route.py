#!/usr/bin/env python3
"""
Test-Skript zum Überprüfen der öffentlichen Route ohne Login
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.database_helpers import get_ticket_categories_from_settings

def test_public_route():
    app = create_app()
    
    print("=== Test: Öffentliche Route ohne Login ===\n")
    
    # Test 1: Mit App-Kontext aber ohne Login
    with app.app_context():
        print("1. Test mit App-Kontext (ohne Login):")
        try:
            categories = get_ticket_categories_from_settings()
            print(f"   Kategorien: {categories}")
            print(f"   Anzahl: {len(categories)}")
        except Exception as e:
            print(f"   Fehler: {e}")
        print()
    
    # Test 2: Simuliere die Route direkt
    with app.test_request_context('/tickets/auftrag-neu'):
        print("2. Test mit Request-Kontext (ohne Login):")
        try:
            categories = get_ticket_categories_from_settings()
            print(f"   Kategorien: {categories}")
            print(f"   Anzahl: {len(categories)}")
        except Exception as e:
            print(f"   Fehler: {e}")
        print()
    
    # Test 3: Direkte Datenbankabfrage
    print("3. Direkte Datenbankabfrage:")
    try:
        from app.models.mongodb_database import mongodb
        settings_doc = mongodb.find_one('settings', {'key': 'ticket_categories'})
        if settings_doc and 'value' in settings_doc:
            print(f"   Kategorien: {settings_doc['value']}")
            print(f"   Anzahl: {len(settings_doc['value'])}")
        else:
            print("   Keine Kategorien gefunden")
    except Exception as e:
        print(f"   Fehler: {e}")
    
    print("\n=== Ende Test ===")

if __name__ == "__main__":
    test_public_route() 