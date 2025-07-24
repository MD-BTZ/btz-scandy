#!/usr/bin/env python3
"""
Debug-Skript für offene Tickets
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import get_mongodb
from app.services.ticket_service import TicketService

def debug_open_tickets():
    """Debug-Funktion für offene Tickets"""
    print("=== DEBUG: Offene Tickets ===")
    
    mongodb = get_mongodb()
    ticket_service = TicketService()
    
    # 1. Alle Tickets in der Datenbank
    print("\n1. Alle Tickets in der Datenbank:")
    all_tickets = list(mongodb.find('tickets', {}))
    print(f"   Gesamtanzahl: {len(all_tickets)}")
    
    for ticket in all_tickets[:5]:  # Zeige nur die ersten 5
        print(f"   - ID: {ticket.get('_id')}")
        print(f"     Titel: {ticket.get('title', 'Kein Titel')}")
        print(f"     Status: {ticket.get('status', 'Kein Status')}")
        print(f"     Zugewiesen an: {ticket.get('assigned_to', 'Nicht zugewiesen')}")
        print(f"     Gelöscht: {ticket.get('deleted', False)}")
        print()
    
    # 2. Offene Tickets (nicht zugewiesene)
    print("\n2. Offene Tickets (nicht zugewiesene):")
    open_query = {
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
    }
    
    open_tickets = list(mongodb.find('tickets', open_query))
    print(f"   Anzahl: {len(open_tickets)}")
    
    for ticket in open_tickets:
        print(f"   - ID: {ticket.get('_id')}")
        print(f"     Titel: {ticket.get('title', 'Kein Titel')}")
        print(f"     Status: {ticket.get('status', 'Kein Status')}")
        print(f"     Zugewiesen an: {ticket.get('assigned_to', 'Nicht zugewiesen')}")
        print()
    
    # 3. Teste verschiedene Queries
    print("\n3. Teste verschiedene Queries:")
    
    # Query 1: Nur Status 'offen'
    query1 = {'status': 'offen', 'deleted': {'$ne': True}}
    count1 = mongodb.count_documents('tickets', query1)
    print(f"   Nur Status 'offen': {count1}")
    
    # Query 2: Nicht zugewiesene (alle Status)
    query2 = {
        '$or': [
            {'assigned_to': None},
            {'assigned_to': ''},
            {'assigned_to': {'$exists': False}}
        ],
        'deleted': {'$ne': True}
    }
    count2 = mongodb.count_documents('tickets', query2)
    print(f"   Nicht zugewiesene (alle Status): {count2}")
    
    # Query 3: Offene und nicht zugewiesene
    query3 = {
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
    }
    count3 = mongodb.count_documents('tickets', query3)
    print(f"   Offene und nicht zugewiesene: {count3}")
    
    # 4. Teste TicketService
    print("\n4. TicketService Test:")
    unassigned_count = ticket_service.get_unassigned_ticket_count()
    print(f"   get_unassigned_ticket_count(): {unassigned_count}")
    
    # 5. Teste get_tickets_by_user für Admin
    print("\n5. get_tickets_by_user Test (Admin):")
    tickets_data = ticket_service.get_tickets_by_user('admin', 'admin')
    print(f"   Offene Tickets: {len(tickets_data['open_tickets'])}")
    print(f"   Zugewiesene Tickets: {len(tickets_data['assigned_tickets'])}")
    print(f"   Alle Tickets: {len(tickets_data['all_tickets'])}")
    
    # 6. Zeige Details der offenen Tickets
    print("\n6. Details der offenen Tickets:")
    for ticket in tickets_data['open_tickets']:
        print(f"   - ID: {ticket.get('id')}")
        print(f"     Titel: {ticket.get('title', 'Kein Titel')}")
        print(f"     Status: {ticket.get('status', 'Kein Status')}")
        print(f"     Zugewiesen an: {ticket.get('assigned_to', 'Nicht zugewiesen')}")
        print()
    
    print("=== DEBUG ENDE ===")

if __name__ == "__main__":
    debug_open_tickets() 