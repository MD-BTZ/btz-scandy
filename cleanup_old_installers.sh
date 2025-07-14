#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Cleanup: Alte Installationsskripte archivieren"
echo "========================================"
echo

# Erstelle Archiv-Verzeichnis
ARCHIVE_DIR="old_installers_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$ARCHIVE_DIR"

echo -e "${BLUE}📁 Erstelle Archiv: $ARCHIVE_DIR${NC}"

# Liste der alten Installationsskripte
OLD_INSTALLERS=(
    "install.sh"
    "install.bat"
    "install_production.sh"
    "install_production.bat"
    "setup_instance.sh"
)

# Liste der alten Start/Stop-Skripte
OLD_MANAGEMENT=(
    "start_all.sh"
    "start_all.bat"
    "stop_all.sh"
    "stop_all.bat"
    "start_standard.sh"
    "stop_standard.sh"
    "start_instance2.sh"
    "stop_instance2.sh"
    "start_dynamic.sh"
    "stop_dynamic.sh"
    "start_dynamic.py"
    "stop_dynamic.py"
    "start_dynamic.bat"
    "stop_dynamic.bat"
    "start_btz.sh"
    "start_btz.bat"
    "start_verwaltung.sh"
    "start_verwaltung.bat"
    "start_werkstatt.sh"
    "start_werkstatt.bat"
    "status_standard.sh"
    "status_instance2.sh"
    "status_production.sh"
    "status_production.bat"
)

# Liste der alten docker-compose Dateien
OLD_DOCKER_COMPOSE=(
    "docker-compose-instance2.yml"
    "docker-compose.btz.yml"
    "docker-compose.dynamic.yml"
    "docker-compose.verwaltung.yml"
    "docker-compose.werkstatt.yml"
)

# Liste der alten env-Dateien
OLD_ENV=(
    "env_instance2.example"
)

# Verschiebe Installationsskripte
echo -e "${BLUE}📦 Verschiebe Installationsskripte...${NC}"
for file in "${OLD_INSTALLERS[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo -e "${GREEN}✅ $file → $ARCHIVE_DIR/${NC}"
    else
        echo -e "${YELLOW}⚠️  $file nicht gefunden${NC}"
    fi
done

# Verschiebe Management-Skripte
echo -e "${BLUE}📦 Verschiebe Management-Skripte...${NC}"
for file in "${OLD_MANAGEMENT[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo -e "${GREEN}✅ $file → $ARCHIVE_DIR/${NC}"
    else
        echo -e "${YELLOW}⚠️  $file nicht gefunden${NC}"
    fi
done

# Verschiebe docker-compose Dateien
echo -e "${BLUE}📦 Verschiebe docker-compose Dateien...${NC}"
for file in "${OLD_DOCKER_COMPOSE[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo -e "${GREEN}✅ $file → $ARCHIVE_DIR/${NC}"
    else
        echo -e "${YELLOW}⚠️  $file nicht gefunden${NC}"
    fi
done

# Verschiebe env-Dateien
echo -e "${BLUE}📦 Verschiebe env-Dateien...${NC}"
for file in "${OLD_ENV[@]}"; do
    if [ -f "$file" ]; then
        mv "$file" "$ARCHIVE_DIR/"
        echo -e "${GREEN}✅ $file → $ARCHIVE_DIR/${NC}"
    else
        echo -e "${YELLOW}⚠️  $file nicht gefunden${NC}"
    fi
done

# Erstelle README im Archiv
cat > "$ARCHIVE_DIR/README.md" << 'EOF'
# Archiv: Alte Installationsskripte

Diese Dateien wurden durch das neue `install_unified.sh` Skript ersetzt.

## Migration

### Alte Skripte → Neue Verwendung

| Alt | Neu |
|-----|-----|
| `./install.sh` | `./install_unified.sh` |
| `./install_production.sh` | `./install_unified.sh -f` |
| `./setup_instance.sh` | `./install_unified.sh -n [NAME]` |
| `./start_all.sh` | `./manage.sh start` |
| `./stop_all.sh` | `./manage.sh stop` |
| `./start_standard.sh` | `./manage.sh start` |
| `./stop_standard.sh` | `./manage.sh stop` |

## Features des neuen Skripts

- ✅ Variable Ports für App und Datenbank
- ✅ Automatische Port-Berechnung
- ✅ Mehrere Instances parallel
- ✅ Sichere Passwort-Generierung
- ✅ Update-Modus ohne Datenverlust
- ✅ Port-Konflikt-Prüfung
- ✅ Einheitliches Management

## Wiederherstellung

Falls Sie die alten Skripte benötigen:

```bash
# Alle Dateien wiederherstellen
cp -r old_installers_*/ .

# Oder einzelne Dateien
cp old_installers_*/install.sh .
cp old_installers_*/start_all.sh .
```

## Dokumentation

Siehe `README_UNIFIED_INSTALLER.md` für die vollständige Dokumentation des neuen Installers.
EOF

echo
echo "========================================"
echo -e "${GREEN}✅ Cleanup abgeschlossen!${NC}"
echo "========================================"
echo
echo -e "${BLUE}📁 Archiv erstellt:${NC} $ARCHIVE_DIR"
echo -e "${BLUE}📖 README erstellt:${NC} $ARCHIVE_DIR/README.md"
echo
echo -e "${BLUE}🚀 Nächste Schritte:${NC}"
echo "1. Verwende das neue Skript: ./install_unified.sh"
echo "2. Siehe Dokumentation: README_UNIFIED_INSTALLER.md"
echo "3. Bei Problemen: Dateien aus $ARCHIVE_DIR wiederherstellen"
echo
echo -e "${YELLOW}⚠️  Wichtig: Die alten Skripte sind archiviert, nicht gelöscht!${NC}" 