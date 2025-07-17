"""
Admin Backup Service

Dieser Service enthält alle Funktionen für die Backup-Verwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from app.models.mongodb_database import mongodb
from app.utils.backup_manager import backup_manager

logger = logging.getLogger(__name__)

class AdminBackupService:
    """Service für Admin-Backup-Funktionen"""
    
    @staticmethod
    def get_backup_list() -> List[Dict[str, Any]]:
        """Hole Liste aller Backups"""
        try:
            backup_dir = backup_manager.backup_dir
            backups = []
            
            if backup_dir.exists():
                for backup_file in backup_dir.glob('*.json'):
                    if backup_file.is_file():
                        stat = backup_file.stat()
                        backups.append({
                            'name': backup_file.name,
                            'size': stat.st_size,
                            'created': stat.st_mtime,
                            'filename': backup_file.name,
                            'size_mb': round(stat.st_size / (1024 * 1024), 2),
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'modified_str': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                        })
            
            # Sortiere nach Änderungsdatum (neueste zuerst)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Liste: {str(e)}")
            return []

    @staticmethod
    def create_backup() -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein neues Backup
        
        Returns:
            (success, message, backup_filename)
        """
        try:
            backup_filename = backup_manager.create_backup()
            
            if backup_filename:
                logger.info(f"Backup erstellt: {backup_filename}")
                return True, f"Backup '{backup_filename}' erfolgreich erstellt", backup_filename
            else:
                return False, "Fehler beim Erstellen des Backups", None
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
            return False, f"Fehler beim Erstellen des Backups: {str(e)}", None

    @staticmethod
    def upload_backup(file) -> Tuple[bool, str]:
        """
        Lädt ein Backup hoch und stellt es wieder her
        
        Args:
            file: Die hochgeladene Backup-Datei
            
        Returns:
            (success, message)
        """
        try:
            if not file:
                return False, "Keine Datei ausgewählt"
            
            if file.filename == '':
                return False, "Keine Datei ausgewählt"
            
            # Prüfe Dateityp
            if not file.filename.endswith('.json'):
                return False, "Ungültiger Dateityp. Bitte eine .json-Datei hochladen."
            
            # Prüfe Dateigröße
            file.seek(0, 2)  # Gehe zum Ende der Datei
            file_size = file.tell()
            file.seek(0)  # Zurück zum Anfang
            
            if file_size == 0:
                return False, "Die hochgeladene Datei ist leer. Bitte wählen Sie eine gültige Backup-Datei aus."
            
            logger.info(f"Backup-Upload: Datei {file.filename}, Größe: {file_size} bytes")
            
            # Erstelle Backup der aktuellen DB vor dem Upload
            current_backup = backup_manager.create_backup()
            logger.info(f"Backup-Upload: Aktuelles Backup erstellt: {current_backup}")
            
            # Stelle das hochgeladene Backup wieder her
            success = backup_manager.restore_backup(file)
            
            if success:
                logger.info(f"Backup erfolgreich hochgeladen und aktiviert: {file.filename}")
                return True, f"Backup '{file.filename}' erfolgreich hochgeladen und aktiviert"
            else:
                return False, "Fehler beim Wiederherstellen des Backups"
                
        except Exception as e:
            logger.error(f"Fehler beim Upload des Backups: {str(e)}")
            return False, f"Fehler beim Upload des Backups: {str(e)}"

    @staticmethod
    def restore_backup(filename: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Stellt ein Backup wieder her
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message, validation_info)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden", None
            
            # Erstelle Backup der aktuellen DB vor der Wiederherstellung
            current_backup = backup_manager.create_backup()
            logger.info(f"Backup-Wiederherstellung: Aktuelles Backup erstellt: {current_backup}")
            
            # Stelle das Backup wieder her
            success = backup_manager.restore_backup_by_filename(filename)
            
            if success:
                # Korrigiere fehlende created_at Felder
                fixed_count = AdminBackupService._fix_missing_created_at_fields()
                
                # Validiere das wiederhergestellte Backup
                validation_info = {
                    'filename': filename,
                    'restored_at': datetime.now(),
                    'previous_backup': current_backup,
                    'collections_restored': ['tools', 'workers', 'consumables', 'users', 'lendings', 'tickets', 'settings'],
                    'fixed_created_at_fields': fixed_count
                }
                
                logger.info(f"Backup erfolgreich wiederhergestellt: {filename} (erganzte Felder: {fixed_count})")
                return True, f"Backup '{filename}' erfolgreich wiederhergestellt", validation_info
            else:
                return False, "Fehler beim Wiederherstellen des Backups", None
                
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Wiederherstellen des Backups: {str(e)}", None

    @staticmethod
    def download_backup(filename: str) -> Tuple[bool, str, Optional[bytes]]:
        """
        Lädt ein Backup zum Download herunter
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message, file_content)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden", None
            
            # Datei lesen
            with open(backup_path, 'rb') as f:
                file_content = f.read()
            
            logger.info(f"Backup zum Download bereitgestellt: {filename}")
            return True, f"Backup '{filename}' zum Download bereit", file_content
            
        except Exception as e:
            logger.error(f"Fehler beim Download des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Download des Backups: {str(e)}", None

    @staticmethod
    def delete_backup(filename: str) -> Tuple[bool, str]:
        """
        Löscht ein Backup
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden"
            
            # Datei löschen
            backup_path.unlink()
            
            logger.info(f"Backup gelöscht: {filename}")
            return True, f"Backup '{filename}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Löschen des Backups: {str(e)}"

    @staticmethod
    def get_backup_statistics() -> Dict[str, Any]:
        """Hole Backup-Statistiken"""
        try:
            backups = AdminBackupService.get_backup_list()
            
            total_size_mb = sum(b['size_mb'] for b in backups)
            oldest_backup = min(backups, key=lambda x: x['modified']) if backups else None
            newest_backup = max(backups, key=lambda x: x['modified']) if backups else None
            
            return {
                'total_backups': len(backups),
                'total_size_mb': total_size_mb,
                'oldest_backup': oldest_backup['modified'] if oldest_backup else None,
                'newest_backup': newest_backup['modified'] if newest_backup else None,
                'average_size_mb': round(total_size_mb / len(backups), 2) if backups else 0
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Statistiken: {str(e)}")
            return {
                'total_backups': 0,
                'total_size_mb': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'average_size_mb': 0
            }

    @staticmethod
    def get_backup_path(filename: str) -> Path:
        """
        Gibt den Pfad zu einer Backup-Datei zurück
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            Path-Objekt zur Backup-Datei
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            return backup_path
            
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln des Backup-Pfads für {filename}: {str(e)}")
            return Path()

    @staticmethod
    def test_backup(filename: str) -> Tuple[bool, str]:
        """
        Testet ein Backup ohne es wiederherzustellen
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden"
            
            # Backup-Datei lesen und validieren
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Prüfe Struktur
            required_collections = ['tools', 'workers', 'consumables', 'users']
            missing_collections = []
            
            for collection in required_collections:
                if collection not in backup_data:
                    missing_collections.append(collection)
            
            if missing_collections:
                return False, f"Backup ist unvollständig. Fehlende Collections: {', '.join(missing_collections)}"
            
            # Statistiken berechnen
            total_documents = sum(len(documents) for documents in backup_data.values())
            
            logger.info(f"Backup getestet: {filename} - {total_documents} Dokumente in {len(backup_data)} Collections")
            return True, f"Backup '{filename}' ist gültig ({total_documents} Dokumente in {len(backup_data)} Collections)"
            
        except json.JSONDecodeError as e:
            logger.error(f"Backup {filename} ist kein gültiges JSON: {str(e)}")
            return False, f"Backup '{filename}' ist kein gültiges JSON-Format"
        except Exception as e:
            logger.error(f"Fehler beim Testen des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Testen des Backups: {str(e)}" 

    @staticmethod
    def _fix_missing_created_at_fields():
        """
        Ergänzt fehlende created_at Felder und andere Standardfelder in Tools und anderen Collections
        """
        try:
            from datetime import datetime
            
            fixed_count = 0
            
            # Tools ohne created_at Feld finden und ergänzen
            tools_without_created_at = mongodb.find('tools', {
                'created_at': {'$exists': False}
            })
            
            for tool in tools_without_created_at:
                # Verwende updated_at als created_at, falls vorhanden
                created_at = tool.get('updated_at') or tool.get('modified_at') or datetime.now()
                
                # Konvertiere String zu datetime falls nötig
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                created_at = datetime.strptime(created_at, '%Y-%m-%d')
                            except ValueError:
                                created_at = datetime.now()
                
                # Ergänze created_at Feld
                mongodb.update_one('tools', 
                                 {'_id': tool['_id']}, 
                                 {'$set': {'created_at': created_at}})
                fixed_count += 1
            
            # Workers ohne created_at Feld finden und ergänzen
            workers_without_created_at = mongodb.find('workers', {
                'created_at': {'$exists': False}
            })
            
            for worker in workers_without_created_at:
                created_at = worker.get('updated_at') or worker.get('modified_at') or datetime.now()
                
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                created_at = datetime.strptime(created_at, '%Y-%m-%d')
                            except ValueError:
                                created_at = datetime.now()
                
                mongodb.update_one('workers', 
                                 {'_id': worker['_id']}, 
                                 {'$set': {'created_at': created_at}})
                fixed_count += 1
            
            # Consumables ohne created_at Feld finden und ergänzen
            consumables_without_created_at = mongodb.find('consumables', {
                'created_at': {'$exists': False}
            })
            
            for consumable in consumables_without_created_at:
                created_at = consumable.get('updated_at') or datetime.now()
                
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                created_at = datetime.strptime(created_at, '%Y-%m-%d')
                            except ValueError:
                                created_at = datetime.now()
                
                # Ergänze created_at und unit Feld falls fehlend
                update_data = {'created_at': created_at}
                
                # Ergänze unit Feld falls nicht vorhanden
                if 'unit' not in consumable:
                    update_data['unit'] = 'Stück'
                
                mongodb.update_one('consumables', 
                                 {'_id': consumable['_id']}, 
                                 {'$set': update_data})
                fixed_count += 1
            
            # Ergänze unit Feld für alle Consumables die es nicht haben
            consumables_without_unit = mongodb.find('consumables', {
                'unit': {'$exists': False}
            })
            
            for consumable in consumables_without_unit:
                mongodb.update_one('consumables', 
                                 {'_id': consumable['_id']}, 
                                 {'$set': {'unit': 'Stück'}})
                fixed_count += 1
            
            # Ergänze sync_status Feld für alle Collections falls fehlend
            collections_to_check = ['tools', 'workers', 'consumables']
            for collection in collections_to_check:
                docs_without_sync = mongodb.find(collection, {
                    'sync_status': {'$exists': False}
                })
                
                for doc in docs_without_sync:
                    mongodb.update_one(collection, 
                                     {'_id': doc['_id']}, 
                                     {'$set': {'sync_status': 'synced'}})
                    fixed_count += 1
            
            # Ergänze deleted_at Feld für alle Collections falls fehlend (für Soft-Delete)
            for collection in collections_to_check:
                docs_without_deleted_at = mongodb.find(collection, {
                    'deleted': True,
                    'deleted_at': {'$exists': False}
                })
                
                for doc in docs_without_deleted_at:
                    deleted_at = doc.get('updated_at') or datetime.now()
                    
                    if isinstance(deleted_at, str):
                        try:
                            deleted_at = datetime.strptime(deleted_at, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                deleted_at = datetime.strptime(deleted_at, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                try:
                                    deleted_at = datetime.strptime(deleted_at, '%Y-%m-%d')
                                except ValueError:
                                    deleted_at = datetime.now()
                    
                    mongodb.update_one(collection, 
                                     {'_id': doc['_id']}, 
                                     {'$set': {'deleted_at': deleted_at}})
                    fixed_count += 1
            
            if fixed_count > 0:
                logger.info(f"Fehlende Felder ergänzt: {fixed_count} Dokumente")
            
            return fixed_count
            
        except Exception as e:
            logger.error(f"Fehler beim Ergänzen fehlender Felder: {str(e)}")
            return 0 