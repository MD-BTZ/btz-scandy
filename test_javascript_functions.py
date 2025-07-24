#!/usr/bin/env python3
"""
Test-Skript für JavaScript-Funktionen
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_javascript_functions():
    """Test-Funktion für JavaScript-Funktionen"""
    print("=== TEST: JavaScript-Funktionen ===")
    
    # 1. Prüfe detail.html Template
    print("\n1. Prüfe detail.html Template:")
    
    try:
        with open('app/templates/tickets/detail.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Prüfe head Block
        if '{% block head %}' in content:
            print("   ✅ head Block gefunden")
        else:
            print("   ❌ head Block nicht gefunden")
            
        # Prüfe JavaScript-Funktionen im head Block
        if 'function updateTicketStatus' in content:
            print("   ✅ updateTicketStatus im head Block gefunden")
        else:
            print("   ❌ updateTicketStatus im head Block nicht gefunden")
            
        if 'function updateTicketAssignment' in content:
            print("   ✅ updateTicketAssignment im head Block gefunden")
        else:
            print("   ❌ updateTicketAssignment im head Block nicht gefunden")
            
        if 'function updateTicketCategory' in content:
            print("   ✅ updateTicketCategory im head Block gefunden")
        else:
            print("   ❌ updateTicketCategory im head Block nicht gefunden")
            
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
            
        # Prüfe Debug-Ausgaben
        if 'console.log' in content:
            print("   ✅ Debug-Ausgaben gefunden")
        else:
            print("   ❌ Debug-Ausgaben nicht gefunden")
            
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
    
    # 3. Empfehlungen
    print("\n3. Empfehlungen:")
    print("   - Öffne die Browser-Konsole (F12)")
    print("   - Prüfe ob die Debug-Ausgaben erscheinen:")
    print("     console.log('updateTicketStatus verfügbar:', typeof updateTicketStatus);")
    print("   - Teste die Funktionen direkt in der Konsole:")
    print("     updateTicketStatus('in_bearbeitung')")
    print("     updateTicketAssignment('admin')")
    print("   - Prüfe ob showToast Funktion verfügbar ist")
    print("   - Stelle sicher, dass die Seite vollständig geladen ist")
    
    print("\n=== TEST ENDE ===")

if __name__ == "__main__":
    test_javascript_functions() 