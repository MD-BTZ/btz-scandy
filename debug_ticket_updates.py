#!/usr/bin/env python3
"""
Debug-Skript für Ticket-Updates
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import get_mongodb
from datetime import datetime

def debug_ticket_updates():
    """Debug-Funktion für Ticket-Updates"""
    print("=== DEBUG: Ticket Updates ===")
    
    mongodb = get_mongodb()
    
    # 1. Finde ein Test-Ticket
    print("\n1. Suche Test-Ticket:")
    test_ticket = mongodb.find_one('tickets', {'status': 'offen'})
    
    if not test_ticket:
        print("   Kein offenes Ticket gefunden!")
        return
    
    ticket_id = str(test_ticket['_id'])
    print(f"   Test-Ticket gefunden: {ticket_id}")
    print(f"   Titel: {test_ticket.get('title', 'Kein Titel')}")
    print(f"   Status: {test_ticket.get('status', 'Kein Status')}")
    print(f"   Zugewiesen an: {test_ticket.get('assigned_to', 'Nicht zugewiesen')}")
    
    # 2. Teste Status-Update
    print("\n2. Teste Status-Update:")
    try:
        from bson import ObjectId
        ticket_id_obj = ObjectId(ticket_id)
        
        # Update Status auf 'in_bearbeitung'
        result = mongodb.update_one('tickets', 
                                  {'_id': ticket_id_obj}, 
                                  {'$set': {'status': 'in_bearbeitung', 'updated_at': datetime.now()}})
        
        print(f"   Status-Update Ergebnis: {result.modified_count} Dokumente aktualisiert")
        
        # Prüfe das Ergebnis
        updated_ticket = mongodb.find_one('tickets', {'_id': ticket_id_obj})
        print(f"   Neuer Status: {updated_ticket.get('status', 'Kein Status')}")
        
    except Exception as e:
        print(f"   Fehler beim Status-Update: {str(e)}")
    
    # 3. Teste Zuweisungs-Update
    print("\n3. Teste Zuweisungs-Update:")
    try:
        # Update Zuweisung auf 'admin'
        result = mongodb.update_one('tickets', 
                                  {'_id': ticket_id_obj}, 
                                  {'$set': {'assigned_to': 'admin', 'updated_at': datetime.now()}})
        
        print(f"   Zuweisungs-Update Ergebnis: {result.modified_count} Dokumente aktualisiert")
        
        # Prüfe das Ergebnis
        updated_ticket = mongodb.find_one('tickets', {'_id': ticket_id_obj})
        print(f"   Neue Zuweisung: {updated_ticket.get('assigned_to', 'Nicht zugewiesen')}")
        
    except Exception as e:
        print(f"   Fehler beim Zuweisungs-Update: {str(e)}")
    
    # 4. Teste automatische Zuweisung bei Status-Änderung
    print("\n4. Teste automatische Zuweisung:")
    try:
        # Setze Status zurück auf 'offen' und entferne Zuweisung
        mongodb.update_one('tickets', 
                          {'_id': ticket_id_obj}, 
                          {'$set': {'status': 'offen', 'assigned_to': None, 'updated_at': datetime.now()}})
        
        print("   Status auf 'offen' gesetzt, Zuweisung entfernt")
        
        # Jetzt ändere Status auf 'in_bearbeitung' (sollte automatisch zuweisen)
        result = mongodb.update_one('tickets', 
                                  {'_id': ticket_id_obj}, 
                                  {'$set': {'status': 'in_bearbeitung', 'assigned_to': 'test_user', 'updated_at': datetime.now()}})
        
        print(f"   Automatische Zuweisung Ergebnis: {result.modified_count} Dokumente aktualisiert")
        
        # Prüfe das Ergebnis
        updated_ticket = mongodb.find_one('tickets', {'_id': ticket_id_obj})
        print(f"   Neuer Status: {updated_ticket.get('status', 'Kein Status')}")
        print(f"   Neue Zuweisung: {updated_ticket.get('assigned_to', 'Nicht zugewiesen')}")
        
    except Exception as e:
        print(f"   Fehler bei automatischer Zuweisung: {str(e)}")
    
    # 5. Prüfe aktuelle Ticket-Listen
    print("\n5. Prüfe aktuelle Ticket-Listen:")
    
    # Offene Tickets
    open_tickets = list(mongodb.find('tickets', {
        '$and': [
            {
                '$or': [
                    {'assigned_to': None},
                    {'assigned_to': ''},
                    {'assigned_to': {'$exists': False}}
                ]
            },
            {'status': 'offen'},
            {'deleted': {'$ne': True}}
        ]
    }))
    print(f"   Offene Tickets: {len(open_tickets)}")
    
    # Zugewiesene Tickets
    assigned_tickets = list(mongodb.find('tickets', {
        'assigned_to': {'$ne': None, '$ne': ''},
        'deleted': {'$ne': True}
    }))
    print(f"   Zugewiesene Tickets: {len(assigned_tickets)}")
    
    # Alle Tickets
    all_tickets = list(mongodb.find('tickets', {'deleted': {'$ne': True}}))
    print(f"   Alle Tickets: {len(all_tickets)}")
    
    print("\n=== DEBUG ENDE ===")

if __name__ == "__main__":
    debug_ticket_updates() 