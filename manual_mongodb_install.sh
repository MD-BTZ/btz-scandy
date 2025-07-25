#!/bin/bash

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}==== Manuelle MongoDB-Installation für Linux Mint ====${NC}"

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

log "Starte manuelle MongoDB-Installation..."

# 1. System aktualisieren
log "Aktualisiere System..."
apt update && apt upgrade -y

# 2. Basis-Pakete installieren
log "Installiere Basis-Pakete..."
apt install -y python3 python3-pip python3-venv git nginx curl gnupg lsb-release wget software-properties-common

# 3. MongoDB manuell installieren
log "Installiere MongoDB manuell..."

# Erkenne Linux Mint Version
MINT_VERSION=$(lsb_release -rs)
log "Linux Mint Version erkannt: $MINT_VERSION"

# Bestimme Ubuntu-Codename
case $MINT_VERSION in
    "22.1"|"22.2"|"22.3")
        UBUNTU_CODENAME="noble"
        ;;
    "21.3"|"21.2"|"21.1")
        UBUNTU_CODENAME="jammy"
        ;;
    "20.3"|"20.2"|"20.1")
        UBUNTU_CODENAME="focal"
        ;;
    *)
        UBUNTU_CODENAME="noble"
        log "${YELLOW}Warnung: Unbekannte Linux Mint Version, verwende noble als Fallback${NC}"
        ;;
esac

log "Verwende Ubuntu-Codename: $UBUNTU_CODENAME"

# 4. MongoDB GPG-Key manuell hinzufügen
log "Füge MongoDB GPG-Key manuell hinzu..."

# Lösche vorhandene GPG-Keys
rm -f /usr/share/keyrings/mongodb-server-7.0.gpg
rm -f /etc/apt/sources.list.d/mongodb-org-7.0.list

# Erstelle temporäres Verzeichnis
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Download GPG-Key
log "Lade MongoDB GPG-Key herunter..."
if curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o server-7.0.asc; then
    log "GPG-Key erfolgreich heruntergeladen"
else
    log "${RED}Fehler beim Download des GPG-Keys${NC}"
    exit 1
fi

# Importiere GPG-Key
log "Importiere GPG-Key..."
if gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg server-7.0.asc; then
    log "GPG-Key erfolgreich importiert"
else
    log "${RED}Fehler beim Import des GPG-Keys${NC}"
    exit 1
fi

# Setze Berechtigungen
chmod 644 /usr/share/keyrings/mongodb-server-7.0.gpg
chown root:root /usr/share/keyrings/mongodb-server-7.0.gpg

# 5. MongoDB Repository hinzufügen
log "Füge MongoDB Repository hinzu..."
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $UBUNTU_CODENAME/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list

# 6. System aktualisieren und MongoDB installieren
log "Aktualisiere Paketlisten und installiere MongoDB..."
apt update
apt install -y mongodb-org

# 7. Aufräumen
cd /
rm -rf "$TEMP_DIR"

# 8. MongoDB-Benutzer erstellen (falls nicht vorhanden)
if ! id "mongodb" &>/dev/null; then
    useradd -r -s /bin/false -d /var/lib/mongodb mongodb
    log "MongoDB-Benutzer erstellt"
fi

# 9. MongoDB-Verzeichnisse erstellen
log "Erstelle MongoDB-Verzeichnisse..."
mkdir -p /var/lib/mongodb
mkdir -p /var/log/mongodb
mkdir -p /etc/mongodb

# 10. Berechtigungen setzen
log "Setze Berechtigungen..."
chown -R mongodb:mongodb /var/lib/mongodb
chown -R mongodb:mongodb /var/log/mongodb
chown -R mongodb:mongodb /etc/mongodb
chmod 755 /var/lib/mongodb
chmod 755 /var/log/mongodb
chmod 755 /etc/mongodb

# 11. MongoDB starten
log "Starte MongoDB..."
systemctl enable mongod
systemctl start mongod

# 12. Warte auf MongoDB-Start
log "Warte auf MongoDB-Start..."
for i in {1..30}; do
    if systemctl is-active --quiet mongod; then
        log "MongoDB läuft"
        break
    fi
    if [ $i -eq 30 ]; then
        log "${RED}Fehler: MongoDB konnte nicht gestartet werden${NC}"
        systemctl status mongod
        exit 1
    fi
    sleep 2
done

# 13. MongoDB-Authentifizierung einrichten
log "Richte MongoDB-Authentifizierung ein..."
sleep 5

# Erstelle Admin-Benutzer
mongosh --eval "
use admin
db.createUser({
  user: 'admin',
  pwd: 'scandy123456',
  roles: [
    { role: 'userAdminAnyDatabase', db: 'admin' },
    { role: 'readWriteAnyDatabase', db: 'admin' },
    { role: 'dbAdminAnyDatabase', db: 'admin' }
  ]
})
" || log "${YELLOW}Warnung: MongoDB-Authentifizierung konnte nicht eingerichtet werden${NC}"

# 14. Teste Verbindung
log "Teste MongoDB-Verbindung..."
if mongosh --eval "db.adminCommand('ping')" --quiet; then
    log "${GREEN}✅ MongoDB-Verbindung erfolgreich${NC}"
else
    log "${RED}❌ MongoDB-Verbindung fehlgeschlagen${NC}"
fi

# 15. Abschluss
echo -e "${GREEN}==== Manuelle MongoDB-Installation abgeschlossen! ====${NC}"
echo -e "${GREEN}✅ MongoDB läuft auf localhost:27017${NC}"
echo -e "${GREEN}✅ Admin-Benutzer: admin / scandy123456${NC}"
echo -e "${YELLOW}⚠️  WICHTIG: Ändern Sie das Standard-Passwort!${NC}"

# 16. Status anzeigen
echo -e "${BLUE}=== MongoDB-Status ===${NC}"
systemctl status mongod --no-pager -l

echo -e "${GREEN}✅ Manuelle Installation erfolgreich abgeschlossen!${NC}" 