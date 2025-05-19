import os
import shutil
import logging
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import threading
import schedule
import time

logger = logging.getLogger(__name__)

class DatabaseBackup:
    def __init__(self, app_path):
        self.app_path = Path(app_path)
        self.backup_dir = self.app_path / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
        self.lock = threading.Lock()
        self._setup_backup_schedule()

    def _setup_backup_schedule(self):
        """Richtet den Backup-Zeitplan ein"""
        # Tägliches Backup um 3 Uhr morgens
        schedule.every().day.at("03:00").do(self.create_scheduled_backup)
        
        # Wöchentliches Backup am Sonntag um 4 Uhr morgens
        schedule.every().sunday.at("04:00").do(self.create_weekly_backup)
        
        # Starte den Scheduler in einem separaten Thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

    def create_backup(self, db_path, backup_type="manual"):
        """Erstellt ein Backup der Datenbank"""
        with self.lock:
            try:
                # Erstelle Backup-Verzeichnis falls nicht vorhanden
                self.backup_dir.mkdir(exist_ok=True)
                
                # Generiere Backup-Dateinamen
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{Path(db_path).stem}_{backup_type}_{timestamp}.db"
                backup_path = self.backup_dir / backup_name
                
                # Erstelle Backup
                with sqlite3.connect(db_path) as source:
                    # WAL-Datei synchronisieren
                    source.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    
                    # Backup erstellen
                    with sqlite3.connect(backup_path) as backup:
                        source.backup(backup)
                
                # Komprimiere Backup
                shutil.make_archive(str(backup_path), 'zip', self.backup_dir, backup_name)
                os.remove(backup_path)  # Lösche unkomprimierte Datei
                
                logger.info(f"Backup erstellt: {backup_path}.zip")
                
                # Lösche alte Backups
                self._cleanup_old_backups()
                
                return str(backup_path) + '.zip'
                
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
                raise

    def create_scheduled_backup(self):
        """Erstellt ein geplantes tägliches Backup"""
        try:
            db_path = self.app_path / 'app' / 'database' / 'inventory.db'
            self.create_backup(db_path, "daily")
            logger.info("Tägliches Backup erfolgreich erstellt")
        except Exception as e:
            logger.error(f"Fehler beim täglichen Backup: {str(e)}")

    def create_weekly_backup(self):
        """Erstellt ein wöchentliches Backup"""
        try:
            db_path = self.app_path / 'app' / 'database' / 'inventory.db'
            self.create_backup(db_path, "weekly")
            logger.info("Wöchentliches Backup erfolgreich erstellt")
        except Exception as e:
            logger.error(f"Fehler beim wöchentlichen Backup: {str(e)}")

    def _cleanup_old_backups(self):
        """Löscht alte Backups basierend auf Aufbewahrungsrichtlinien"""
        try:
            current_time = datetime.now()
            
            # Behalte tägliche Backups für 7 Tage
            daily_retention = current_time - timedelta(days=7)
            
            # Behalte wöchentliche Backups für 4 Wochen
            weekly_retention = current_time - timedelta(weeks=4)
            
            # Behalte manuelle Backups für 30 Tage
            manual_retention = current_time - timedelta(days=30)
            
            for backup_file in self.backup_dir.glob("*.zip"):
                try:
                    # Extrahiere Backup-Typ und Zeitstempel aus Dateinamen
                    parts = backup_file.stem.split('_')
                    if len(parts) >= 3:
                        backup_type = parts[1]
                        timestamp_str = '_'.join(parts[2:])
                        backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        
                        # Prüfe ob Backup gelöscht werden soll
                        should_delete = False
                        if backup_type == "daily" and backup_time < daily_retention:
                            should_delete = True
                        elif backup_type == "weekly" and backup_time < weekly_retention:
                            should_delete = True
                        elif backup_type == "manual" and backup_time < manual_retention:
                            should_delete = True
                        
                        if should_delete:
                            backup_file.unlink()
                            logger.info(f"Altes Backup gelöscht: {backup_file}")
                
                except Exception as e:
                    logger.error(f"Fehler beim Verarbeiten von Backup {backup_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Fehler beim Aufräumen alter Backups: {str(e)}")

    def restore_backup(self, backup_file):
        """Stellt ein Backup wieder her"""
        with self.lock:
            try:
                backup_path = self.backup_dir / backup_file
                if not backup_path.exists():
                    raise FileNotFoundError(f"Backup-Datei nicht gefunden: {backup_file}")
                
                # Entpacke Backup
                shutil.unpack_archive(str(backup_path), self.backup_dir, 'zip')
                db_file = backup_path.stem
                
                # Stelle Backup wieder her
                db_path = self.app_path / 'app' / 'database' / 'inventory.db'
                
                # Erstelle Backup der aktuellen Datenbank
                current_backup = f"{db_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(db_path, current_backup)
                
                # Kopiere Backup über aktuelle Datenbank
                shutil.copy2(self.backup_dir / db_file, db_path)
                
                # Lösche temporäre Dateien
                os.remove(self.backup_dir / db_file)
                
                logger.info(f"Backup {backup_file} erfolgreich wiederhergestellt")
                return True
                
            except Exception as e:
                logger.error(f"Fehler beim Wiederherstellen des Backups: {str(e)}")
                return False

    def list_backups(self):
        """Listet alle verfügbaren Backups"""
        try:
            backups = []
            for backup_file in self.backup_dir.glob("*.zip"):
                try:
                    parts = backup_file.stem.split('_')
                    if len(parts) >= 3:
                        backup_type = parts[1]
                        timestamp_str = '_'.join(parts[2:])
                        backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        
                        backups.append({
                            'filename': backup_file.name,
                            'type': backup_type,
                            'timestamp': backup_time,
                            'size': backup_file.stat().st_size
                        })
                except Exception as e:
                    logger.error(f"Fehler beim Verarbeiten von Backup {backup_file}: {str(e)}")
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Fehler beim Auflisten der Backups: {str(e)}")
            return [] 