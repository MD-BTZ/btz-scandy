"""
Zentraler Backup Service für Scandy
Alle Backup-Funktionalitäten an einem Ort
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import json
import os
import zipfile
import tempfile
from pathlib import Path
from app.models.mongodb_database import mongodb
from app.utils.backup_manager import BackupManager
import logging

logger = logging.getLogger(__name__)

class BackupService:
    """Zentraler Service für alle Backup-Operationen"""
    
    def __init__(self):
        self.backup_manager = BackupManager()
    
    def create_backup(self, include_files: bool = True) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein vollständiges Backup der Anwendung
        
        Args:
            include_files: Ob Dateien mit einbezogen werden sollen
            
        Returns:
            Tuple: (success, message, backup_path)
        """
        try:
            # Erstelle Backup-Verzeichnis
            backup_dir = Path("backups")
            backup_dir.mkdir(exist_ok=True)
            
            # Zeitstempel für Backup-Namen
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"scandy_backup_{timestamp}"
            backup_path = backup_dir / f"{backup_name}.json"
            
            # Datenbank-Backup erstellen
            backup_data = self._create_database_backup()
            
            # Backup-Datei speichern
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
            
            # Dateien hinzufügen falls gewünscht
            if include_files:
                zip_path = backup_dir / f"{backup_name}.zip"
                self._create_backup_archive(backup_path, zip_path)
                backup_path = zip_path
            
            logger.info(f"Backup erfolgreich erstellt: {backup_path}")
            return True, f"Backup erfolgreich erstellt: {backup_path.name}", str(backup_path)
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
            return False, f"Fehler beim Erstellen des Backups: {str(e)}", None
    
    def _create_database_backup(self) -> Dict[str, Any]:
        """Erstellt ein Backup aller Datenbank-Collections"""
        try:
            backup_data = {
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'version': '1.0',
                    'collections': []
                },
                'data': {}
            }
            
            # Collections die gesichert werden sollen
            collections = [
                'tools', 'workers', 'consumables', 'lendings', 
                'consumable_usages', 'tickets', 'users', 'settings',
                'homepage_notices', 'work_times'
            ]
            
            for collection_name in collections:
                try:
                    # Alle Dokumente aus der Collection laden
                    documents = list(mongodb.find(collection_name, {}))
                    
                    # Dokumente für Backup vorbereiten
                    backup_documents = []
                    for doc in documents:
                        # ObjectId zu String konvertieren
                        if '_id' in doc:
                            doc['_id'] = str(doc['_id'])
                        backup_documents.append(doc)
                    
                    backup_data['data'][collection_name] = backup_documents
                    backup_data['metadata']['collections'].append({
                        'name': collection_name,
                        'count': len(backup_documents)
                    })
                    
                    logger.info(f"Collection {collection_name}: {len(backup_documents)} Dokumente gesichert")
                    
                except Exception as e:
                    logger.error(f"Fehler beim Sichern der Collection {collection_name}: {str(e)}")
                    backup_data['data'][collection_name] = []
            
            return backup_data
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Datenbank-Backups: {str(e)}")
            raise
    
    def _create_backup_archive(self, json_path: Path, zip_path: Path) -> None:
        """Erstellt ein ZIP-Archiv mit Backup-Daten und Dateien"""
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # JSON-Backup hinzufügen
                zipf.write(json_path, json_path.name)
                
                # Uploads-Verzeichnis hinzufügen
                uploads_dir = Path("app/static/uploads")
                if uploads_dir.exists():
                    for file_path in uploads_dir.rglob("*"):
                        if file_path.is_file():
                            # Relativen Pfad im ZIP verwenden
                            arcname = f"uploads/{file_path.relative_to(uploads_dir)}"
                            zipf.write(file_path, arcname)
                
                # Logs-Verzeichnis hinzufügen (nur die letzten 10 Dateien)
                logs_dir = Path("logs")
                if logs_dir.exists():
                    log_files = sorted(logs_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
                    for log_file in log_files:
                        arcname = f"logs/{log_file.name}"
                        zipf.write(log_file, arcname)
            
            # JSON-Datei löschen da sie jetzt im ZIP ist
            json_path.unlink()
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backup-Archivs: {str(e)}")
            raise
    
    def restore_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Stellt ein Backup wieder her
        
        Args:
            backup_path: Pfad zur Backup-Datei
            
        Returns:
            Tuple: (success, message)
        """
        try:
            # Prüfe ob es eine ZIP-Datei ist
            if backup_path.endswith('.zip'):
                return self._restore_from_archive(backup_path)
            else:
                return self._restore_from_json(backup_path)
                
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen des Backups: {str(e)}")
            return False, f"Fehler beim Wiederherstellen: {str(e)}"
    
    def _restore_from_archive(self, zip_path: str) -> Tuple[bool, str]:
        """Stellt ein Backup aus einem ZIP-Archiv wieder her"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # JSON-Backup extrahieren
                json_files = [f for f in zipf.namelist() if f.endswith('.json')]
                if not json_files:
                    return False, "Keine JSON-Backup-Datei im Archiv gefunden"
                
                # JSON-Datei extrahieren
                json_filename = json_files[0]
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as tmp_file:
                    tmp_file.write(zipf.read(json_filename))
                    tmp_path = tmp_file.name
                
                try:
                    # Backup wiederherstellen
                    success, message = self._restore_from_json(tmp_path)
                    
                    # Dateien wiederherstellen falls Backup erfolgreich war
                    if success:
                        self._restore_files_from_archive(zipf)
                    
                    return success, message
                    
                finally:
                    # Temporäre Datei löschen
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen aus Archiv: {str(e)}")
            return False, f"Fehler beim Wiederherstellen aus Archiv: {str(e)}"
    
    def _restore_from_json(self, json_path: str) -> Tuple[bool, str]:
        """Stellt ein Backup aus einer JSON-Datei wieder her mit erweiterter Unterstützung für alte Formate"""
        try:
            # Backup-Daten laden
            with open(json_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # ERWEITERTE Backup-Format-Erkennung (ohne rekursive Aufrufe)
            if 'data' in backup_data:
                # Neues Format mit Metadata
                has_metadata = True
                has_datatype_preservation = backup_data.get('metadata', {}).get('datatype_preservation', False)
                data_section = backup_data['data']
                format_type = 'new'
                version_estimate = '2.0+' if has_datatype_preservation else '1.0-1.9'
            else:
                # Altes Format
                has_metadata = False
                has_datatype_preservation = False
                data_section = backup_data
                format_type = 'old'
                
                # Schätze Version basierend auf vorhandenen Collections
                if 'jobs' in data_section:
                    version_estimate = '1.5+'
                elif 'tickets' in data_section:
                    version_estimate = '1.0+'
                else:
                    version_estimate = 'pre-1.0'
            
            format_info = {
                'is_old_format': format_type == 'old',
                'version_estimate': version_estimate,
                'collections_found': list(data_section.keys()) if isinstance(data_section, dict) else [],
                'total_documents': sum(len(docs) for docs in data_section.values() if isinstance(docs, list)) if isinstance(data_section, dict) else 0,
                'has_metadata': has_metadata,
                'has_datatype_preservation': has_datatype_preservation,
                'format_type': format_type
            }
            
            logger.info(f"Backup-Format erkannt: {format_type} ({version_estimate})")
            
            # Backup validieren mit erweiterter Unterstützung
            is_valid, validation_message = self.backup_manager._validate_backup_data(backup_data)
            if not is_valid:
                return False, f"Ungültiges Backup: {validation_message}"
            
            # ERWEITERTE Collections-Liste für verschiedene Backup-Versionen
            collections_to_restore = [
                'tools', 'workers', 'consumables', 'lendings', 
                'consumable_usages', 'tickets', 'users', 'settings',
                'homepage_notices', 'work_times', 'jobs', 'timesheets',
                'auftrag_details', 'auftrag_material', 'email_config', 
                'email_settings', 'system_logs'
            ]
            
            # Bestimme welche Collections im Backup vorhanden sind
            if format_info['has_metadata']:
                data_section = backup_data['data']
            else:
                # Altes Format - verwende direkt
                data_section = backup_data
            
            restore_stats = {
                'total_collections': 0,
                'successful_collections': 0,
                'failed_collections': 0,
                'total_documents': 0
            }
            
            for collection_name in collections_to_restore:
                if collection_name in data_section:
                    restore_stats['total_collections'] += 1
                    
                    try:
                        # Collection leeren
                        mongodb.db[collection_name].delete_many({})
                        
                        # Dokumente wiederherstellen mit erweiterter Konvertierung
                        documents = data_section[collection_name]
                        if documents:
                            # ERWEITERTE Dokument-Konvertierung für alte Formate
                            converted_documents = []
                            for doc in documents:
                                try:
                                    # Verwende BackupManager für Datentyp-Konvertierung
                                    converted_doc = self.backup_manager._deserialize_from_backup(doc)
                                    fixed_doc = self.backup_manager._fix_id_for_restore(converted_doc)
                                    converted_documents.append(fixed_doc)
                                except Exception as e:
                                    logger.warning(f"Fehler bei Dokument-Konvertierung in {collection_name}: {str(e)}")
                                    # Fallback: Verwende ursprüngliches Dokument
                                    converted_documents.append(doc)
                            
                            mongodb.db[collection_name].insert_many(converted_documents)
                            restore_stats['successful_collections'] += 1
                            restore_stats['total_documents'] += len(converted_documents)
                            
                            logger.info(f"✅ Collection {collection_name}: {len(converted_documents)} Dokumente wiederhergestellt")
                        
                    except Exception as e:
                        logger.error(f"❌ Fehler beim Wiederherstellen der Collection {collection_name}: {str(e)}")
                        restore_stats['failed_collections'] += 1
                        
                        # Fallback für sehr alte Backups: Versuche ohne Konvertierung
                        try:
                            mongodb.db[collection_name].insert_many(documents)
                            logger.info(f"🔄 Collection {collection_name}: {len(documents)} Dokumente ohne Konvertierung wiederhergestellt (Fallback)")
                            restore_stats['successful_collections'] += 1
                            restore_stats['total_documents'] += len(documents)
                        except Exception as e2:
                            logger.error(f"💥 Kritischer Fehler bei {collection_name}: {str(e2)}")
                            restore_stats['failed_collections'] += 1
            
            # ERWEITERTE Erfolgsmeldung
            success_message = f"Backup erfolgreich wiederhergestellt ({format_info['version_estimate']} Format)"
            success_message += f" - {restore_stats['successful_collections']}/{restore_stats['total_collections']} Collections"
            success_message += f" - {restore_stats['total_documents']} Dokumente"
            
            if restore_stats['failed_collections'] > 0:
                success_message += f" - ⚠️ {restore_stats['failed_collections']} fehlgeschlagene Collections"
            
            if format_info['is_old_format']:
                success_message += " (altes Format - Konvertierung empfohlen)"
            
            return True, success_message
            
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen aus JSON: {str(e)}")
            return False, f"Fehler beim Wiederherstellen: {str(e)}"
    
    def _restore_files_from_archive(self, zipf: zipfile.ZipFile) -> None:
        """Stellt Dateien aus einem ZIP-Archiv wieder her"""
        try:
            # Uploads wiederherstellen
            uploads_dir = Path("app/static/uploads")
            uploads_dir.mkdir(parents=True, exist_ok=True)
            
            for file_info in zipf.filelist:
                if file_info.filename.startswith('uploads/'):
                    # Relativen Pfad extrahieren
                    relative_path = file_info.filename[8:]  # 'uploads/' entfernen
                    target_path = uploads_dir / relative_path
                    
                    # Verzeichnis erstellen falls nötig
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Datei extrahieren
                    with zipf.open(file_info.filename) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
            
            logger.info("Dateien erfolgreich wiederhergestellt")
            
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen der Dateien: {str(e)}")
    
    def get_backup_list(self) -> List[Dict[str, Any]]:
        """
        Gibt eine Liste aller verfügbaren Backups zurück
        
        Returns:
            List: Liste der Backup-Informationen
        """
        try:
            backup_dir = Path("backups")
            if not backup_dir.exists():
                return []
            
            backups = []
            
            # JSON-Backups
            for json_file in backup_dir.glob("*.json"):
                backup_info = self._get_backup_info(json_file)
                if backup_info:
                    backups.append(backup_info)
            
            # ZIP-Backups
            for zip_file in backup_dir.glob("*.zip"):
                backup_info = self._get_backup_info(zip_file)
                if backup_info:
                    backups.append(backup_info)
            
            # Nach Datum sortieren (neueste zuerst)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Liste: {str(e)}")
            return []
    
    def _get_backup_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extrahiert Informationen aus einer Backup-Datei"""
        try:
            stat = file_path.stat()
            
            backup_info = {
                'filename': file_path.name,
                'path': str(file_path),
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_mtime),
                'type': 'zip' if file_path.suffix == '.zip' else 'json'
            }
            
            # Zusätzliche Informationen aus JSON extrahieren falls möglich
            if file_path.suffix == '.json':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'metadata' in data:
                            backup_info['version'] = data['metadata'].get('version', '1.0')
                            backup_info['collections'] = data['metadata'].get('collections', [])
                except:
                    pass
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren der Backup-Informationen: {str(e)}")
            return None
    
    def delete_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Löscht ein Backup
        
        Args:
            backup_path: Pfad zur Backup-Datei
            
        Returns:
            Tuple: (success, message)
        """
        try:
            file_path = Path(backup_path)
            if not file_path.exists():
                return False, "Backup-Datei nicht gefunden"
            
            file_path.unlink()
            logger.info(f"Backup gelöscht: {backup_path}")
            return True, "Backup erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Backups: {str(e)}")
            return False, f"Fehler beim Löschen: {str(e)}" 