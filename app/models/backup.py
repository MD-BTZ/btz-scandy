import os
import shutil
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseBackup:
    def __init__(self, base_dir, db_path, backup_dir):
        """Initialisiert den DatabaseBackup mit den notwendigen Pfaden."""
        self.base_dir = base_dir
        self.db_path = db_path
        self.backup_dir = backup_dir

        logger.info("DatabaseBackup initialisiert mit:")
        logger.info(f"- Basis-Verzeichnis: {base_dir}")
        logger.info(f"- Datenbank-Pfad: {db_path}")
        logger.info(f"- Backup-Verzeichnis: {backup_dir}")

        # Stelle sicher, dass das Backup-Verzeichnis existiert
        os.makedirs(backup_dir, exist_ok=True)

    def create_backup(self):
        """Erstellt ein Backup der Datenbank."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"backup_{timestamp}.db")
            shutil.copy2(self.db_path, backup_file)
            logger.info(f"Backup erstellt: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
            return False

    def restore_backup(self, backup_file):
        """Stellt ein Backup wieder her."""
        try:
            if not os.path.exists(backup_file):
                logger.error(f"Backup-Datei nicht gefunden: {backup_file}")
                return False
            self.create_backup()
            shutil.copy2(backup_file, self.db_path)
            logger.info(f"Backup wiederhergestellt: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen des Backups: {str(e)}")
            return False

    def list_backups(self):
        """Listet alle verfügbaren Backups auf."""
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.startswith("backup_") and file.endswith(".db"):
                    full_path = os.path.join(self.backup_dir, file)
                    backups.append({
                        'filename': file,
                        'path': full_path,
                        'size': os.path.getsize(full_path),
                        'created': datetime.fromtimestamp(os.path.getctime(full_path))
                    })
            return sorted(backups, key=lambda x: x['created'], reverse=True)
        except Exception as e:
            logger.error(f"Fehler beim Auflisten der Backups: {str(e)}")
            return []

    def cleanup_old_backups(self, keep_last=5):
        """Löscht alte Backups und behält nur die letzten X Backups."""
        try:
            backups = self.list_backups()
            if len(backups) > keep_last:
                for backup in backups[keep_last:]:
                    os.remove(backup['path'])
                    logger.info(f"Altes Backup gelöscht: {backup['filename']}")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Aufräumen alter Backups: {str(e)}")
            return False
