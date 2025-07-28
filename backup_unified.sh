#!/bin/bash

# Vereinheitlichtes Backup-Skript für Scandy
# Verwendet das neue UnifiedBackupManager System

set -e

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Prüfe ob Python-Umgebung aktiviert ist
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [[ -d "venv" ]]; then
        log_info "Aktiviere virtuelles Environment..."
        source venv/bin/activate
    else
        log_error "Virtuelles Environment nicht gefunden!"
        exit 1
    fi
fi

# Funktion zum Erstellen eines Backups
create_backup() {
    local include_media=${1:-true}
    local compress=${2:-true}
    
    log_info "Erstelle vereinheitlichtes Backup..."
    log_info "Medien einschließen: $include_media"
    log_info "Komprimierung: $compress"
    
    python3 -c "
import sys
sys.path.append('.')
from app.utils.unified_backup_manager import unified_backup_manager

# String zu Boolean konvertieren
include_media_bool = '$include_media' == 'true'
compress_bool = '$compress' == 'true'

result = unified_backup_manager.create_backup(
    include_media=include_media_bool,
    compress=compress_bool
)

if result:
    print(f'SUCCESS: {result}')
else:
    print('ERROR: Backup fehlgeschlagen')
    sys.exit(1)
"
}

# Funktion zum Wiederherstellen eines Backups
restore_backup() {
    local backup_filename=$1
    local include_media=${2:-true}
    
    log_info "Stelle Backup wieder her: $backup_filename"
    log_info "Medien wiederherstellen: $include_media"
    
    python3 -c "
import sys
sys.path.append('.')
from app.utils.unified_backup_manager import unified_backup_manager

# String zu Boolean konvertieren
include_media_bool = '$include_media' == 'true'

result = unified_backup_manager.restore_backup(
    '$backup_filename',
    include_media=include_media_bool
)

if result:
    print('SUCCESS: Backup erfolgreich wiederhergestellt')
else:
    print('ERROR: Backup-Wiederherstellung fehlgeschlagen')
    sys.exit(1)
"
}

# Funktion zum Importieren eines JSON-Backups
import_json_backup() {
    local json_file=$1
    
    log_info "Importiere JSON-Backup: $json_file"
    
    python3 -c "
import sys
sys.path.append('.')
from app.utils.unified_backup_manager import unified_backup_manager

result = unified_backup_manager.import_json_backup('$json_file')

if result:
    print('SUCCESS: JSON-Backup erfolgreich importiert')
else:
    print('ERROR: JSON-Backup-Import fehlgeschlagen')
    sys.exit(1)
"
}

# Funktion zum Auflisten von Backups
list_backups() {
    log_info "Verfügbare Backups:"
    
    python3 -c "
import sys
sys.path.append('.')
from app.utils.unified_backup_manager import unified_backup_manager

backups = unified_backup_manager.list_backups()

if not backups:
    print('Keine Backups gefunden')
else:
    print('\\n{:<50} {:<15} {:<25} {:<10}'.format('Dateiname', 'Größe', 'Erstellt', 'Version'))
    print('-' * 100)
    for backup in backups:
        print('{:<50} {:<15} {:<25} {:<10}'.format(
            backup['filename'][:49],
            backup['size'],
            backup['created_at'][:24],
            backup['version']
        ))
"
}

# Funktion zum Löschen eines Backups
delete_backup() {
    local backup_filename=$1
    
    log_warning "Lösche Backup: $backup_filename"
    
    if [[ -f "backups/$backup_filename" ]]; then
        rm "backups/$backup_filename"
        log_success "Backup gelöscht: $backup_filename"
    else
        log_error "Backup nicht gefunden: $backup_filename"
        exit 1
    fi
}

# Funktion zum Testen eines Backups
test_backup() {
    local backup_filename=$1
    
    log_info "Teste Backup: $backup_filename"
    
    python3 -c "
import sys
import zipfile
from pathlib import Path

backup_path = Path('backups/$backup_filename')

if not backup_path.exists():
    print('ERROR: Backup nicht gefunden')
    sys.exit(1)

try:
    with zipfile.ZipFile(backup_path, 'r') as zipf:
        # Prüfe Metadaten
        if 'backup_metadata.json' in zipf.namelist():
            import json
            metadata_content = zipf.read('backup_metadata.json')
            metadata = json.loads(metadata_content.decode('utf-8'))
            print(f'SUCCESS: Backup ist gültig')
            print(f'  Name: {metadata.get(\"backup_name\", \"Unbekannt\")}')
            print(f'  Version: {metadata.get(\"version\", \"1.0\")}')
            print(f'  Enthält Medien: {metadata.get(\"includes_media\", False)}')
        else:
            print('WARNING: Keine Metadaten gefunden')
        
        # Prüfe Struktur
        files = zipf.namelist()
        if any(f.startswith('mongodb/') for f in files):
            print('  ✅ MongoDB-Backup gefunden')
        if any(f.startswith('media/') for f in files):
            print('  ✅ Medien-Backup gefunden')
        if any(f.startswith('config/') for f in files):
            print('  ✅ Konfigurations-Backup gefunden')
            
except Exception as e:
    print(f'ERROR: Backup ist beschädigt: {e}')
    sys.exit(1)
"
}

# Hauptfunktion
main() {
    case "${1:-help}" in
        "create")
            create_backup "${2:-true}" "${3:-true}"
            ;;
        "restore")
            if [[ -z "$2" ]]; then
                log_error "Backup-Dateiname erforderlich"
                echo "Verwendung: $0 restore <backup_filename> [include_media]"
                exit 1
            fi
            restore_backup "$2" "${3:-true}"
            ;;
        "import")
            if [[ -z "$2" ]]; then
                log_error "JSON-Backup-Datei erforderlich"
                echo "Verwendung: $0 import <json_file>"
                exit 1
            fi
            import_json_backup "$2"
            ;;
        "list")
            list_backups
            ;;
        "delete")
            if [[ -z "$2" ]]; then
                log_error "Backup-Dateiname erforderlich"
                echo "Verwendung: $0 delete <backup_filename>"
                exit 1
            fi
            delete_backup "$2"
            ;;
        "test")
            if [[ -z "$2" ]]; then
                log_error "Backup-Dateiname erforderlich"
                echo "Verwendung: $0 test <backup_filename>"
                exit 1
            fi
            test_backup "$2"
            ;;
        "help"|*)
            echo "Vereinheitlichtes Backup-System für Scandy"
            echo ""
            echo "Verwendung: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  create [include_media] [compress]  - Erstellt ein neues Backup"
            echo "  restore <filename> [include_media] - Stellt ein Backup wieder her"
            echo "  import <json_file>                 - Importiert ein JSON-Backup"
            echo "  list                               - Listet alle Backups auf"
            echo "  delete <filename>                  - Löscht ein Backup"
            echo "  test <filename>                    - Testet ein Backup"
            echo "  help                               - Zeigt diese Hilfe"
            echo ""
            echo "Beispiele:"
            echo "  $0 create                          # Backup mit Medien"
            echo "  $0 create false                    # Backup ohne Medien"
            echo "  $0 restore backup_20241201.zip     # Backup wiederherstellen"
            echo "  $0 import old_backup.json          # JSON-Backup importieren"
            echo "  $0 list                            # Backups auflisten"
            ;;
    esac
}

# Skript ausführen
main "$@" 