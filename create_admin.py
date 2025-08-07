#!/usr/bin/env python3
"""
Skript zum Erstellen des Admin-Benutzers.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from datetime import datetime
from app.models.mongodb_database import MongoDB

def create_admin_user():
    """Erstellt den Admin-Benutzer in der Datenbank"""
    try:
        mongodb = MongoDB()
        
        # Admin-Daten
        admin_data = {
            'username': 'Admin',
            'password_hash': generate_password_hash('admin123'),
            'role': 'admin',
            'is_active': True,
            'timesheet_enabled': False,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Prüfe ob Admin bereits existiert
        existing_admin = mongodb.find_one('users', {'username': 'Admin'})
        if existing_admin:
            print("Admin-Benutzer existiert bereits!")
            return
        
        # Admin erstellen
        result = mongodb.insert_one('users', admin_data)
        print(f"Admin-Benutzer erfolgreich erstellt mit ID: {result.inserted_id}")
        
        # Systemeinstellungen
        settings = [
            {'key': 'label_tickets_name', 'value': 'Tickets'},
            {'key': 'label_tickets_icon', 'value': 'fas fa-ticket-alt'},
            {'key': 'label_tools_name', 'value': 'Werkzeuge'},
            {'key': 'label_tools_icon', 'value': 'fas fa-tools'},
            {'key': 'label_consumables_name', 'value': 'Verbrauchsmaterial'},
            {'key': 'label_consumables_icon', 'value': 'fas fa-box-open'}
        ]
        
        for setting in settings:
            mongodb.update_one('settings', {'key': setting['key']}, {'$set': setting}, upsert=True)
        
        print("Systemeinstellungen gespeichert")
        print("Setup abgeschlossen!")
        print("Login-Daten: Username: Admin, Password: admin123")
        
    except Exception as e:
        print(f"Fehler beim Erstellen des Admin-Benutzers: {e}")

if __name__ == "__main__":
    create_admin_user() 