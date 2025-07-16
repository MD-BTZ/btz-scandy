#!/usr/bin/env python3
"""
Test-Skript für Lending-Konsistenz
Überprüft und behebt Inkonsistenzen in der Ausleihdatenbank
"""

import sys
import os
import json
from datetime import datetime

# Füge das App-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_lending_consistency():
    """Testet die Lending-Konsistenz"""
    try:
        from app.services.lending_service import LendingService
        from app.models.mongodb_database import mongodb
        
        print("🔍 Lending-Konsistenz-Test gestartet...")
        print("=" * 50)
        
        # 1. Konsistenz prüfen
        print("\n1. Konsistenzprüfung...")
        is_consistent, message, issues = LendingService.validate_lending_consistency()
        
        print(f"Status: {'✅ Konsistent' if is_consistent else '❌ Inkonsistent'}")
        print(f"Nachricht: {message}")
        
        if issues.get('total_issues', 0) > 0:
            print(f"\nGefundene Probleme ({issues['total_issues']}):")
            for i, issue in enumerate(issues.get('issues', []), 1):
                print(f"  {i}. {issue['message']}")
        
        # 2. Inkonsistenzen beheben (falls vorhanden)
        if not is_consistent:
            print("\n2. Behebe Inkonsistenzen...")
            success, message, statistics = LendingService.fix_lending_inconsistencies()
            
            if success:
                print(f"✅ {message}")
                if statistics:
                    print("Statistiken:")
                    for key, value in statistics.items():
                        print(f"  - {key}: {value}")
            else:
                print(f"❌ Fehler beim Beheben: {message}")
        
        # 3. Erneute Konsistenzprüfung
        print("\n3. Erneute Konsistenzprüfung...")
        is_consistent_after, message_after, issues_after = LendingService.validate_lending_consistency()
        
        print(f"Status: {'✅ Konsistent' if is_consistent_after else '❌ Inkonsistent'}")
        print(f"Nachricht: {message_after}")
        
        # 4. Aktuelle Ausleihen anzeigen
        print("\n4. Aktuelle Ausleihen:")
        active_lendings = LendingService.get_active_lendings()
        
        if active_lendings:
            print(f"Anzahl aktiver Ausleihen: {len(active_lendings)}")
            for i, lending in enumerate(active_lendings[:5], 1):  # Zeige nur die ersten 5
                tool_name = lending.get('tool_name', 'Unbekannt')
                worker_name = lending.get('worker_name', 'Unbekannt')
                lent_at = lending.get('lent_at', 'Unbekannt')
                
                if isinstance(lent_at, datetime):
                    lent_at = lent_at.strftime('%d.%m.%Y %H:%M')
                
                print(f"  {i}. {tool_name} → {worker_name} (seit {lent_at})")
            
            if len(active_lendings) > 5:
                print(f"  ... und {len(active_lendings) - 5} weitere")
        else:
            print("Keine aktiven Ausleihen")
        
        # 5. Werkzeug-Status-Übersicht
        print("\n5. Werkzeug-Status-Übersicht:")
        tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
        
        status_counts = {}
        for tool in tools:
            status = tool.get('status', 'unbekannt')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"  - {status}: {count}")
        
        # 6. Zusammenfassung
        print("\n" + "=" * 50)
        print("📊 ZUSAMMENFASSUNG")
        print("=" * 50)
        
        if is_consistent_after:
            print("✅ Alle Daten sind konsistent!")
        else:
            print("❌ Es bestehen noch Inkonsistenzen")
        
        print(f"📦 Gesamtanzahl Werkzeuge: {len(tools)}")
        print(f"📋 Aktive Ausleihen: {len(active_lendings)}")
        
        return is_consistent_after
        
    except Exception as e:
        print(f"❌ Fehler beim Test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_lending_operations():
    """Testet Lending-Operationen"""
    try:
        from app.services.lending_service import LendingService
        from app.models.mongodb_database import mongodb
        
        print("\n🧪 Teste Lending-Operationen...")
        
        # Finde ein verfügbares Werkzeug
        available_tool = mongodb.find_one('tools', {
            'status': 'verfügbar',
            'deleted': {'$ne': True}
        })
        
        if not available_tool:
            print("❌ Kein verfügbares Werkzeug für Tests gefunden")
            return False
        
        # Finde einen Mitarbeiter
        worker = mongodb.find_one('workers', {'deleted': {'$ne': True}})
        
        if not worker:
            print("❌ Kein Mitarbeiter für Tests gefunden")
            return False
        
        tool_barcode = available_tool['barcode']
        worker_barcode = worker['barcode']
        
        print(f"🔧 Teste mit Werkzeug: {available_tool['name']} ({tool_barcode})")
        print(f"👤 Teste mit Mitarbeiter: {worker['firstname']} {worker['lastname']} ({worker_barcode})")
        
        # Test 1: Ausleihe
        print("\n1. Teste Ausleihe...")
        lend_data = {
            'item_barcode': tool_barcode,
            'worker_barcode': worker_barcode,
            'action': 'lend',
            'item_type': 'tool',
            'quantity': 1
        }
        
        success, message, result = LendingService.process_lending_request(lend_data)
        
        if success:
            print(f"✅ Ausleihe erfolgreich: {message}")
        else:
            print(f"❌ Ausleihe fehlgeschlagen: {message}")
            return False
        
        # Test 2: Rückgabe
        print("\n2. Teste Rückgabe...")
        return_data = {
            'item_barcode': tool_barcode,
            'worker_barcode': worker_barcode,
            'action': 'return',
            'item_type': 'tool',
            'quantity': 1
        }
        
        success, message, result = LendingService.process_lending_request(return_data)
        
        if success:
            print(f"✅ Rückgabe erfolgreich: {message}")
        else:
            print(f"❌ Rückgabe fehlgeschlagen: {message}")
            return False
        
        print("\n✅ Alle Lending-Tests erfolgreich!")
        return True
        
    except Exception as e:
        print(f"❌ Fehler beim Testen der Lending-Operationen: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Hauptfunktion"""
    print("🚀 Lending-Konsistenz-Test-Suite")
    print("=" * 50)
    
    # Test 1: Konsistenzprüfung
    consistency_ok = test_lending_consistency()
    
    # Test 2: Lending-Operationen (nur wenn Konsistenz OK)
    if consistency_ok:
        operations_ok = test_lending_operations()
    else:
        print("\n⚠️  Überspringe Lending-Operationen-Tests wegen Inkonsistenzen")
        operations_ok = False
    
    # Ergebnis
    print("\n" + "=" * 50)
    print("🏁 ERGEBNIS")
    print("=" * 50)
    
    if consistency_ok and operations_ok:
        print("✅ Alle Tests erfolgreich!")
        return 0
    else:
        print("❌ Einige Tests fehlgeschlagen")
        if not consistency_ok:
            print("  - Konsistenzprüfung fehlgeschlagen")
        if not operations_ok:
            print("  - Lending-Operationen fehlgeschlagen")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 