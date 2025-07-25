#!/bin/bash

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}==== Berechtigungs-Fix für MongoDB-Installation ====${NC}"

# Funktion für Logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Prüfe Root-Rechte
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Dieses Script muss mit Root-Rechten ausgeführt werden!${NC}"
    echo "Verwende: sudo $0"
    exit 1
fi

log "Prüfe und korrigiere Berechtigungen..."

# 1. /tmp Verzeichnis Berechtigungen
log "Korrigiere /tmp Berechtigungen..."
chmod 1777 /tmp
chown root:root /tmp
echo -e "${GREEN}✅ /tmp Berechtigungen korrigiert${NC}"

# 2. /var/tmp Verzeichnis Berechtigungen
log "Korrigiere /var/tmp Berechtigungen..."
chmod 1777 /var/tmp
chown root:root /var/tmp
echo -e "${GREEN}✅ /var/tmp Berechtigungen korrigiert${NC}"

# 3. MongoDB-Verzeichnisse erstellen und Berechtigungen setzen
log "Erstelle MongoDB-Verzeichnisse..."
mkdir -p /var/lib/mongodb
mkdir -p /var/log/mongodb
mkdir -p /etc/mongodb

# MongoDB-Benutzer erstellen (falls nicht vorhanden)
if ! id "mongodb" &>/dev/null; then
    useradd -r -s /bin/false -d /var/lib/mongodb mongodb
    log "MongoDB-Benutzer erstellt"
fi

# Berechtigungen für MongoDB-Verzeichnisse
chown -R mongodb:mongodb /var/lib/mongodb
chown -R mongodb:mongodb /var/log/mongodb
chown -R mongodb:mongodb /etc/mongodb
chmod 755 /var/lib/mongodb
chmod 755 /var/log/mongodb
chmod 755 /etc/mongodb

echo -e "${GREEN}✅ MongoDB-Verzeichnisse und Berechtigungen korrigiert${NC}"

# 4. GPG-Verzeichnis Berechtigungen
log "Korrigiere GPG-Verzeichnis Berechtigungen..."
mkdir -p /usr/share/keyrings
chmod 755 /usr/share/keyrings
chown root:root /usr/share/keyrings
echo -e "${GREEN}✅ GPG-Verzeichnis Berechtigungen korrigiert${NC}"

# 5. APT-Verzeichnis Berechtigungen
log "Korrigiere APT-Verzeichnis Berechtigungen..."
mkdir -p /etc/apt/sources.list.d
chmod 755 /etc/apt/sources.list.d
chown root:root /etc/apt/sources.list.d
echo -e "${GREEN}✅ APT-Verzeichnis Berechtigungen korrigiert${NC}"

# 6. Teste temporäre Verzeichnisse
log "Teste temporäre Verzeichnisse..."
TEMP_DIR=$(mktemp -d)
if [ -d "$TEMP_DIR" ]; then
    echo -e "${GREEN}✅ Temporäres Verzeichnis erstellbar: $TEMP_DIR${NC}"
    rm -rf "$TEMP_DIR"
else
    echo -e "${RED}❌ Temporäres Verzeichnis nicht erstellbar${NC}"
fi

# 7. Teste Download-Berechtigungen
log "Teste Download-Berechtigungen..."
TEMP_FILE=$(mktemp)
if curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o "$TEMP_FILE" 2>/dev/null; then
    echo -e "${GREEN}✅ Download-Berechtigungen funktionieren${NC}"
    rm -f "$TEMP_FILE"
else
    echo -e "${YELLOW}⚠️  Download-Berechtigungen problematisch${NC}"
    echo "Versuche alternative Methode..."
    
    # Alternative: Direkt mit gpg importieren
    if curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg 2>/dev/null; then
        echo -e "${GREEN}✅ MongoDB GPG-Key erfolgreich importiert${NC}"
    else
        echo -e "${RED}❌ MongoDB GPG-Key Import fehlgeschlagen${NC}"
    fi
fi

# 8. GPG-Berechtigungen korrigieren
log "Korrigiere GPG-Berechtigungen..."
if [ -f "/usr/share/keyrings/mongodb-server-7.0.gpg" ]; then
    chmod 644 /usr/share/keyrings/mongodb-server-7.0.gpg
    chown root:root /usr/share/keyrings/mongodb-server-7.0.gpg
    echo -e "${GREEN}✅ GPG-Key Berechtigungen korrigiert${NC}"
else
    echo -e "${YELLOW}⚠️  GPG-Key nicht gefunden, wird beim Download erstellt${NC}"
fi

# 8. System-Informationen anzeigen
log "System-Informationen..."
echo -e "${BLUE}=== System-Info ===${NC}"
echo "Linux Mint Version: $(lsb_release -ds)"
echo "Kernel: $(uname -r)"
echo "Architektur: $(uname -m)"
echo "Aktueller Benutzer: $(whoami)"
echo "EUID: $EUID"
echo ""

# 9. Berechtigungen anzeigen
log "Berechtigungen anzeigen..."
echo -e "${BLUE}=== Wichtige Berechtigungen ===${NC}"
echo "/tmp:"
ls -ld /tmp
echo ""
echo "/var/tmp:"
ls -ld /var/tmp
echo ""
echo "/usr/share/keyrings:"
ls -ld /usr/share/keyrings
echo ""

# 10. Lösungsvorschläge
echo -e "${BLUE}=== Nächste Schritte ===${NC}"
echo -e "${GREEN}✅ Berechtigungen korrigiert!${NC}"
echo ""
echo "Jetzt können Sie das MongoDB-Installationsscript erneut ausführen:"
echo "sudo ./install_scandy_lxc_linux_mint.sh"
echo ""
echo "Falls weiterhin Probleme auftreten, führen Sie das Troubleshooting-Script aus:"
echo "sudo ./troubleshoot_mongodb.sh"
echo ""

echo -e "${GREEN}✅ Berechtigungs-Fix abgeschlossen!${NC}" 