import os
import shutil
from datetime import datetime, timedelta
import glob
import logging
from pathlib import Path
import json
import sqlite3

# Logging einrichten
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseBackup:
    def __init__(self, app_path=None):
        # Basis-Verzeichnis bestimmen
        if app_path:
            self.base_dir = Path(app_path)
        else:
            self.base_dir = Path.cwd()

        # Konfiguration
        self.db_path = self.base_dir / 'app' / 'database' / 'inventory.db'
        self.backup_dir = self.base_dir / 'backups'
        self.max_days = 7

        # Backup-Verzeichnis erstellen
        self.backup_dir.mkdir(exist_ok=True)
        logger.info(f"DatabaseBackup initialisiert mit:")
        logger.info(f"- Basis-Verzeichnis: {self.base_dir}")
        logger.info(f"- Datenbank-Pfad: {self.db_path}")
        logger.info(f"- Backup-Verzeichnis: {self.backup_dir}")

    def get_database_stats(self):
        """Sammelt Statistiken über die Datenbank"""
        try:
            logger.info(f"Sammle Statistiken für Datenbank: {self.db_path}")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # SQL-Abfragen mit Fehlerprüfung
                queries = {
                    'tools': 'SELECT COUNT(*) FROM tools WHERE deleted = 0',
                    'consumables': 'SELECT COUNT(*) FROM consumables WHERE deleted = 0',
                    'workers': 'SELECT COUNT(*) FROM workers WHERE deleted = 0',
                    'active_lendings': 'SELECT COUNT(*) FROM lendings WHERE returned_at IS NULL',
                    'total_consumable_usages': 'SELECT COUNT(*) FROM consumable_usages'
                }
                
                stats = {}
                for key, query in queries.items():
                    try:
                        result = cursor.execute(query).fetchone()
                        stats[key] = result[0] if result else 0
                        logger.info(f"Statistik {key}: {stats[key]}")
                    except sqlite3.Error as e:
                        logger.error(f"Fehler bei SQL-Abfrage für {key}: {str(e)}")
                        stats[key] = 0
                
                return stats
        except Exception as e:
            logger.error(f"Fehler beim Sammeln der Datenbankstatistiken: {str(e)}", exc_info=True)
            return None
        
    def create_backup(self):
        """Erstellt ein Backup der Datenbank"""
        try:
            if not self.db_path.exists():
                logger.error(f"Datenbank nicht gefunden unter: {self.db_path}")
                return False

            # Aktuelles Datum und Uhrzeit für den Backup-Namen
            now = datetime.now()
            backup_name = f"inventory_{now.strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = self.backup_dir / backup_name

            logger.info(f"Erstelle Backup von {self.db_path} nach {backup_path}")

            # Backup erstellen
            shutil.copy2(self.db_path, backup_path)

            # Statistiken sammeln und speichern
            logger.info("Sammle Statistiken für das Backup...")
            stats = self.get_database_stats()
            if stats:
                metadata_path = backup_path.with_suffix('.json')
                logger.info(f"Speichere Metadaten in: {metadata_path}")
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    metadata = {
                        'created_at': now.isoformat(),
                        'database_stats': stats
                    }
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                logger.info(f"Metadaten erfolgreich gespeichert: {metadata}")
            else:
                logger.error("Keine Statistiken verfügbar für das Backup")

            logger.info(f"Backup erfolgreich erstellt: {backup_name}")

            # Alte Backups aufräumen
            self.cleanup_old_backups()
            return True

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups: {str(e)}", exc_info=True)
            return False

    def cleanup_old_backups(self):
        """Löscht Backups, die älter als max_days sind"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.max_days)
            
            for backup_file in self.backup_dir.glob('inventory_*.db'):
                try:
                    # Datum aus dem Dateinamen extrahieren
                    date_str = backup_file.stem.split('_')[1]
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    # Backup und zugehörige Metadaten löschen, wenn es älter als max_days ist
                    if file_date < cutoff_date:
                        backup_file.unlink()
                        metadata_file = backup_file.with_suffix('.json')
                        if metadata_file.exists():
                            metadata_file.unlink()
                        logger.info(f"Altes Backup gelöscht: {backup_file.name}")
                
                except Exception as e:
                    logger.error(f"Fehler beim Löschen des Backups {backup_file}: {str(e)}")

        except Exception as e:
            logger.error(f"Fehler beim Aufräumen der Backups: {str(e)}")

    def list_backups(self):
        """Listet alle verfügbaren Backups auf"""
        try:
            backups = []
            logger.info(f"Suche Backups in: {self.backup_dir}")
            for backup_file in sorted(self.backup_dir.glob('inventory_*.db')):
                backup_info = {
                    'name': backup_file.name,
                    'size': backup_file.stat().st_size,
                    'created': datetime.fromtimestamp(backup_file.stat().st_mtime)
                }
                
                # Metadaten laden, falls vorhanden
                metadata_path = backup_file.with_suffix('.json')
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            backup_info['stats'] = metadata.get('database_stats', {})
                    except Exception as e:
                        logger.error(f"Fehler beim Laden der Metadaten für {backup_file.name}: {str(e)}")
                
                backups.append(backup_info)
            logger.info(f"Gefundene Backups: {len(backups)}")
            return backups
        except Exception as e:
            logger.error(f"Fehler beim Auflisten der Backups: {str(e)}")
            return []

    def restore_backup(self, backup_name):
        """Stellt ein Backup wieder her"""
        try:
            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                logger.error(f"Backup nicht gefunden: {backup_name}")
                return False

            logger.info(f"Stelle Backup wieder her: {backup_name}")
            
            # Stelle sicher, dass das Datenbankverzeichnis existiert
            self.db_path.parent.mkdir(exist_ok=True)
            
            # Schließe alle bestehenden Datenbankverbindungen
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.close()
            except:
                pass
                
            # Kopiere das Backup über die aktuelle Datenbank
            shutil.copy2(backup_path, self.db_path)
            
            # Setze Berechtigungen
            os.chmod(self.db_path, 0o666)
            
            # Teste die wiederhergestellte Datenbank
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    # Teste ob die wichtigsten Tabellen existieren
                    tables = ['tools', 'consumables', 'workers', 'lendings', 'consumable_usages']
                    for table in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        logger.info(f"Tabelle {table} enthält {count} Einträge")
                logger.info(f"Backup erfolgreich wiederhergestellt und getestet: {backup_name}")
                
                # Signalisiere dass ein Neustart nötig ist
                restart_flag = self.base_dir / 'tmp' / 'needs_restart'
                restart_flag.parent.mkdir(exist_ok=True)
                restart_flag.touch()
                
                return True
            except Exception as e:
                logger.error(f"Fehler beim Testen der wiederhergestellten Datenbank: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Fehler bei der Wiederherstellung des Backups: {str(e)}")
            return False

if __name__ == '__main__':
    backup = DatabaseBackup()
    backup.create_backup() 