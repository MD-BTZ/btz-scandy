import sys
from pathlib import Path

# Backup-System importieren
sys.path.append(str(Path(__file__).parent.parent.parent))
from backup import DatabaseBackup

# Backup-Manager initialisieren
backup_manager = DatabaseBackup(str(Path(__file__).parent.parent.parent))

# Backup-Verzeichnisse erstellen
backup_dir = Path(__file__).parent.parent.parent / 'backups'
backup_dir.mkdir(exist_ok=True) 