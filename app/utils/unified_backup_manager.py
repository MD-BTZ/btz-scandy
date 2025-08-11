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
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import random
import string
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
        
        # Import-Job Verwaltung (Statusablage in MongoDB)
        # Hinweis: Für Persistenz/Mehrprozess-Sicherheit wird MongoDB genutzt, nicht nur RAM.

    # ===== Normalisierungs-Helfer =====
    @staticmethod
    def _norm_str(value: Any) -> Optional[str]:
        try:
            if value is None:
                return None
            s = str(value).strip()
            return s if s else None
        except Exception:
            return None

    @staticmethod
    def _normalize_barcode(value: Any) -> Optional[str]:
        # Barcodes als getrimmten String behandeln (Groß/Kleinschreibung beibehalten)
        return UnifiedBackupManager._norm_str(value)

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
                # Alte Backups (>7 Tage) aufräumen
                try:
                    self._prune_old_backups(days=7)
                except Exception as e:
                    print(f"⚠️  Konnte alte Backups nicht bereinigen: {e}")
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
            backup_path.mkdir(exist_ok=True)
            
            # MongoDB-Verbindungsdaten
            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
            db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
            
            print(f"  📊 Erstelle MongoDB-Backup...")
            
            # Versuche mongodump zu verwenden
            try:
                cmd = [
                    'mongodump',
                    '--uri', mongo_uri,
                    '--out', str(backup_path),
                    '--gzip'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print(f"  ✅ MongoDB-Backup mit mongodump erstellt")
                    return backup_path
                else:
                    print(f"  ⚠️  mongodump fehlgeschlagen, verwende Python-Backup: {result.stderr}")
                    raise Exception("mongodump nicht verfügbar")
                    
            except (FileNotFoundError, Exception):
                # Fallback: Python-basiertes Backup
                print(f"  🔄 Verwende Python-basiertes MongoDB-Backup...")
                
                from app.models.mongodb_database import mongodb
                from datetime import datetime
                
                # Collections die gesichert werden sollen
                collections = [
                    'tools', 'workers', 'consumables', 'lendings', 
                    'consumable_usages', 'tickets', 'users', 'settings',
                    'homepage_notices', 'work_times', 'jobs', 'timesheets',
                    'auftrag_details', 'auftrag_material', 'email_config', 
                    'email_settings', 'system_logs'
                ]
                
                backup_data = {
                    'metadata': {
                        'created_at': datetime.now().isoformat(),
                        'version': '2.0',
                        'datatype_preservation': True,
                        'collections': []
                    },
                    'data': {}
                }
                
                for collection_name in collections:
                    try:
                        # Alle Dokumente aus der Collection laden
                        documents = list(mongodb.find(collection_name, {}))
                        
                        if documents:
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
                            
                            print(f"    ✅ Collection {collection_name}: {len(backup_documents)} Dokumente")
                            
                    except Exception as e:
                        print(f"    ⚠️  Fehler bei Collection {collection_name}: {e}")
                        continue
                
                # Backup-Datei speichern
                backup_file = backup_path / f"{backup_name}.json"
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)
                
                print(f"  ✅ Python-basiertes MongoDB-Backup erstellt")
                return backup_path
                
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
            
            # Datenbereich ermitteln (neu: data, alt: flach)
            data_section = backup_data['data'] if ('metadata' in backup_data and 'data' in backup_data) else backup_data

            # Collections wiederherstellen (inkl. users)
            for collection_name, documents in data_section.items():
                if collection_name == 'metadata':
                    continue
                
                print(f"  📊 Stelle Collection wieder her: {collection_name}")
                
                # Collection leeren (vollständiger Import)
                db[collection_name].delete_many({})
                
                # Dokumente wiederherstellen
                if documents:
                    # IDs korrigieren
                    fixed_documents = []
                    for doc in documents:
                        fixed_doc = self._fix_json_document(doc)
                        # Spezielle Behandlung für Benutzer: Passwort sicherstellen
                        if collection_name == 'users':
                            try:
                                from werkzeug.security import generate_password_hash
                                if not fixed_doc.get('password_hash'):
                                    if fixed_doc.get('password'):
                                        fixed_doc['password_hash'] = generate_password_hash(fixed_doc['password'])
                                    else:
                                        pw = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                                        fixed_doc['password_hash'] = generate_password_hash(pw)
                                fixed_doc.pop('password', None)
                                fixed_doc.setdefault('role', 'anwender')
                                fixed_doc.setdefault('is_active', True)
                            except Exception:
                                pass
                        fixed_documents.append(fixed_doc)
                    
                    # Dokumente einfügen
                    if fixed_documents:
                        db[collection_name].insert_many(fixed_documents)
                        print(f"    ✅ {len(fixed_documents)} Dokumente wiederhergestellt")
            # Nach dem Import: Verwaiste Nutzernamen anonymisieren
            try:
                self._anonymize_orphan_user_names()
            except Exception as e:
                print(f"⚠️  Konnte Orphan-Namen nicht anonymisieren: {e}")
            
            print(f"✅ JSON-Backup erfolgreich importiert")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Importieren des JSON-Backups: {e}")
            return False
    
    def _validate_json_backup(self, backup_data: Dict) -> bool:
        """Validiert JSON-Backup-Daten (tolerant für alte Formate)."""
        try:
            if not isinstance(backup_data, dict):
                return False

            # Prüfe Struktur (neu: metadata+data, alt: flach)
            if 'metadata' in backup_data and 'data' in backup_data and isinstance(backup_data['data'], dict):
                data_section = backup_data['data']
            else:
                data_section = backup_data

            if not isinstance(data_section, dict):
                return False

            # Akzeptiere, wenn mindestens eine relevante Collection vorhanden ist
            relevant = {
                'tools', 'workers', 'consumables', 'lendings', 'consumable_usages',
                'tickets', 'ticket_messages', 'ticket_notes', 'auftrag_details', 'auftrag_material',
                'users', 'settings'
            }
            present = [k for k in data_section.keys() if k in relevant]
            if not present:
                print("JSON enthält keine relevanten Collections")
                return False
            return True
        except Exception:
            return False
    
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

    def _anonymize_orphan_user_names(self):
        """Ersetzt Namen/Bezüge auf nicht vorhandene Benutzer durch 'Anonym'."""
        from datetime import datetime as _dt
        try:
            from app.models.mongodb_database import mongodb
            existing_users = set(u.get('username') for u in mongodb.find('users', {}) if u.get('username'))
            anonymized = 0
            # Felder, die Usernamen enthalten können
            username_fields = ['created_by', 'assigned_to', 'reporter', 'author', 'user', 'username']
            name_fields = ['created_by_name', 'assigned_to_name', 'reporter_name', 'author_name', 'user_name']
            for collection in ['tickets', 'messages', 'ticket_messages', 'ticket_history']:
                docs = list(mongodb.find(collection, {}))
                for doc in docs:
                    updates = {}
                    # Username-Felder: nullen, wenn User nicht existiert
                    for field in username_fields:
                        if field in doc and doc.get(field) and doc.get(field) not in existing_users:
                            updates[field] = None
                    # Namens-Felder: auf 'Anonym' setzen, wenn korrespondierender Benutzer fehlt
                    for field in name_fields:
                        if field in doc and doc.get(field):
                            related_user = None
                            if field.endswith('_name'):
                                base = field[:-5]
                                related_user = doc.get(base)
                            if (not related_user) or (related_user not in existing_users):
                                if doc.get(field) != 'Anonym':
                                    updates[field] = 'Anonym'
                    if updates:
                        updates['updated_at'] = _dt.now()
                        mongodb.update_one(collection, {'_id': doc['_id']}, {'$set': updates})
                        anonymized += 1
            if anonymized:
                print(f"  🔒 {anonymized} Dokumente anonymisiert (fehlende Benutzer)")
        except Exception as e:
            print(f"⚠️  Anonymisierung fehlgeschlagen: {e}")
    
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

    def _prune_old_backups(self, days: int = 7):
        """Löscht Backup-ZIP-Dateien, die älter als 'days' Tage sind."""
        cutoff = datetime.now().timestamp() - days * 86400
        removed = 0
        for backup_file in self.backup_dir.glob('scandy_backup_*.zip'):
            try:
                if backup_file.stat().st_mtime < cutoff:
                    backup_file.unlink()
                    removed += 1
            except Exception:
                continue
        if removed:
            print(f"🧹 {removed} alte Backups (> {days} Tage) gelöscht")

    def import_json_backup_scoped(self, json_file_path: str, target_department: str) -> bool:
        """Importiert ein altes JSON-Backup und weist alle Daten der angegebenen Abteilung zu."""
        try:
            # Stelle sicher, dass während des Imports das Department-Scoping mit der Ziel-Abteilung übereinstimmt
            try:
                from flask import g, has_app_context
                _had_ctx = has_app_context()
                _old_dep = getattr(g, 'current_department', None) if _had_ctx else None
                if _had_ctx:
                    g.current_department = target_department
            except Exception:
                _had_ctx = False
                _old_dep = None
            if not target_department:
                print("❌ Keine Ziel-Abteilung angegeben")
                return False
            print(f"🔄 Importiere JSON-Backup (Department={target_department}): {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            if not self._validate_json_backup(backup_data):
                print("❌ Ungültiges JSON-Backup")
                return False
            # Verwende die bestehende App-Datenbankverbindung
            from app.models.mongodb_database import mongodb
            # Datenbereich extrahieren
            data_section = backup_data['data'] if ('metadata' in backup_data and 'data' in backup_data) else backup_data
            # Collections importieren – 'settings' nur selektiv
            scoped_collections = ['tools', 'workers', 'consumables', 'lendings', 'consumable_usages', 'tickets', 'ticket_messages', 'ticket_notes', 'auftrag_details', 'auftrag_material']
            total_inserted = 0
            total_failed = 0
            for collection_name, documents in data_section.items():
                if collection_name == 'metadata':
                    continue
                if collection_name not in scoped_collections:
                    # Überspringe nicht-relevante oder system-Collections
                    continue
                print(f"  📊 Stelle Collection wieder her (scoped): {collection_name}")
                inserted_count = 0
                failed_count = 0
                for doc in documents or []:
                    doc = self._fix_json_document(doc)
                    # IDs immer entfernen, um Kollisionen zu vermeiden
                    if '_id' in doc:
                        try:
                            del doc['_id']
                        except Exception:
                            pass
                    # Alte/inkompatible Abteilungsfelder entfernen
                    dept_like_fields = ['department', 'allowed_departments', 'default_department', 'departments', 'dept', 'dept_id', 'source_department', 'target_department']
                    for key in list(doc.keys()):
                        if key in dept_like_fields:
                            try:
                                del doc[key]
                            except Exception:
                                pass
                    # Department erzwingen
                    doc['department'] = target_department
                    if collection_name == 'tickets':
                        # Ziel-Abteilung in Tickets ggf. zusätzlich setzen
                        doc['target_department'] = target_department
                    # Einfügen/Upsert mit Duplikat-Schutz
                    try:
                        # Legacy-Dokumente ohne Department bevorzugt umhängen statt duplizieren
                        if collection_name in ('tools', 'workers', 'consumables'):
                            # Barcode normalisieren
                            bc = self._normalize_barcode(doc.get('barcode'))
                            if not bc:
                                # Ohne Barcode keine Idempotenz möglich -> Insert als Fallback
                                mongodb.insert_one(collection_name, doc)
                                inserted_count += 1
                                continue
                            doc['barcode'] = bc
                            try:
                                mongodb.update_one(
                                    collection_name,
                                    {'barcode': bc, 'department': {'$exists': False}},
                                    {'$set': {'department': target_department}},
                                    upsert=False
                                )
                            except Exception:
                                pass
                            # Idempotentes Upsert pro (department, barcode)
                            ok = mongodb.update_one(
                                collection_name,
                                {'barcode': bc, 'department': target_department},
                                {'$set': doc},
                                upsert=True
                            )
                            if ok:
                                inserted_count += 1
                            continue
                        # Tickets: Upsert per ticket_number, falls vorhanden
                        if collection_name == 'tickets' and doc.get('ticket_number'):
                            ok = mongodb.update_one(
                                'tickets',
                                {'ticket_number': doc['ticket_number'], 'department': target_department},
                                {'$set': doc},
                                upsert=True
                            )
                            if ok:
                                inserted_count += 1
                            continue
                        # Fallback: normales Insert
                        mongodb.insert_one(collection_name, doc)
                        inserted_count += 1
                    except Exception as e:
                        failed_count += 1
                        # Kurz-Log, aber Import fortsetzen
                        print(f"    ⚠️  Fehler beim Einfügen in {collection_name}: {e}")
                total_inserted += inserted_count
                total_failed += failed_count
                print(f"    ✅ {inserted_count} eingefügt, ❌ {failed_count} fehlgeschlagen in {collection_name}")
            print(f"✅ JSON-Backup (scoped) abgeschlossen – Gesamt: {total_inserted} eingefügt, {total_failed} fehlgeschlagen")
            # Optional: Benutzer global importieren, wenn vorhanden (idempotent über username)
            try:
                users_docs = data_section.get('users')
                if isinstance(users_docs, list):
                    from app.models.mongodb_database import mongodb
                    from werkzeug.security import generate_password_hash
                    for doc in users_docs:
                        try:
                            fixed = self._fix_json_document(doc)
                            username = (fixed.get('username') or '').strip()
                            if not username:
                                continue
                            # Passwort sicherstellen
                            if not fixed.get('password_hash'):
                                if fixed.get('password'):
                                    fixed['password_hash'] = generate_password_hash(fixed['password'])
                                else:
                                    pw = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                                    fixed['password_hash'] = generate_password_hash(pw)
                            fixed.pop('password', None)
                            fixed.setdefault('role', 'anwender')
                            fixed.setdefault('is_active', True)
                            # Department-Felder entfernen, Nutzer sind global
                            for k in ['department', 'allowed_departments', 'default_department', 'departments']:
                                if k in fixed and k != 'allowed_departments' and k != 'default_department':
                                    fixed.pop(k, None)
                            # Idempotentes Upsert am username
                            mongodb.update_one('users', {'username': username}, {'$setOnInsert': {'created_at': datetime.now()}, '$set': fixed}, upsert=True)
                        except Exception as e:
                            print(f"    ⚠️  Nutzer-Import: {e}")
            except Exception as e:
                print(f"⚠️  Benutzer-Import (scoped) übersprungen: {e}")

            # Nachzug: Orphan-Namen anonymisieren
            try:
                self._anonymize_orphan_user_names()
            except Exception as e:
                print(f"⚠️  Orphan-Anonymisierung (scoped) fehlgeschlagen: {e}")

            # Erfolg, wenn mindestens ein Dokument eingefügt wurde
            return total_inserted > 0
        except Exception as e:
            print(f"❌ Fehler beim scoped-Import: {e}")
            return False
        finally:
            # Ursprüngliches Department im Kontext wiederherstellen
            try:
                if _had_ctx:
                    from flask import g
                    g.current_department = _old_dep
            except Exception:
                pass

    def import_json_backup_scoped_report(self, json_file_path: str, target_department: str) -> dict:
        """
        Wie import_json_backup_scoped, liefert aber eine Detail-Statistik zurück.
        Rückgabe:
          { ok: bool, total_inserted: int, total_failed: int,
            per_collection: { name: {inserted:int, failed:int} }, errors: [str,...] }
        """
        report = {
            'ok': False,
            'total_inserted': 0,
            'total_failed': 0,
            'total_duplicates': 0,
            'per_collection': {},
            'errors': []
        }
        try:
            # Department-Kontext für den Import setzen (falls App-Kontext vorhanden)
            try:
                from flask import g, has_app_context
                _had_ctx = has_app_context()
                _old_dep = getattr(g, 'current_department', None) if _had_ctx else None
                if _had_ctx:
                    g.current_department = target_department
            except Exception:
                _had_ctx = False
                _old_dep = None
            if not target_department:
                report['errors'].append('Keine Ziel-Abteilung angegeben')
                return report
            with open(json_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            if not self._validate_json_backup(backup_data):
                report['errors'].append('Ungültiges JSON-Backup')
                return report
            from app.models.mongodb_database import mongodb
            data_section = backup_data['data'] if ('metadata' in backup_data and 'data' in backup_data) else backup_data
            scoped_collections = ['tools', 'workers', 'consumables', 'lendings', 'consumable_usages', 'tickets', 'ticket_messages', 'ticket_notes', 'auftrag_details', 'auftrag_material']
            from pymongo.errors import DuplicateKeyError
            for collection_name, documents in data_section.items():
                if collection_name == 'metadata':
                    continue
                if collection_name not in scoped_collections:
                    continue
                inserted_count = 0
                failed_count = 0
                duplicate_count = 0
                reassigned_count = 0
                for doc in documents or []:
                    try:
                        doc = self._fix_json_document(doc)
                        if '_id' in doc:
                            del doc['_id']
                        for key in ['department', 'allowed_departments', 'default_department', 'departments', 'dept', 'dept_id', 'source_department', 'target_department']:
                            if key in doc:
                                del doc[key]
                        doc['department'] = target_department
                        if collection_name == 'tickets':
                            doc['target_department'] = target_department
                        # Vorab: Versuche vorhandenes Dokument ohne Department auf Ziel-Abteilung umzuhängen
                        if collection_name in ('tools', 'workers', 'consumables') and doc.get('barcode'):
                            # Reassign nur, wenn bestehendes Dokument KEIN department-Feld hat
                            reassigned = mongodb.update_one(
                                collection_name,
                                {'barcode': doc['barcode'], 'department': {'$exists': False}},
                                {'$set': {'department': target_department}},
                                upsert=False
                            )
                            if reassigned:
                                reassigned_count += 1
                                # Optional: weitere Felder aktualisieren? Vorsichtig: Nur Dept setzen um Daten nicht zu überschreiben
                                continue
                        mongodb.insert_one(collection_name, doc)
                        inserted_count += 1
                    except DuplicateKeyError as e:
                        # Duplikat: als übersprungen zählen, nicht als Fehler
                        duplicate_count += 1
                    except Exception as e:
                        failed_count += 1
                        if len(report['errors']) < 20:
                            report['errors'].append(f"{collection_name}: {e}")
                report['per_collection'][collection_name] = {
                    'inserted': inserted_count,
                    'failed': failed_count,
                    'duplicates': duplicate_count,
                    'reassigned': reassigned_count
                }
                report['total_inserted'] += inserted_count
                report['total_failed'] += failed_count
                report['total_duplicates'] += duplicate_count
                report['total_reassigned'] = report.get('total_reassigned', 0) + reassigned_count
            # Erfolg, wenn Insert stattfand oder nur Duplikate vorlagen
            report['ok'] = (report['total_inserted'] > 0 and len(report['errors']) == 0) or (
                report['total_inserted'] == 0 and report['total_failed'] == 0 and report['total_duplicates'] > 0
            )
            return report
        except Exception as e:
            report['errors'].append(str(e))
            return report
        finally:
            try:
                if _had_ctx:
                    from flask import g
                    g.current_department = _old_dep
            except Exception:
                pass
    
    # ===== Hintergrund-Jobs für Import =====
    def start_import_job(self, json_file_path: str, target_department: str) -> str:
        """Startet einen Hintergrund-Import-Job und gibt die Job-ID zurück."""
        job_id = str(uuid.uuid4())
        try:
            from app.models.mongodb_database import mongodb
            now = datetime.now()
            job_doc = {
                '_id': job_id,
                'type': 'json_scoped_import',
                'status': 'running',
                'created_at': now,
                'updated_at': now,
                'file_path': json_file_path,
                'target_department': target_department,
                'progress': {'inserted': 0, 'failed': 0, 'duplicates': 0},
                'result': None,
                'errors': []
            }
            mongodb.insert_one('import_jobs', job_doc)

            # Hintergrund-Thread starten
            thread = threading.Thread(target=self._run_import_job, args=(job_id,), daemon=True)
            thread.start()
            return job_id
        except Exception as e:
            # Fallback: Job nicht gestartet
            return ''

    def _run_import_job(self, job_id: str):
        """Führt den Import-Job im Hintergrund aus und aktualisiert den Status in MongoDB."""
        from app.models.mongodb_database import mongodb
        try:
            job = mongodb.find_one('import_jobs', {'_id': job_id})
            if not job:
                return
            json_file_path = job.get('file_path')
            target_department = job.get('target_department')

            # Import ausführen (mit Report)
            report = self.import_json_backup_scoped_report(json_file_path, target_department)

            # Status aktualisieren
            status = 'done' if report.get('ok') else 'error'
            mongodb.update_one('import_jobs', {'_id': job_id}, {'$set': {
                'status': status,
                'updated_at': datetime.now(),
                'result': report,
                'progress': {
                    'inserted': report.get('total_inserted', 0),
                    'failed': report.get('total_failed', 0),
                    'duplicates': report.get('total_duplicates', 0)
                },
                'errors': report.get('errors', [])
            }})
        except Exception as e:
            mongodb.update_one('import_jobs', {'_id': job_id}, {'$set': {
                'status': 'error',
                'updated_at': datetime.now(),
                'errors': [str(e)]
            }})

    def get_import_job(self, job_id: str) -> dict:
        """Liest den Status eines Import-Jobs aus MongoDB."""
        try:
            from app.models.mongodb_database import mongodb
            job = mongodb.find_one('import_jobs', {'_id': job_id})
            if not job:
                return {'exists': False}
            # Konvertiere Datumswerte für JSON-Ausgabe
            for k in ['created_at', 'updated_at']:
                if k in job and isinstance(job[k], datetime):
                    job[k] = job[k].isoformat()
            job['exists'] = True
            return job
        except Exception as e:
            return {'exists': False, 'error': str(e)}

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