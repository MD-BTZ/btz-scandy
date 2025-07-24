#!/usr/bin/env python3
"""
Debug-Skript für JavaScript-Funktionen
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import get_mongodb

def debug_javascript_functions():
    """Debug-Funktion für JavaScript-Funktionen"""
    print("=== DEBUG: JavaScript-Funktionen ===")
    
    mongodb = get_mongodb()
    
    # 1. Prüfe ob Ticket-Detail-Template die richtigen Funktionen hat
    print("\n1. Prüfe Ticket-Detail-Template:")
    
    try:
        with open('app/templates/tickets/detail.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'function updateTicketStatus' in content:
            print("   ✅ updateTicketStatus Funktion gefunden")
        else:
            print("   ❌ updateTicketStatus Funktion nicht gefunden")
            
        if 'function updateTicketAssignment' in content:
            print("   ✅ updateTicketAssignment Funktion gefunden")
        else:
            print("   ❌ updateTicketAssignment Funktion nicht gefunden")
            
        if 'onchange="updateTicketStatus' in content:
            print("   ✅ onchange Event für Status gefunden")
        else:
            print("   ❌ onchange Event für Status nicht gefunden")
            
        if 'onchange="updateTicketAssignment' in content:
            print("   ✅ onchange Event für Zuweisung gefunden")
        else:
            print("   ❌ onchange Event für Zuweisung nicht gefunden")
            
    except Exception as e:
        print(f"   ❌ Fehler beim Lesen der Template-Datei: {str(e)}")
    
    # 2. Prüfe ob View-Template die richtigen Funktionen hat
    print("\n2. Prüfe Ticket-View-Template:")
    
    try:
        with open('app/templates/tickets/view.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'function updateTicketStatus' in content:
            print("   ✅ updateTicketStatus Funktion gefunden")
        else:
            print("   ❌ updateTicketStatus Funktion nicht gefunden")
            
        if 'function updateTicketAssignment' in content:
            print("   ✅ updateTicketAssignment Funktion gefunden")
        else:
            print("   ❌ updateTicketAssignment Funktion nicht gefunden")
            
    except Exception as e:
        print(f"   ❌ Fehler beim Lesen der View-Template-Datei: {str(e)}")
    
    # 3. Prüfe Admin-Template
    print("\n3. Prüfe Admin-Ticket-Detail-Template:")
    
    try:
        with open('app/templates/admin/ticket_detail.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'function updateTicketStatus' in content:
            print("   ✅ updateTicketStatus Funktion gefunden")
        else:
            print("   ❌ updateTicketStatus Funktion nicht gefunden")
            
        if 'function updateTicketAssignment' in content:
            print("   ✅ updateTicketAssignment Funktion gefunden")
        else:
            print("   ❌ updateTicketAssignment Funktion nicht gefunden")
            
    except Exception as e:
        print(f"   ❌ Fehler beim Lesen der Admin-Template-Datei: {str(e)}")
    
    # 4. Teste Backend-Routes
    print("\n4. Teste Backend-Routes:")
    
    # Simuliere eine einfache Route-Prüfung
    routes_to_check = [
        '/tickets/<id>/update-status',
        '/tickets/<id>/update-assignment',
        '/admin/tickets/<id>/update-status',
        '/admin/tickets/<id>/update-assignment'
    ]
    
    for route in routes_to_check:
        print(f"   Route: {route}")
    
    # 5. Empfehlungen
    print("\n5. Empfehlungen:")
    print("   - Stelle sicher, dass die JavaScript-Funktionen vor den onchange Events geladen werden")
    print("   - Prüfe die Browser-Konsole auf JavaScript-Fehler")
    print("   - Teste die Funktionen direkt in der Browser-Konsole")
    print("   - Stelle sicher, dass showToast Funktion verfügbar ist")
    
    print("\n=== DEBUG ENDE ===")

if __name__ == "__main__":
    debug_javascript_functions() 