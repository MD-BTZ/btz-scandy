import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from app.models.mongodb_database import mongodb

class BackupManager:
    """Vollständiger Backup-Manager für MongoDB"""
    
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent.parent / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
    
    def _fix_id_for_restore(self, doc):
        """
        Wandelt das _id-Feld in einen echten ObjectId um, wenn möglich.
        Wichtig für Backup-Wiederherstellung, da JSON-Export IDs als String speichert.
        """
        if '_id' in doc:
            # Falls _id ein String ist und wie eine ObjectId aussieht
            if isinstance(doc['_id'], str) and len(doc['_id']) == 24:
                try:
                    doc['_id'] = ObjectId(doc['_id'])
                except Exception:
                    # Falls es keine gültige ObjectId ist, entferne das Feld
                    # MongoDB wird automatisch eine neue ObjectId generieren
                    del doc['_id']
            # Falls _id bereits eine ObjectId ist, belasse es
            elif isinstance(doc['_id'], ObjectId):
                pass
            # Falls _id ein anderer Typ ist, entferne es
            else:
                del doc['_id']
        return doc
    
    def _validate_backup_data(self, backup_data):
        """
        Validiert Backup-Daten vor der Wiederherstellung
        """
        if not isinstance(backup_data, dict):
            return False, "Backup-Daten sind kein gültiges Dictionary"
        
        required_collections = ['tools', 'workers', 'consumables', 'settings']
        missing_collections = [coll for coll in required_collections if coll not in backup_data]
        
        if missing_collections:
            return False, f"Fehlende Collections im Backup: {missing_collections}"
        
        total_docs = sum(len(docs) for docs in backup_data.values())
        if total_docs == 0:
            return False, "Backup enthält keine Dokumente"
        
        return True, f"Backup ist gültig mit {total_docs} Dokumenten in {len(backup_data)} Collections"
        
    def create_backup(self):
        """Erstellt ein Backup aller Collections"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"scandy_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            # Alle Collections sichern
            collections_to_backup = [
                'tools', 'workers', 'consumables', 'lendings', 'consumable_usages', 
                'settings', 'tickets', 'timesheets', 'users', 'auftrag_details', 
                'auftrag_material', 'email_config', 'email_settings', 'system_logs'
            ]
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
            
            print(f"Backup erstellt: {backup_filename} mit {sum(len(docs) for docs in backup_data.values())} Dokumenten")
            
            # Alte Backups aufräumen
            self._cleanup_old_backups()
            
            return backup_filename
            
        except Exception as e:
            print(f"Fehler beim Erstellen des Backups: {e}")
            return None
    
    def restore_backup(self, file):
        """Stellt ein Backup aus einer hochgeladenen Datei wieder her"""
        temp_path = None
        try:
            # Prüfe ob die Datei leer ist
            file.seek(0, 2)  # Gehe zum Ende der Datei
            file_size = file.tell()
            file.seek(0)  # Zurück zum Anfang
            
            if file_size == 0:
                print("Fehler: Hochgeladene Datei ist leer")
                return False
            
            # Temporäre Datei speichern
            temp_path = self.backup_dir / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file.save(temp_path)
            
            # Prüfe ob die Datei erfolgreich gespeichert wurde
            if not temp_path.exists():
                print("Fehler: Temporäre Datei konnte nicht gespeichert werden")
                return False
            
            # Prüfe Dateigröße nochmal
            actual_file_size = temp_path.stat().st_size
            if actual_file_size == 0:
                print("Fehler: Gespeicherte Datei ist leer")
                temp_path.unlink()
                return False
            
            print(f"Temporäre Datei gespeichert: {temp_path}, Größe: {actual_file_size} bytes")
            
            # Backup wiederherstellen
            success = self._restore_from_file(temp_path)
            
            return success
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des Backups: {e}")
            return False
        finally:
            # Temporäre Datei löschen
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    print(f"Fehler beim Löschen der temporären Datei: {e}")
    
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
            # Prüfe Dateigröße
            file_size = backup_path.stat().st_size
            if file_size == 0:
                print("Fehler: Backup-Datei ist leer")
                return False
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Backup-Daten validieren
            is_valid, validation_message = self._validate_backup_data(backup_data)
            if not is_valid:
                print(f"Backup-Validierung fehlgeschlagen: {validation_message}")
                return False
            
            print(f"Backup-Validierung erfolgreich: {validation_message}")
            
            # Collections wiederherstellen
            for collection, documents in backup_data.items():
                try:
                    # Collection leeren
                    mongodb.db[collection].delete_many({})
                    
                    # Dokumente wiederherstellen mit ID-Korrektur
                    if documents:
                        # IDs für alle Dokumente korrigieren
                        fixed_documents = []
                        for doc in documents:
                            fixed_doc = self._fix_id_for_restore(doc)
                            fixed_documents.append(fixed_doc)
                        
                        # Dokumente in die Datenbank einfügen
                        mongodb.db[collection].insert_many(fixed_documents)
                        print(f"Collection {collection}: {len(fixed_documents)} Dokumente wiederhergestellt")
                        
                except Exception as e:
                    print(f"Fehler beim Wiederherstellen von {collection}: {e}")
                    # Bei Fehler: Versuche ohne ID-Korrektur
                    try:
                        mongodb.db[collection].insert_many(documents)
                        print(f"Collection {collection}: {len(documents)} Dokumente ohne ID-Korrektur wiederhergestellt")
                    except Exception as e2:
                        print(f"Kritischer Fehler bei {collection}: {e2}")
            
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
    
    def test_backup(self, filename):
        """
        Testet ein Backup ohne es wiederherzustellen.
        Gibt Informationen über das Backup zurück.
        """
        try:
            backup_path = self.backup_dir / filename
            if not backup_path.exists():
                return False, "Backup-Datei nicht gefunden"
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Backup validieren
            is_valid, validation_message = self._validate_backup_data(backup_data)
            
            if not is_valid:
                return False, validation_message
            
            # Detaillierte Informationen sammeln
            collection_info = {}
            for collection, documents in backup_data.items():
                collection_info[collection] = {
                    'count': len(documents),
                    'sample_ids': [str(doc.get('_id', 'N/A'))[:10] + '...' for doc in documents[:3]]
                }
            
            return True, {
                'validation_message': validation_message,
                'collections': collection_info,
                'file_size': backup_path.stat().st_size,
                'file_modified': datetime.fromtimestamp(backup_path.stat().st_mtime)
            }
            
        except Exception as e:
            return False, f"Fehler beim Testen des Backups: {str(e)}"
    
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