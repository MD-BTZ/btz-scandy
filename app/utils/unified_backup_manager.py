#!/usr/bin/env python3
"""
Vereinheitlichter Backup-Manager für Scandy
- Natives MongoDB-Backup (Standard)
- JSON-Import für Kompatibilität
- Medien-Backup (optional)
- Automatische Komprimierung
"""

import os
import json
import shutil
import subprocess
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from bson import ObjectId

class UnifiedBackupManager:
    """
    Vereinheitlichter Backup-Manager für Scandy
    """
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Medien-Verzeichnisse
        self.media_dirs = [
            Path("app/static/uploads"),
            Path("app/uploads"),
            Path("uploads")
        ]
        
        # Backup-Konfiguration
        self.max_backup_size_gb = 10  # Maximale Backup-Größe
        self.include_media = True      # Medien einschließen
        self.compress_backups = True   # Backups komprimieren
        
    def create_backup(self, include_media: bool = True, compress: bool = True) -> Optional[str]:
        """
        Erstellt ein vollständiges Backup (Datenbank + Medien)
        
        Args:
            include_media: Medien einschließen
            compress: Backup komprimieren
            
        Returns:
            Backup-Dateiname oder None bei Fehler
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"scandy_backup_{timestamp}"
            
            print(f"🔄 Erstelle vereinheitlichtes Backup: {backup_name}")
            
            # 1. MongoDB-Backup erstellen
            db_backup_path = self._create_mongodb_backup(backup_name)
            if not db_backup_path:
                return None
            
            # 2. Medien-Backup (optional)
            media_backup_path = None
            if include_media:
                media_backup_path = self._create_media_backup(backup_name)
            
            # 3. Konfiguration sichern
            config_backup_path = self._create_config_backup(backup_name)
            
            # 4. Alles zusammenfassen
            final_backup_path = self._create_final_backup(
                backup_name, 
                db_backup_path, 
                media_backup_path, 
                config_backup_path,
                compress
            )
            
            if final_backup_path:
                print(f"✅ Backup erfolgreich erstellt: {final_backup_path}")
                self._cleanup_temp_files([db_backup_path, media_backup_path, config_backup_path])
                return final_backup_path
            else:
                return None
                
        except Exception as e:
            print(f"❌ Fehler beim Erstellen des Backups: {e}")
            return None
    
    def _create_mongodb_backup(self, backup_name: str) -> Optional[Path]:
        """Erstellt MongoDB-Backup"""
        try:
            temp_dir = Path(tempfile.mkdtemp())
            backup_path = temp_dir / backup_name
            
            # MongoDB-Verbindungsdaten
            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
            db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
            
            # mongodump ausführen
            cmd = [
                '/usr/bin/mongodump',
                '--uri', mongo_uri,
                '--out', str(backup_path),
                '--gzip'
            ]
            
            print(f"  📊 Erstelle MongoDB-Backup...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"  ✅ MongoDB-Backup erstellt")
                return backup_path
            else:
                print(f"  ❌ MongoDB-Backup fehlgeschlagen: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"  ❌ Fehler beim MongoDB-Backup: {e}")
            return None
    
    def _create_media_backup(self, backup_name: str) -> Optional[Path]:
        """Erstellt Medien-Backup"""
        try:
            temp_dir = Path(tempfile.mkdtemp())
            media_backup_path = temp_dir / f"{backup_name}_media"
            media_backup_path.mkdir(exist_ok=True)
            
            print(f"  📁 Erstelle Medien-Backup...")
            
            total_size = 0
            copied_files = 0
            
            # Alle Medien-Verzeichnisse durchsuchen
            for media_dir in self.media_dirs:
                if media_dir.exists():
                    print(f"    📂 Kopiere Medien aus: {media_dir}")
                    
                    # Rekursiv kopieren
                    for root, dirs, files in os.walk(media_dir):
                        # Relativen Pfad berechnen
                        rel_path = Path(root).relative_to(media_dir)
                        target_dir = media_backup_path / rel_path
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        for file in files:
                            source_file = Path(root) / file
                            target_file = target_dir / file
                            
                            # Dateigröße prüfen
                            file_size = source_file.stat().st_size
                            if total_size + file_size > self.max_backup_size_gb * 1024**3:
                                print(f"    ⚠️  Maximale Backup-Größe erreicht, überspringe weitere Medien")
                                break
                            
                            # Datei kopieren
                            shutil.copy2(source_file, target_file)
                            total_size += file_size
                            copied_files += 1
                    
                    print(f"    ✅ {copied_files} Dateien kopiert ({self._format_size(total_size)})")
                    break  # Nur das erste gefundene Verzeichnis verwenden
            
            if copied_files > 0:
                return media_backup_path
            else:
                print(f"    ⚠️  Keine Medien gefunden")
                return None
                
        except Exception as e:
            print(f"  ❌ Fehler beim Medien-Backup: {e}")
            return None
    
    def _create_config_backup(self, backup_name: str) -> Optional[Path]:
        """Erstellt Konfigurations-Backup"""
        try:
            temp_dir = Path(tempfile.mkdtemp())
            config_backup_path = temp_dir / f"{backup_name}_config"
            config_backup_path.mkdir(exist_ok=True)
            
            print(f"  ⚙️  Erstelle Konfigurations-Backup...")
            
            # Wichtige Konfigurationsdateien kopieren
            config_files = [
                Path(".env"),
                Path("docker-compose.yml"),
                Path("requirements.txt"),
                Path("package.json")
            ]
            
            copied_files = 0
            for config_file in config_files:
                if config_file.exists():
                    shutil.copy2(config_file, config_backup_path / config_file.name)
                    copied_files += 1
            
            if copied_files > 0:
                print(f"  ✅ {copied_files} Konfigurationsdateien kopiert")
                return config_backup_path
            else:
                print(f"  ⚠️  Keine Konfigurationsdateien gefunden")
                return None
                
        except Exception as e:
            print(f"  ❌ Fehler beim Konfigurations-Backup: {e}")
            return None
    
    def _create_final_backup(self, backup_name: str, db_path: Path, 
                            media_path: Optional[Path], config_path: Optional[Path],
                            compress: bool) -> Optional[str]:
        """Erstellt das finale Backup-Paket"""
        try:
            final_backup_path = self.backup_dir / f"{backup_name}.zip"
            
            print(f"  📦 Erstelle finales Backup-Paket...")
            
            with zipfile.ZipFile(final_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # MongoDB-Backup hinzufügen
                if db_path and db_path.exists():
                    for root, dirs, files in os.walk(db_path):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = f"mongodb/{file_path.relative_to(db_path)}"
                            zipf.write(file_path, arcname)
                
                # Medien-Backup hinzufügen
                if media_path and media_path.exists():
                    for root, dirs, files in os.walk(media_path):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = f"media/{file_path.relative_to(media_path)}"
                            zipf.write(file_path, arcname)
                
                # Konfigurations-Backup hinzufügen
                if config_path and config_path.exists():
                    for root, dirs, files in os.walk(config_path):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = f"config/{file_path.relative_to(config_path)}"
                            zipf.write(file_path, arcname)
                
                # Backup-Metadaten hinzufügen
                metadata = {
                    'backup_name': backup_name,
                    'created_at': datetime.now().isoformat(),
                    'includes_media': media_path is not None,
                    'includes_config': config_path is not None,
                    'compressed': compress,
                    'version': '2.0'
                }
                
                zipf.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
            
            backup_size = final_backup_path.stat().st_size
            print(f"  ✅ Finales Backup erstellt: {self._format_size(backup_size)}")
            
            return final_backup_path.name
            
        except Exception as e:
            print(f"  ❌ Fehler beim Erstellen des finalen Backups: {e}")
            return None
    
    def restore_backup(self, backup_filename: str, include_media: bool = True) -> bool:
        """
        Stellt ein Backup wieder her
        
        Args:
            backup_filename: Name der Backup-Datei
            include_media: Medien wiederherstellen
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                print(f"❌ Backup nicht gefunden: {backup_path}")
                return False
            
            print(f"🔄 Stelle Backup wieder her: {backup_filename}")
            
            # Temporäres Verzeichnis für Extraktion
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Backup extrahieren
                print(f"  📦 Extrahiere Backup...")
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_path)
                
                # Metadaten lesen
                metadata_path = temp_path / 'backup_metadata.json'
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    print(f"  📋 Backup-Metadaten: {metadata.get('backup_name', 'Unbekannt')}")
                
                # 1. MongoDB wiederherstellen
                mongodb_path = temp_path / 'mongodb'
                if mongodb_path.exists():
                    success = self._restore_mongodb(mongodb_path)
                    if not success:
                        return False
                
                # 2. Medien wiederherstellen (optional)
                if include_media:
                    media_path = temp_path / 'media'
                    if media_path.exists():
                        success = self._restore_media(media_path)
                        if not success:
                            print(f"  ⚠️  Medien-Wiederherstellung fehlgeschlagen, fahre fort...")
                
                # 3. Konfiguration wiederherstellen (optional)
                config_path = temp_path / 'config'
                if config_path.exists():
                    success = self._restore_config(config_path)
                    if not success:
                        print(f"  ⚠️  Konfigurations-Wiederherstellung fehlgeschlagen, fahre fort...")
                
                print(f"✅ Backup erfolgreich wiederhergestellt")
                return True
                
        except Exception as e:
            print(f"❌ Fehler beim Wiederherstellen des Backups: {e}")
            return False
    
    def _restore_mongodb(self, mongodb_path: Path) -> bool:
        """Stellt MongoDB-Backup wieder her"""
        try:
            print(f"  📊 Stelle MongoDB wieder her...")
            
            # MongoDB-Verbindungsdaten
            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
            db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
            
            # mongorestore ausführen
            cmd = [
                '/usr/bin/mongorestore',
                '--uri', mongo_uri,
                '--gzip',
                '--drop',  # Bestehende Collections löschen
                str(mongodb_path / db_name)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"  ✅ MongoDB erfolgreich wiederhergestellt")
                return True
            else:
                print(f"  ❌ MongoDB-Wiederherstellung fehlgeschlagen: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"  ❌ Fehler bei MongoDB-Wiederherstellung: {e}")
            return False
    
    def _restore_media(self, media_path: Path) -> bool:
        """Stellt Medien wieder her"""
        try:
            print(f"  📁 Stelle Medien wieder her...")
            
            # Zielverzeichnis für Medien
            target_dir = Path("app/static/uploads")
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Medien kopieren
            copied_files = 0
            for root, dirs, files in os.walk(media_path):
                # Relativen Pfad berechnen
                rel_path = Path(root).relative_to(media_path)
                target_subdir = target_dir / rel_path
                target_subdir.mkdir(parents=True, exist_ok=True)
                
                for file in files:
                    source_file = Path(root) / file
                    target_file = target_subdir / file
                    
                    # Datei kopieren
                    shutil.copy2(source_file, target_file)
                    copied_files += 1
            
            print(f"  ✅ {copied_files} Mediendateien wiederhergestellt")
            return True
            
        except Exception as e:
            print(f"  ❌ Fehler bei Medien-Wiederherstellung: {e}")
            return False
    
    def _restore_config(self, config_path: Path) -> bool:
        """Stellt Konfiguration wieder her"""
        try:
            print(f"  ⚙️  Stelle Konfiguration wieder her...")
            
            # Konfigurationsdateien kopieren
            copied_files = 0
            for config_file in config_path.iterdir():
                if config_file.is_file():
                    target_file = Path(config_file.name)
                    shutil.copy2(config_file, target_file)
                    copied_files += 1
            
            print(f"  ✅ {copied_files} Konfigurationsdateien wiederhergestellt")
            return True
            
        except Exception as e:
            print(f"  ❌ Fehler bei Konfigurations-Wiederherstellung: {e}")
            return False
    
    def import_json_backup(self, json_file_path: str) -> bool:
        """
        Importiert ein altes JSON-Backup
        
        Args:
            json_file_path: Pfad zur JSON-Backup-Datei
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            print(f"🔄 Importiere JSON-Backup: {json_file_path}")
            
            # JSON-Datei laden
            with open(json_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Backup validieren
            if not self._validate_json_backup(backup_data):
                print(f"❌ Ungültiges JSON-Backup")
                return False
            
            # MongoDB-Verbindung
            from pymongo import MongoClient
            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
            db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
            
            client = MongoClient(mongo_uri)
            db = client[db_name]
            
            # Collections wiederherstellen
            for collection_name, documents in backup_data.items():
                if collection_name == 'metadata':
                    continue
                
                print(f"  📊 Stelle Collection wieder her: {collection_name}")
                
                # Collection leeren
                db[collection_name].delete_many({})
                
                # Dokumente wiederherstellen
                if documents:
                    # IDs korrigieren
                    fixed_documents = []
                    for doc in documents:
                        fixed_doc = self._fix_json_document(doc)
                        fixed_documents.append(fixed_doc)
                    
                    # Dokumente einfügen
                    if fixed_documents:
                        db[collection_name].insert_many(fixed_documents)
                        print(f"    ✅ {len(fixed_documents)} Dokumente wiederhergestellt")
            
            print(f"✅ JSON-Backup erfolgreich importiert")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Importieren des JSON-Backups: {e}")
            return False
    
    def _validate_json_backup(self, backup_data: Dict) -> bool:
        """Validiert JSON-Backup-Daten"""
        if not isinstance(backup_data, dict):
            return False
        
        # Prüfe ob es das neue Format ist
        if 'metadata' in backup_data and 'data' in backup_data:
            data_section = backup_data['data']
        else:
            data_section = backup_data
        
        # Mindestanforderungen
        required_collections = ['tools', 'workers', 'consumables', 'settings']
        missing_collections = [coll for coll in required_collections if coll not in data_section]
        
        if missing_collections:
            print(f"Fehlende Collections: {missing_collections}")
            return False
        
        return True
    
    def _fix_json_document(self, doc: Dict) -> Dict:
        """Korrigiert JSON-Dokument für MongoDB-Import"""
        if not isinstance(doc, dict):
            return doc
        
        # _id konvertieren
        if '_id' in doc:
            if isinstance(doc['_id'], str) and len(doc['_id']) == 24:
                try:
                    doc['_id'] = ObjectId(doc['_id'])
                except:
                    del doc['_id']
            elif not isinstance(doc['_id'], ObjectId):
                del doc['_id']
        
        # Datetime-Felder konvertieren
        datetime_fields = ['created_at', 'updated_at', 'modified_at', 'deleted_at']
        for field in datetime_fields:
            if field in doc and isinstance(doc[field], str):
                try:
                    doc[field] = datetime.fromisoformat(doc[field].replace('Z', '+00:00'))
                except:
                    pass
        
        return doc
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Listet alle verfügbaren Backups auf"""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.zip"):
            try:
                with zipfile.ZipFile(backup_file, 'r') as zipf:
                    # Metadaten lesen
                    if 'backup_metadata.json' in zipf.namelist():
                        metadata_content = zipf.read('backup_metadata.json')
                        metadata = json.loads(metadata_content.decode('utf-8'))
                    else:
                        metadata = {
                            'backup_name': backup_file.stem,
                            'created_at': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                            'version': '1.0'
                        }
                
                backups.append({
                    'filename': backup_file.name,
                    'size': self._format_size(backup_file.stat().st_size),
                    'created_at': metadata.get('created_at', 'Unbekannt'),
                    'includes_media': metadata.get('includes_media', False),
                    'version': metadata.get('version', '1.0')
                })
                
            except Exception as e:
                print(f"Fehler beim Lesen von Backup {backup_file.name}: {e}")
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)
    
    def _cleanup_temp_files(self, temp_paths: List[Optional[Path]]):
        """Räumt temporäre Dateien auf"""
        for temp_path in temp_paths:
            if temp_path and temp_path.exists():
                try:
                    shutil.rmtree(temp_path)
                except Exception as e:
                    print(f"Warnung: Konnte temporäre Dateien nicht löschen: {e}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Formatiert Dateigröße"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

# Globale Instanz
unified_backup_manager = UnifiedBackupManager() 