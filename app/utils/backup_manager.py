import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime
from app.models.mongodb_database import mongodb

class BackupManager:
    """Vollständiger Backup-Manager für MongoDB"""
    
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent.parent / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self):
        """Erstellt ein Backup aller Collections"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"scandy_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            # Alle Collections sichern
            collections_to_backup = ['tools', 'workers', 'consumables', 'lendings', 'consumable_usages', 'settings', 'tickets', 'ticket_messages', 'ticket_notes']
            backup_data = {}
            
            for collection in collections_to_backup:
                try:
                    documents = list(mongodb.find(collection, {}))
                    backup_data[collection] = documents
                except Exception as e:
                    print(f"Fehler beim Sichern von {collection}: {e}")
                    backup_data[collection] = []
            
            # Backup-Datei speichern
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
            # Alte Backups aufräumen
            self._cleanup_old_backups()
            
            return backup_filename
            
        except Exception as e:
            print(f"Fehler beim Erstellen des Backups: {e}")
            return None
    
    def restore_backup(self, file):
        """Stellt ein Backup aus einer hochgeladenen Datei wieder her"""
        try:
            # Temporäre Datei speichern
            temp_path = self.backup_dir / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file.save(temp_path)
            
            # Backup wiederherstellen
            success = self._restore_from_file(temp_path)
            
            # Temporäre Datei löschen
            if temp_path.exists():
                temp_path.unlink()
            
            return success
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des Backups: {e}")
            return False
    
    def restore_backup_by_filename(self, filename):
        """Stellt ein Backup anhand des Dateinamens wieder her"""
        try:
            backup_path = self.backup_dir / filename
            if not backup_path.exists():
                print(f"Backup-Datei nicht gefunden: {filename}")
                return False
            
            return self._restore_from_file(backup_path)
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des Backups: {e}")
            return False
    
    def _restore_from_file(self, backup_path):
        """Stellt ein Backup aus einer Datei wieder her"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Collections wiederherstellen
            for collection, documents in backup_data.items():
                try:
                    # Collection leeren
                    mongodb.db[collection].delete_many({})
                    
                    # Dokumente wiederherstellen
                    if documents:
                        mongodb.db[collection].insert_many(documents)
                        
                except Exception as e:
                    print(f"Fehler beim Wiederherstellen von {collection}: {e}")
            
            # Nach der Wiederherstellung: Kategorien-Inkonsistenz beheben
            self._fix_category_inconsistency()
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen aus Datei: {e}")
            return False
    
    def _fix_category_inconsistency(self):
        """Behebt Inkonsistenzen zwischen Kategorien in den Settings und den tatsächlich verwendeten Kategorien"""
        try:
            print("Behebe Kategorien-Inkonsistenz...")
            
            # Sammle alle verwendeten Kategorien aus den Daten
            used_categories = set()
            
            # Aus Werkzeugen
            tools = list(mongodb.find('tools', {}))
            for tool in tools:
                if tool.get('category'):
                    used_categories.add(tool['category'])
            
            # Aus Verbrauchsgütern
            consumables = list(mongodb.find('consumables', {}))
            for consumable in consumables:
                if consumable.get('category'):
                    used_categories.add(consumable['category'])
            
            # Aus Mitarbeitern (Abteilungen)
            workers = list(mongodb.find('workers', {}))
            for worker in workers:
                if worker.get('department'):
                    used_categories.add(worker['department'])
            
            # Aktualisiere die Settings mit allen verwendeten Kategorien
            if used_categories:
                categories_list = list(used_categories)
                mongodb.update_one('settings', 
                                 {'key': 'categories'}, 
                                 {'$set': {'value': categories_list}}, 
                                 upsert=True)
                print(f"Kategorien aktualisiert: {categories_list}")
            
            # Sammle alle verwendeten Standorte
            used_locations = set()
            for tool in tools:
                if tool.get('location'):
                    used_locations.add(tool['location'])
            for consumable in consumables:
                if consumable.get('location'):
                    used_locations.add(consumable['location'])
            
            # Aktualisiere die Standorte-Settings
            if used_locations:
                locations_list = list(used_locations)
                mongodb.update_one('settings', 
                                 {'key': 'locations'}, 
                                 {'$set': {'value': locations_list}}, 
                                 upsert=True)
                print(f"Standorte aktualisiert: {locations_list}")
            
            # Sammle alle verwendeten Abteilungen
            used_departments = set()
            for worker in workers:
                if worker.get('department'):
                    used_departments.add(worker['department'])
            
            # Aktualisiere die Abteilungen-Settings
            if used_departments:
                departments_list = list(used_departments)
                mongodb.update_one('settings', 
                                 {'key': 'departments'}, 
                                 {'$set': {'value': departments_list}}, 
                                 upsert=True)
                print(f"Abteilungen aktualisiert: {departments_list}")
            
            print("Kategorien-Inkonsistenz behoben!")
            
        except Exception as e:
            print(f"Fehler beim Beheben der Kategorien-Inkonsistenz: {e}")
    
    def get_backup_path(self, filename):
        """Gibt den Pfad zu einer Backup-Datei zurück"""
        return self.backup_dir / filename
    
    def delete_backup(self, filename):
        """Löscht eine Backup-Datei"""
        try:
            backup_path = self.backup_dir / filename
            if backup_path.exists():
                backup_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Fehler beim Löschen des Backups: {e}")
            return False
    
    def _cleanup_old_backups(self, keep=10):
        """Löscht alte Backups, behält nur die letzten 'keep'"""
        try:
            # Finde alle Backup-Dateien
            backup_files = list(self.backup_dir.glob('scandy_backup_*.json'))
            
            if len(backup_files) > keep:
                # Sortiere nach Änderungsdatum
                backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                
                # Lösche alte Backups
                for old_backup in backup_files[keep:]:
                    old_backup.unlink()
                    print(f"Altes Backup gelöscht: {old_backup.name}")
                    
        except Exception as e:
            print(f"Fehler beim Aufräumen alter Backups: {e}")

# Globale Instanz
backup_manager = BackupManager() 