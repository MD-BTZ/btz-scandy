#!/bin/bash

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}==== MongoDB Troubleshooting für Linux Mint ====${NC}"

# Funktion für Logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# 1. System-Informationen
log "Sammle System-Informationen..."
echo -e "${BLUE}=== System-Informationen ===${NC}"
echo "Linux Mint Version: $(lsb_release -ds)"
echo "Kernel: $(uname -r)"
echo "Architektur: $(uname -m)"
echo ""

# 2. MongoDB-Status prüfen
log "Prüfe MongoDB-Status..."
echo -e "${BLUE}=== MongoDB-Status ===${NC}"
if systemctl is-active --quiet mongod; then
    echo -e "${GREEN}✅ MongoDB läuft${NC}"
    systemctl status mongod --no-pager -l
else
    echo -e "${RED}❌ MongoDB läuft nicht${NC}"
    systemctl status mongod --no-pager -l
fi
echo ""

# 3. MongoDB-Logs prüfen
log "Prüfe MongoDB-Logs..."
echo -e "${BLUE}=== MongoDB-Logs (letzte 20 Zeilen) ===${NC}"
journalctl -u mongod -n 20 --no-pager
echo ""

# 4. Port-Verfügbarkeit prüfen
log "Prüfe Port-Verfügbarkeit..."
echo -e "${BLUE}=== Port-Status ===${NC}"
if netstat -tlnp | grep :27017; then
    echo -e "${GREEN}✅ Port 27017 ist belegt${NC}"
else
    echo -e "${RED}❌ Port 27017 ist nicht belegt${NC}"
fi
echo ""

# 5. MongoDB-Prozess prüfen
log "Prüfe MongoDB-Prozesse..."
echo -e "${BLUE}=== MongoDB-Prozesse ===${NC}"
ps aux | grep -E "(mongod|mongo)" | grep -v grep || echo "Keine MongoDB-Prozesse gefunden"
echo ""

# 6. MongoDB-Verbindung testen
log "Teste MongoDB-Verbindung..."
echo -e "${BLUE}=== MongoDB-Verbindungstest ===${NC}"
if command -v mongosh &> /dev/null; then
    if mongosh --eval "db.adminCommand('ping')" --quiet; then
        echo -e "${GREEN}✅ MongoDB-Verbindung erfolgreich${NC}"
    else
        echo -e "${RED}❌ MongoDB-Verbindung fehlgeschlagen${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  mongosh nicht gefunden${NC}"
fi
echo ""

# 7. MongoDB-Konfiguration prüfen
log "Prüfe MongoDB-Konfiguration..."
echo -e "${BLUE}=== MongoDB-Konfiguration ===${NC}"
if [ -f "/etc/mongod.conf" ]; then
    echo "MongoDB-Konfigurationsdatei gefunden:"
    cat /etc/mongod.conf | grep -E "(port|bindIp|dbPath)" | head -10
else
    echo -e "${YELLOW}⚠️  MongoDB-Konfigurationsdatei nicht gefunden${NC}"
fi
echo ""

# 8. Datenbank-Verzeichnis prüfen
log "Prüfe Datenbank-Verzeichnis..."
echo -e "${BLUE}=== Datenbank-Verzeichnis ===${NC}"
DB_PATH="/var/lib/mongodb"
if [ -d "$DB_PATH" ]; then
    echo "Datenbank-Verzeichnis: $DB_PATH"
    ls -la "$DB_PATH" | head -5
    echo "Verfügbarer Speicherplatz:"
    df -h "$DB_PATH"
else
    echo -e "${YELLOW}⚠️  Datenbank-Verzeichnis nicht gefunden${NC}"
fi
echo ""

# 9. Berechtigungen prüfen
log "Prüfe Berechtigungen..."
echo -e "${BLUE}=== Berechtigungen ===${NC}"
if [ -d "$DB_PATH" ]; then
    echo "Datenbank-Verzeichnis Berechtigungen:"
    ls -ld "$DB_PATH"
    echo ""
    echo "MongoDB-Benutzer:"
    id mongodb 2>/dev/null || echo "MongoDB-Benutzer nicht gefunden"
fi
echo ""

# 10. Repository-Status prüfen
log "Prüfe MongoDB-Repository..."
echo -e "${BLUE}=== MongoDB-Repository ===${NC}"
if [ -f "/etc/apt/sources.list.d/mongodb-org-7.0.list" ]; then
    echo "MongoDB-Repository gefunden:"
    cat /etc/apt/sources.list.d/mongodb-org-7.0.list
else
    echo -e "${YELLOW}⚠️  MongoDB-Repository nicht gefunden${NC}"
fi
echo ""

# 11. GPG-Key prüfen
log "Prüfe MongoDB GPG-Key..."
echo -e "${BLUE}=== MongoDB GPG-Key ===${NC}"
if [ -f "/usr/share/keyrings/mongodb-server-7.0.gpg" ]; then
    echo -e "${GREEN}✅ MongoDB GPG-Key gefunden${NC}"
else
    echo -e "${RED}❌ MongoDB GPG-Key nicht gefunden${NC}"
fi
echo ""

# 12. Netzwerk-Konnektivität prüfen
log "Prüfe Netzwerk-Konnektivität..."
echo -e "${BLUE}=== Netzwerk-Konnektivität ===${NC}"
if ping -c 1 repo.mongodb.org &> /dev/null; then
    echo -e "${GREEN}✅ MongoDB-Repository erreichbar${NC}"
else
    echo -e "${RED}❌ MongoDB-Repository nicht erreichbar${NC}"
fi
echo ""

# 13. Lösungsvorschläge
echo -e "${BLUE}=== Lösungsvorschläge ===${NC}"

if ! systemctl is-active --quiet mongod; then
    echo -e "${YELLOW}🔧 MongoDB starten:${NC}"
    echo "sudo systemctl start mongod"
    echo "sudo systemctl enable mongod"
    echo ""
fi

if ! command -v mongosh &> /dev/null; then
    echo -e "${YELLOW}🔧 MongoDB Shell installieren:${NC}"
    echo "sudo apt update"
    echo "sudo apt install mongodb-mongosh"
    echo ""
fi

if [ ! -f "/etc/apt/sources.list.d/mongodb-org-7.0.list" ]; then
    echo -e "${YELLOW}🔧 MongoDB-Repository hinzufügen:${NC}"
    echo "curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor"
    echo "echo 'deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse' | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list"
    echo "sudo apt update"
    echo "sudo apt install mongodb-org"
    echo ""
fi

echo -e "${YELLOW}🔧 Allgemeine Troubleshooting-Schritte:${NC}"
echo "1. MongoDB neu starten: sudo systemctl restart mongod"
echo "2. Logs prüfen: sudo journalctl -u mongod -f"
echo "3. Konfiguration prüfen: sudo nano /etc/mongod.conf"
echo "4. Berechtigungen korrigieren: sudo chown -R mongodb:mongodb /var/lib/mongodb"
echo "5. Firewall prüfen: sudo ufw status"
echo ""

echo -e "${GREEN}✅ Troubleshooting abgeschlossen${NC}" 