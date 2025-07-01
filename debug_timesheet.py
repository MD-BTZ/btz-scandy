#!/usr/bin/env python3
"""
Debug-Script für timesheet_enabled Problem
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from app.models.user import User

def debug_timesheet_enabled():
    print("=== DEBUG: timesheet_enabled Problem ===\n")
    
    # Hole alle Benutzer
    users = list(mongodb.find('users', {}))
    
    print(f"Anzahl Benutzer: {len(users)}\n")
    
    for user in users:
        print(f"Benutzer: {user.get('username', 'N/A')}")
        print(f"  - timesheet_enabled in DB: {user.get('timesheet_enabled', 'FELD NICHT VORHANDEN')}")
        print(f"  - Rolle: {user.get('role', 'N/A')}")
        
        # Erstelle User-Objekt
        user_obj = User(user)
        print(f"  - timesheet_enabled im User-Objekt: {user_obj.timesheet_enabled}")
        
        # Simuliere Formular-Daten
        form_data = {'timesheet_enabled': 'on'}  # Checkbox angehakt
        timesheet_enabled = form_data.get('timesheet_enabled') == 'on'
        print(f"  - Formular timesheet_enabled (checkbox angehakt): {timesheet_enabled}")
        
        form_data = {}  # Checkbox nicht angehakt
        timesheet_enabled = form_data.get('timesheet_enabled') == 'on'
        print(f"  - Formular timesheet_enabled (checkbox nicht angehakt): {timesheet_enabled}")
        
        print()
    
    # Teste die automatische Korrektur
    print("=== TESTE AUTOMATISCHE KORREKTUR ===")
    
    # Teste Admin
    admin_user = mongodb.find_one('users', {'username': 'Admin'})
    if admin_user:
        print(f"Admin vor Korrektur: {admin_user.get('timesheet_enabled')}")
        
        # Erstelle User-Objekt (sollte automatisch korrigieren)
        admin_obj = User(admin_user)
        print(f"Admin nach User-Objekt Erstellung: {admin_obj.timesheet_enabled}")
        
        # Prüfe Datenbank
        updated_admin = mongodb.find_one('users', {'username': 'Admin'})
        print(f"Admin in DB nach Korrektur: {updated_admin.get('timesheet_enabled')}")
    
    print()
    
    # Teste nicht-Admin Benutzer
    test_user = mongodb.find_one('users', {'username': 'Test'})
    if test_user:
        print(f"Test-Benutzer vor Korrektur: {test_user.get('timesheet_enabled')}")
        
        # Erstelle User-Objekt
        test_obj = User(test_user)
        print(f"Test-Benutzer nach User-Objekt Erstellung: {test_obj.timesheet_enabled}")
        
        # Prüfe Datenbank
        updated_test = mongodb.find_one('users', {'username': 'Test'})
        print(f"Test-Benutzer in DB nach Korrektur: {updated_test.get('timesheet_enabled')}")
    
    print()
    
    # Teste hypothetischen alten Benutzer ohne timesheet_enabled Feld
    print("=== TESTE HYPOTHETISCHEN ALTEN BENUTZER ===")
    # Erstelle temporären Test-Benutzer ohne timesheet_enabled
    old_user_data = {
        '_id': 'test_old_user',
        'username': 'OldUser',
        'role': 'mitarbeiter',
        'is_active': True
        # Kein timesheet_enabled Feld!
    }
    
    old_user_obj = User(old_user_data)
    print(f"Hypothetischer alter Benutzer (Mitarbeiter): {old_user_obj.timesheet_enabled}")
    
    old_admin_data = {
        '_id': 'test_old_admin',
        'username': 'OldAdmin',
        'role': 'admin',
        'is_active': True
        # Kein timesheet_enabled Feld!
    }
    
    old_admin_obj = User(old_admin_data)
    print(f"Hypothetischer alter Admin: {old_admin_obj.timesheet_enabled}")

if __name__ == "__main__":
    debug_timesheet_enabled() 