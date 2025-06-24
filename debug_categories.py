#!/usr/bin/env python3
"""
Debug-Skript zum Überprüfen der Kategorien in der Datenbank
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from app.utils.database_helpers import get_ticket_categories_from_settings, get_categories_from_settings

def main():
    print("=== Debug: Kategorien in der Datenbank ===\n")
    
    # Prüfe Ticket-Kategorien
    print("1. Ticket-Kategorien (get_ticket_categories_from_settings):")
    ticket_categories = get_ticket_categories_from_settings()
    print(f"   Anzahl: {len(ticket_categories)}")
    print(f"   Kategorien: {ticket_categories}")
    print()
    
    # Prüfe normale Kategorien
    print("2. Normale Kategorien (get_categories_from_settings):")
    normal_categories = get_categories_from_settings()
    print(f"   Anzahl: {len(normal_categories)}")
    print(f"   Kategorien: {normal_categories}")
    print()
    
    # Prüfe direkt in der Datenbank
    print("3. Direkte Datenbankabfrage:")
    try:
        settings_doc = mongodb.find_one('settings', {'key': 'ticket_categories'})
        print(f"   Ticket-Kategorien Dokument: {settings_doc}")
        
        settings_doc_normal = mongodb.find_one('settings', {'key': 'categories'})
        print(f"   Normale Kategorien Dokument: {settings_doc_normal}")
    except Exception as e:
        print(f"   Fehler bei Datenbankabfrage: {e}")
    
    print("\n=== Ende Debug ===")

if __name__ == "__main__":
    main() 