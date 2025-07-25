#!/bin/bash

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}==== GPG-Berechtigungs-Fix für MongoDB ====${NC}"

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

log "Behebe GPG-Berechtigungsprobleme..."

# 1. Lösche vorhandene problematische GPG-Keys
log "Lösche vorhandene GPG-Keys..."
rm -f /usr/share/keyrings/mongodb-server-7.0.gpg
rm -f /etc/apt/sources.list.d/mongodb-org-7.0.list

# 2. Korrigiere GPG-Verzeichnis Berechtigungen
log "Korrigiere GPG-Verzeichnis Berechtigungen..."
mkdir -p /usr/share/keyrings
chmod 755 /usr/share/keyrings
chown root:root /usr/share/keyrings

# 3. Korrigiere APT-Verzeichnis Berechtigungen
log "Korrigiere APT-Verzeichnis Berechtigungen..."
mkdir -p /etc/apt/sources.list.d
chmod 755 /etc/apt/sources.list.d
chown root:root /etc/apt/sources.list.d

# 4. Korrigiere temporäre Verzeichnisse
log "Korrigiere temporäre Verzeichnisse..."
chmod 1777 /tmp
chmod 1777 /var/tmp
chown root:root /tmp
chown root:root /var/tmp

# 5. Teste GPG-Funktionalität
log "Teste GPG-Funktionalität..."
if gpg --version > /dev/null 2>&1; then
    echo -e "${GREEN}✅ GPG funktioniert${NC}"
else
    echo -e "${RED}❌ GPG funktioniert nicht${NC}"
    exit 1
fi

# 6. Manueller GPG-Key-Download und Import
log "Lade MongoDB GPG-Key manuell herunter..."

# Erstelle temporäres Verzeichnis
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download GPG-Key
log "Download GPG-Key..."
if curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o server-7.0.asc; then
    log "GPG-Key erfolgreich heruntergeladen"
else
    log "${RED}Fehler beim Download des GPG-Keys${NC}"
    cd /
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Überprüfe GPG-Key
log "Überprüfe GPG-Key..."
if gpg --list-packets server-7.0.asc > /dev/null 2>&1; then
    log "GPG-Key ist gültig"
else
    log "${RED}GPG-Key ist ungültig${NC}"
    cd /
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Importiere GPG-Key mit expliziten Berechtigungen
log "Importiere GPG-Key..."
if gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg server-7.0.asc; then
    log "GPG-Key erfolgreich importiert"
else
    log "${RED}Fehler beim Import des GPG-Keys${NC}"
    cd /
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Setze korrekte Berechtigungen
chmod 644 /usr/share/keyrings/mongodb-server-7.0.gpg
chown root:root /usr/share/keyrings/mongodb-server-7.0.gpg

# 7. Überprüfe GPG-Key
log "Überprüfe importierten GPG-Key..."
if [ -f "/usr/share/keyrings/mongodb-server-7.0.gpg" ]; then
    log "GPG-Key existiert"
    ls -la /usr/share/keyrings/mongodb-server-7.0.gpg
else
    log "${RED}GPG-Key wurde nicht erstellt${NC}"
    cd /
    rm -rf "$TEMP_DIR"
    exit 1
fi

# 8. Teste GPG-Key-Verifizierung
log "Teste GPG-Key-Verifizierung..."
if gpg --no-default-keyring --keyring /usr/share/keyrings/mongodb-server-7.0.gpg --list-keys > /dev/null 2>&1; then
    log "GPG-Key-Verifizierung erfolgreich"
else
    log "${YELLOW}Warnung: GPG-Key-Verifizierung fehlgeschlagen${NC}"
fi

# 9. Aufräumen
cd /
rm -rf "$TEMP_DIR"

# 10. Erstelle MongoDB Repository
log "Erstelle MongoDB Repository..."

# Erkenne Linux Mint Version
MINT_VERSION=$(lsb_release -rs)
log "Linux Mint Version erkannt: $MINT_VERSION"

# Bestimme Ubuntu-Codename
case $MINT_VERSION in
    "22.1"|"22.2"|"22.3")
        # Linux Mint 22.x verwendet Ubuntu 22.04 (jammy) Repository, da noble noch nicht existiert
        UBUNTU_CODENAME="jammy"
        log "${YELLOW}Hinweis: Linux Mint 22.x verwendet Ubuntu 22.04 (jammy) Repository${NC}"
        ;;
    "21.3"|"21.2"|"21.1")
        UBUNTU_CODENAME="jammy"
        ;;
    "20.3"|"20.2"|"20.1")
        UBUNTU_CODENAME="focal"
        ;;
    *)
        UBUNTU_CODENAME="jammy"
        log "${YELLOW}Warnung: Unbekannte Linux Mint Version, verwende jammy als Fallback${NC}"
        ;;
esac

log "Verwende Ubuntu-Codename: $UBUNTU_CODENAME"

# Erstelle Repository-Datei
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $UBUNTU_CODENAME/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list

# 11. Teste Repository
log "Teste Repository..."
apt update > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log "${GREEN}✅ Repository funktioniert${NC}"
else
    log "${RED}❌ Repository funktioniert nicht${NC}"
fi

# 12. Abschluss
echo -e "${GREEN}==== GPG-Berechtigungs-Fix abgeschlossen! ====${NC}"
echo -e "${GREEN}✅ GPG-Key erfolgreich importiert${NC}"
echo -e "${GREEN}✅ Repository erstellt${NC}"
echo ""
echo "Jetzt können Sie die MongoDB-Installation fortsetzen:"
echo "sudo ./install_scandy_lxc_linux_mint.sh"
echo ""
echo "Oder verwenden Sie das manuelle Installationsscript:"
echo "sudo ./manual_mongodb_install.sh"
echo ""

echo -e "${GREEN}✅ GPG-Berechtigungs-Fix erfolgreich abgeschlossen!${NC}" 