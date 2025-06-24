#!/usr/bin/env python3
"""
Test-Skript zum Überprüfen der Kategorien in beiden Routen
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.database_helpers import get_ticket_categories_from_settings

def test_routes():
    app = create_app()
    
    with app.app_context():
        print("=== Test: Kategorien in beiden Routen ===\n")
        
        # Teste die Funktion direkt
        categories = get_ticket_categories_from_settings()
        print(f"1. Direkter Aufruf von get_ticket_categories_from_settings():")
        print(f"   Kategorien: {categories}")
        print(f"   Anzahl: {len(categories)}")
        print()
        
        # Teste die Route-Funktionen
        from app.routes.tickets import public_create_order
        
        # Simuliere einen GET-Request für public_create_order
        from flask import request
        with app.test_request_context('/tickets/auftrag-neu'):
            try:
                # Hole die Kategorien wie in der Route
                categories_public = get_ticket_categories_from_settings()
                print(f"2. Kategorien in public_create_order Route:")
                print(f"   Kategorien: {categories_public}")
                print(f"   Anzahl: {len(categories_public)}")
            except Exception as e:
                print(f"   Fehler: {e}")
        
        print("\n=== Ende Test ===")

if __name__ == "__main__":
    test_routes() 