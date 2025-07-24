#!/usr/bin/env python3
"""
Test-Skript für Ticket-Funktionen
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ticket_functions():
    """Test-Funktion für Ticket-Funktionen"""
    print("=== TEST: Ticket-Funktionen ===")
    
    # 1. Prüfe detail.html Template
    print("\n1. Prüfe detail.html Template:")
    
    try:
        with open('app/templates/tickets/detail.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Prüfe showToast Funktion
        if 'if (typeof showToast === \'undefined\')' in content:
            print("   ✅ showToast Fallback-Funktion gefunden")
        else:
            print("   ❌ showToast Fallback-Funktion nicht gefunden")
            
        # Prüfe JavaScript-Funktionen
        if 'function updateTicketStatus' in content:
            print("   ✅ updateTicketStatus Funktion gefunden")
        else:
            print("   ❌ updateTicketStatus Funktion nicht gefunden")
            
        if 'function updateTicketAssignment' in content:
            print("   ✅ updateTicketAssignment Funktion gefunden")
        else:
            print("   ❌ updateTicketAssignment Funktion nicht gefunden")
            
        if 'function updateTicketCategory' in content:
            print("   ✅ updateTicketCategory Funktion gefunden")
        else:
            print("   ❌ updateTicketCategory Funktion nicht gefunden")
            
        # Prüfe Debug-Ausgaben
        if 'console.log(' in content:
            print("   ✅ Debug-Ausgaben gefunden")
        else:
            print("   ❌ Debug-Ausgaben nicht gefunden")
            
        # Prüfe onchange Events
        if 'onchange="updateTicketStatus' in content:
            print("   ✅ onchange Event für Status gefunden")
        else:
            print("   ❌ onchange Event für Status nicht gefunden")
            
        if 'onchange="updateTicketAssignment' in content:
            print("   ✅ onchange Event für Zuweisung gefunden")
        else:
            print("   ❌ onchange Event für Zuweisung nicht gefunden")
            
        if 'onchange="updateTicketCategory' in content:
            print("   ✅ onchange Event für Kategorie gefunden")
        else:
            print("   ❌ onchange Event für Kategorie nicht gefunden")
            
    except Exception as e:
        print(f"   ❌ Fehler beim Lesen der Template-Datei: {str(e)}")
    
    # 2. Prüfe Backend-Routes
    print("\n2. Prüfe Backend-Routes:")
    
    try:
        with open('app/routes/tickets.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if '@bp.route(\'/<id>/update-status\'' in content:
            print("   ✅ update-status Route gefunden")
        else:
            print("   ❌ update-status Route nicht gefunden")
            
        if '@bp.route(\'/<id>/update-assignment\'' in content:
            print("   ✅ update-assignment Route gefunden")
        else:
            print("   ❌ update-assignment Route nicht gefunden")
            
        if '@bp.route(\'/<id>/update-details\'' in content:
            print("   ✅ update-details Route gefunden")
        else:
            print("   ❌ update-details Route nicht gefunden")
            
    except Exception as e:
        print(f"   ❌ Fehler beim Lesen der Routes-Datei: {str(e)}")
    
    # 3. Browser-Test-Anweisungen
    print("\n3. Browser-Test-Anweisungen:")
    print("   1. Öffne die Browser-Konsole (F12)")
    print("   2. Prüfe die Debug-Ausgaben:")
    print("      - updateTicketStatus verfügbar: function")
    print("      - updateTicketAssignment verfügbar: function")
    print("      - updateTicketCategory verfügbar: function")
    print("      - showToast verfügbar: function")
    print("   3. Teste die Funktionen direkt:")
    print("      updateTicketStatus('in_bearbeitung')")
    print("      updateTicketAssignment('admin')")
    print("      updateTicketCategory('Wartung')")
    print("   4. Prüfe ob Toast-Nachrichten erscheinen")
    print("   5. Prüfe ob die Seite nach 1 Sekunde neu lädt")
    
    print("\n=== TEST ENDE ===")

if __name__ == "__main__":
    test_ticket_functions() 