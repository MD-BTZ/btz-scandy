#!/bin/bash

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}==== Repository-Fix für Linux Mint 22.x ====${NC}"

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

log "Behebe Repository-Problem für Linux Mint 22.x..."

# 1. Lösche vorhandene Repository-Datei
log "Lösche vorhandene Repository-Datei..."
rm -f /etc/apt/sources.list.d/mongodb-org-7.0.list

# 2. Erstelle neue Repository-Datei mit jammy (Ubuntu 22.04)
log "Erstelle neue Repository-Datei mit jammy..."
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list

# 3. Überprüfe GPG-Key
log "Überprüfe GPG-Key..."
if [ -f "/usr/share/keyrings/mongodb-server-7.0.gpg" ]; then
    log "GPG-Key existiert"
else
    log "${YELLOW}GPG-Key nicht gefunden, erstelle neu..."
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
    chmod 644 /usr/share/keyrings/mongodb-server-7.0.gpg
    chown root:root /usr/share/keyrings/mongodb-server-7.0.gpg
fi

# 4. Teste Repository
log "Teste Repository..."
apt update > /dev/null 2>&1
if [ $? -eq 0 ]; then
    log "${GREEN}✅ Repository funktioniert${NC}"
else
    log "${RED}❌ Repository funktioniert nicht${NC}"
    log "Versuche alternative Methode..."
    
    # Alternative: Verwende focal (Ubuntu 20.04) als Fallback
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list
    
    apt update > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        log "${GREEN}✅ Repository funktioniert mit focal${NC}"
    else
        log "${RED}❌ Auch focal funktioniert nicht${NC}"
        exit 1
    fi
fi

# 5. Installiere MongoDB
log "Installiere MongoDB..."
apt install -y mongodb-org

# 6. Starte MongoDB
log "Starte MongoDB..."
systemctl enable mongod
systemctl start mongod

# 7. Warte auf MongoDB-Start
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

# 8. Teste MongoDB-Verbindung
log "Teste MongoDB-Verbindung..."
if mongosh --eval "db.adminCommand('ping')" --quiet 2>/dev/null; then
    log "${GREEN}✅ MongoDB-Verbindung erfolgreich${NC}"
else
    log "${YELLOW}⚠️  MongoDB-Verbindung fehlgeschlagen (möglicherweise noch nicht bereit)${NC}"
fi

# 9. Abschluss
echo -e "${GREEN}==== Repository-Fix abgeschlossen! ====${NC}"
echo -e "${GREEN}✅ Repository korrigiert${NC}"
echo -e "${GREEN}✅ MongoDB installiert und gestartet${NC}"
echo -e "${GREEN}✅ MongoDB läuft auf localhost:27017${NC}"

# 10. Status anzeigen
echo -e "${BLUE}=== MongoDB-Status ===${NC}"
systemctl status mongod --no-pager -l

echo -e "${GREEN}✅ Repository-Fix erfolgreich abgeschlossen!${NC}" 