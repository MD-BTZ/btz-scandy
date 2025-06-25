#!/usr/bin/env python3
"""
Skript zur Behebung aller Datenbankinkonsistenzen in der Scandy-Anwendung
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from bson import ObjectId
from datetime import datetime

def fix_all_inconsistencies():
    """Behebt alle gefundenen Datenbankinkonsistenzen"""
    try:
        print("=== Behebe alle Datenbankinkonsistenzen ===\n")
        
        # 1. Kategorien-Inkonsistenz beheben
        print("1. Behebe Kategorien-Inkonsistenz...")
        fix_category_inconsistency()
        
        # 2. Notice-Feld-Inkonsistenzen beheben
        print("\n2. Behebe Notice-Feld-Inkonsistenzen...")
        fix_notice_field_inconsistencies()
        
        # 3. Fehlende Indizes erstellen
        print("\n3. Erstelle fehlende Indizes...")
        create_missing_indexes()
        
        # 4. Datenbank-Validierung
        print("\n4. Validiere Datenbankintegrität...")
        validate_database_integrity()
        
        print("\n=== Alle Inkonsistenzen behoben! ===")
        
    except Exception as e:
        print(f"✗ Fehler beim Beheben der Inkonsistenzen: {e}")
        import traceback
        traceback.print_exc()

def fix_category_inconsistency():
    """Behebt Inkonsistenzen zwischen Kategorien in den Settings und den tatsächlich verwendeten Kategorien"""
    try:
        # Sammle alle verwendeten Kategorien aus den Daten
        used_categories = set()
        used_locations = set()
        used_departments = set()
        
        # Aus Werkzeugen
        tools = list(mongodb.find('tools', {}))
        for tool in tools:
            if tool.get('category'):
                used_categories.add(tool['category'])
            if tool.get('location'):
                used_locations.add(tool['location'])
        
        # Aus Verbrauchsgütern
        consumables = list(mongodb.find('consumables', {}))
        for consumable in consumables:
            if consumable.get('category'):
                used_categories.add(consumable['category'])
            if consumable.get('location'):
                used_locations.add(consumable['location'])
        
        # Aus Mitarbeitern (Abteilungen)
        workers = list(mongodb.find('workers', {}))
        for worker in workers:
            if worker.get('department'):
                used_departments.add(worker['department'])
        
        # Aktualisiere die Settings
        if used_categories:
            categories_list = list(used_categories)
            mongodb.update_one('settings', 
                             {'key': 'categories'}, 
                             {'$set': {'value': categories_list}}, 
                             upsert=True)
            print(f"   ✓ Kategorien aktualisiert: {categories_list}")
        
        if used_locations:
            locations_list = list(used_locations)
            mongodb.update_one('settings', 
                             {'key': 'locations'}, 
                             {'$set': {'value': locations_list}}, 
                             upsert=True)
            print(f"   ✓ Standorte aktualisiert: {locations_list}")
        
        if used_departments:
            departments_list = list(used_departments)
            mongodb.update_one('settings', 
                             {'key': 'departments'}, 
                             {'$set': {'value': departments_list}}, 
                             upsert=True)
            print(f"   ✓ Abteilungen aktualisiert: {departments_list}")
            
    except Exception as e:
        print(f"   ✗ Fehler bei Kategorien-Inkonsistenz: {e}")

def fix_notice_field_inconsistencies():
    """Behebt Inkonsistenzen bei den Notice-Feldern"""
    try:
        # Finde alle Notices mit inkonsistenten Feldern
        notices = list(mongodb.find('homepage_notices', {}))
        
        for notice in notices:
            updates = {}
            
            # Korrigiere 'active' zu 'is_active'
            if 'active' in notice and 'is_active' not in notice:
                updates['is_active'] = notice['active']
                updates['$unset'] = {'active': 1}
            
            # Füge fehlende 'priority' hinzu
            if 'priority' not in notice:
                updates['priority'] = 1
            
            # Füge fehlende Timestamps hinzu
            if 'created_at' not in notice:
                updates['created_at'] = notice.get('updated_at') or datetime.now()
            if 'updated_at' not in notice:
                updates['updated_at'] = notice.get('created_at') or datetime.now()
            
            # Aktualisiere Notice
            if updates:
                unset_data = updates.pop('$unset', {})
                if unset_data:
                    mongodb.update_one('homepage_notices', 
                                     {'_id': notice['_id']}, 
                                     {'$set': updates, '$unset': unset_data})
                else:
                    mongodb.update_one('homepage_notices', 
                                     {'_id': notice['_id']}, 
                                     {'$set': updates})
        
        print(f"   ✓ {len(notices)} Notices überprüft und korrigiert")
        
    except Exception as e:
        print(f"   ✗ Fehler bei Notice-Feld-Inkonsistenzen: {e}")

def create_missing_indexes():
    """Erstellt fehlende Indizes"""
    try:
        # Homepage Notices Indizes
        try:
            mongodb.create_index('homepage_notices', 'is_active')
        except Exception as e:
            if 'existing index' not in str(e).lower():
                print(f"   ⚠️ Fehler beim Erstellen des is_active Index: {e}")
        
        try:
            mongodb.create_index('homepage_notices', 'priority')
        except Exception as e:
            if 'existing index' not in str(e).lower():
                print(f"   ⚠️ Fehler beim Erstellen des priority Index: {e}")
        
        try:
            mongodb.create_index('homepage_notices', 'created_at')
        except Exception as e:
            if 'existing index' not in str(e).lower():
                print(f"   ⚠️ Fehler beim Erstellen des created_at Index: {e}")
        
        # Settings Indizes
        try:
            mongodb.create_index('settings', 'key', unique=True)
        except Exception as e:
            if 'existing index' not in str(e).lower():
                print(f"   ⚠️ Fehler beim Erstellen des settings key Index: {e}")
        
        # User Indizes
        try:
            mongodb.create_index('users', 'username', unique=True)
        except Exception as e:
            if 'existing index' not in str(e).lower():
                print(f"   ⚠️ Fehler beim Erstellen des username Index: {e}")
        
        try:
            mongodb.create_index('users', 'email')
        except Exception as e:
            if 'existing index' not in str(e).lower():
                print(f"   ⚠️ Fehler beim Erstellen des email Index: {e}")
        
        print("   ✓ Indizes überprüft (bestehende Indizes übersprungen)")
        
    except Exception as e:
        print(f"   ✗ Fehler beim Erstellen der Indizes: {e}")

def validate_database_integrity():
    """Validiert die Datenbankintegrität"""
    try:
        issues = []
        
        # Prüfe auf doppelte Benutzernamen
        users = list(mongodb.find('users', {}))
        usernames = [user.get('username') for user in users if user.get('username')]
        if len(usernames) != len(set(usernames)):
            issues.append("Doppelte Benutzernamen gefunden")
        
        # Prüfe auf doppelte Barcodes
        tools = list(mongodb.find('tools', {}))
        tool_barcodes = [tool.get('barcode') for tool in tools if tool.get('barcode')]
        if len(tool_barcodes) != len(set(tool_barcodes)):
            issues.append("Doppelte Werkzeug-Barcodes gefunden")
        
        workers = list(mongodb.find('workers', {}))
        worker_barcodes = [worker.get('barcode') for worker in workers if worker.get('barcode')]
        if len(worker_barcodes) != len(set(worker_barcodes)):
            issues.append("Doppelte Mitarbeiter-Barcodes gefunden")
        
        consumables = list(mongodb.find('consumables', {}))
        consumable_barcodes = [consumable.get('barcode') for consumable in consumables if consumable.get('barcode')]
        if len(consumable_barcodes) != len(set(consumable_barcodes)):
            issues.append("Doppelte Verbrauchsmaterial-Barcodes gefunden")
        
        if issues:
            print(f"   ⚠️ Gefundene Probleme: {', '.join(issues)}")
        else:
            print("   ✓ Keine Integritätsprobleme gefunden")
            
    except Exception as e:
        print(f"   ✗ Fehler bei der Datenbankvalidierung: {e}")

if __name__ == '__main__':
    fix_all_inconsistencies() 