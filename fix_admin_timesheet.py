#!/usr/bin/env python3
"""
Script um den Admin-Benutzer timesheet_enabled zu korrigieren
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from bson import ObjectId

def fix_admin_timesheet():
    print("=== FIX: Admin timesheet_enabled ===\n")
    
    # Finde Admin-Benutzer
    admin_user = mongodb.find_one('users', {'username': 'Admin'})
    
    if not admin_user:
        print("Admin-Benutzer nicht gefunden!")
        return
    
    print(f"Admin-Benutzer gefunden: {admin_user['username']}")
    print(f"Aktueller timesheet_enabled Wert: {admin_user.get('timesheet_enabled', 'FELD NICHT VORHANDEN')}")
    
    # Setze timesheet_enabled auf True
    result = mongodb.update_one('users', 
                               {'_id': admin_user['_id']}, 
                               {'$set': {'timesheet_enabled': True}})
    
    if result:
        print("✅ Admin timesheet_enabled erfolgreich auf True gesetzt")
        
        # Prüfe das Ergebnis
        updated_admin = mongodb.find_one('users', {'username': 'Admin'})
        print(f"Neuer timesheet_enabled Wert: {updated_admin.get('timesheet_enabled')}")
    else:
        print("❌ Fehler beim Aktualisieren des Admin-Benutzers")

if __name__ == "__main__":
    fix_admin_timesheet() 