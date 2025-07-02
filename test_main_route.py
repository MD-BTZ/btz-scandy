#!/usr/bin/env python3
"""
Test-Skript für die Hauptseite-Route
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.routes.main import index
from flask import Flask
from flask_login import current_user

def test_main_route():
    """Testet die Hauptseite-Route"""
    print("=== TEST HAUPTSEITE ROUTE ===")
    
    # Erstelle eine minimale Flask-App für den Test
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    
    with app.app_context():
        try:
            # Simuliere einen nicht-eingeloggten Benutzer
            result = index()
            print("Route-Aufruf erfolgreich")
            print(f"Resultat-Typ: {type(result)}")
            
            # Wenn es ein Template-Render ist, extrahiere die Variablen
            if hasattr(result, 'template'):
                print("Template-Variablen:")
                for key, value in result.template_vars.items():
                    if 'stats' in key or 'tool' in key or 'consumable' in key or 'worker' in key:
                        print(f"  {key}: {value}")
            
        except Exception as e:
            print(f"Fehler beim Testen der Route: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_main_route() 