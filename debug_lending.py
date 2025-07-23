#!/usr/bin/env python3
"""
Debug-Skript für Ausleihprobleme
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from datetime import datetime

def debug_lending_issues():
    """Debug-Ausleihprobleme"""
    print("=== DEBUG: Ausleihprobleme ===")
    
    # 1. Alle aktiven Ausleihen anzeigen
    print("\n1. Alle aktiven Ausleihen:")
    active_lendings = list(mongodb.find('lendings', {'returned_at': None}))
    for lending in active_lendings:
        print(f"  - Tool: {lending.get('tool_barcode')}, Worker: {lending.get('worker_barcode')}, Lent: {lending.get('lent_at')}")
    
    # 2. Alle Werkzeuge mit Status anzeigen
    print("\n2. Alle Werkzeuge mit Status:")
    tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
    for tool in tools:
        print(f"  - {tool.get('name')} ({tool.get('barcode')}): Status = {tool.get('status')}")
    
    # 3. Prüfe Inkonsistenzen
    print("\n3. Inkonsistenzen prüfen:")
    for tool in tools:
        barcode = tool.get('barcode')
        status = tool.get('status')
        
        # Prüfe aktive Ausleihe
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': barcode,
            'returned_at': None
        })
        
        if active_lending and status != 'ausgeliehen':
            print(f"  ❌ {tool.get('name')}: Status ist '{status}' aber hat aktive Ausleihe")
        elif not active_lending and status == 'ausgeliehen':
            print(f"  ❌ {tool.get('name')}: Status ist 'ausgeliehen' aber keine aktive Ausleihe")
        else:
            print(f"  ✅ {tool.get('name')}: Status '{status}' ist konsistent")
    
    # 4. Prüfe Mitarbeiter-Ausleihen
    print("\n4. Mitarbeiter-Ausleihen:")
    workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}))
    for worker in workers:
        barcode = worker.get('barcode')
        active_lendings = list(mongodb.find('lendings', {
            'worker_barcode': barcode,
            'returned_at': None
        }))
        if active_lendings:
            print(f"  - {worker.get('firstname')} {worker.get('lastname')} ({barcode}): {len(active_lendings)} aktive Ausleihen")
            for lending in active_lendings:
                tool = mongodb.find_one('tools', {'barcode': lending.get('tool_barcode')})
                tool_name = tool.get('name') if tool else 'Unbekannt'
                print(f"    * {tool_name} ({lending.get('tool_barcode')})")

def fix_lending_inconsistencies():
    """Behebt Inkonsistenzen in den Ausleihdaten"""
    print("\n=== FIX: Inkonsistenzen beheben ===")
    
    # 1. Werkzeuge mit falschem Status korrigieren
    tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
    fixed_count = 0
    
    for tool in tools:
        barcode = tool.get('barcode')
        status = tool.get('status')
        
        # Prüfe aktive Ausleihe
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': barcode,
            'returned_at': None
        })
        
        if active_lending and status != 'ausgeliehen':
            # Werkzeug ist ausgeliehen aber Status ist falsch
            mongodb.update_one('tools', 
                             {'barcode': barcode}, 
                             {'$set': {'status': 'ausgeliehen'}})
            print(f"  ✅ {tool.get('name')}: Status auf 'ausgeliehen' korrigiert")
            fixed_count += 1
        elif not active_lending and status == 'ausgeliehen':
            # Werkzeug ist nicht ausgeliehen aber Status ist falsch
            mongodb.update_one('tools', 
                             {'barcode': barcode}, 
                             {'$set': {'status': 'verfügbar'}})
            print(f"  ✅ {tool.get('name')}: Status auf 'verfügbar' korrigiert")
            fixed_count += 1
    
    print(f"\nInsgesamt {fixed_count} Werkzeug-Status korrigiert")
    
    # 2. Verwaiste Ausleihen bereinigen
    print("\n2. Verwaiste Ausleihen bereinigen:")
    orphaned_lendings = list(mongodb.find('lendings', {
        'returned_at': None,
        'tool_barcode': {'$exists': True}
    }))
    
    cleaned_count = 0
    for lending in orphaned_lendings:
        tool_barcode = lending.get('tool_barcode')
        tool = mongodb.find_one('tools', {'barcode': tool_barcode, 'deleted': {'$ne': True}})
        
        if not tool:
            # Werkzeug existiert nicht mehr, Ausleihe löschen
            mongodb.delete_one('lendings', {'_id': lending['_id']})
            print(f"  ✅ Verwaiste Ausleihe für nicht existierendes Werkzeug {tool_barcode} gelöscht")
            cleaned_count += 1
    
    print(f"Insgesamt {cleaned_count} verwaiste Ausleihen bereinigt")

if __name__ == "__main__":
    debug_lending_issues()
    
    response = input("\nMöchten Sie Inkonsistenzen automatisch beheben? (j/N): ")
    if response.lower() in ['j', 'ja', 'y', 'yes']:
        fix_lending_inconsistencies()
        print("\n=== Nach der Behebung ===")
        debug_lending_issues() 