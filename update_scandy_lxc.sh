#!/bin/bash
set -e

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================"
echo "Scandy LXC Update Script"
echo "========================================"
echo "Dieses Skript aktualisiert die Scandy-App:"
echo "- ✅ Codebase wird aktualisiert"
echo "- ✅ Python-Abhängigkeiten werden aktualisiert"
echo "- ✅ App wird neugestartet"
echo "- 🔒 MongoDB bleibt unverändert"
echo "- 💾 Alle Daten bleiben erhalten"
echo "- 🔐 .env-Einstellungen bleiben erhalten"
echo "========================================"
echo "${NC}"

# Prüfe ob wir als root laufen
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Dieses Script muss als root ausgeführt werden!${NC}"
    echo "Verwende: sudo ./update_scandy_lxc.sh"
    exit 1
fi

# Prüfe ob Scandy installiert ist
if [ ! -d "/opt/scandy" ]; then
    echo -e "${RED}❌ ERROR: Scandy ist nicht installiert!${NC}"
    echo "Bitte führen Sie zuerst ./install_scandy_lxc.sh aus."
    exit 1
fi

# Sichere .env-Datei vor dem Update
if [ -f "/opt/scandy/.env" ]; then
    echo -e "${BLUE}💾 Sichere .env-Datei...${NC}"
    cp /opt/scandy/.env /opt/scandy/.env.backup
    echo -e "${GREEN}✅ .env gesichert als .env.backup${NC}"
fi

# Sichere wichtige Daten
echo -e "${BLUE}💾 Sichere wichtige Daten...${NC}"
if [ -d "/opt/scandy/app/uploads" ]; then
    cp -r /opt/scandy/app/uploads /opt/scandy/app/uploads.backup
    echo -e "${GREEN}✅ Uploads gesichert${NC}"
fi

if [ -d "/opt/scandy/app/backups" ]; then
    cp -r /opt/scandy/app/backups /opt/scandy/app/backups.backup
    echo -e "${GREEN}✅ Backups gesichert${NC}"
fi

# Stoppe Scandy-Service
echo -e "${BLUE}🛑 Stoppe Scandy-Service...${NC}"
systemctl stop scandy || true

# Kopiere aktuelle Codebase
echo -e "${BLUE}📥 Kopiere aktuelle Codebase...${NC}"
if [ "$PWD" != "/opt/scandy" ]; then
    # Kopiere alle Dateien außer .env und wichtigen Daten
    rsync -av --exclude='.env' --exclude='app/uploads' --exclude='app/backups' --exclude='venv' --exclude='.git' . /opt/scandy/
    echo -e "${GREEN}✅ Codebase kopiert${NC}"
else
    echo -e "${YELLOW}⚠️  Bereits im Zielverzeichnis - überspringe Kopieren${NC}"
fi

# Setze korrekte Berechtigungen
echo -e "${BLUE}🔐 Setze Berechtigungen...${NC}"
chown -R scandy:scandy /opt/scandy
chmod +x /opt/scandy/app/*.py 2>/dev/null || true

# Aktualisiere Python-Abhängigkeiten
echo -e "${BLUE}🐍 Aktualisiere Python-Abhängigkeiten...${NC}"
sudo -u scandy /opt/scandy/venv/bin/pip install --upgrade pip
sudo -u scandy /opt/scandy/venv/bin/pip install -r /opt/scandy/requirements.txt

# Stelle .env wieder her falls sie überschrieben wurde
if [ -f "/opt/scandy/.env.backup" ]; then
    echo -e "${BLUE}🔄 Stelle .env wieder her...${NC}"
    cp /opt/scandy/.env.backup /opt/scandy/.env
    chown scandy:scandy /opt/scandy/.env
    echo -e "${GREEN}✅ .env wieder hergestellt${NC}"
fi

# Stelle wichtige Daten wieder her
echo -e "${BLUE}🔄 Stelle wichtige Daten wieder her...${NC}"
if [ -d "/opt/scandy/app/uploads.backup" ]; then
    rm -rf /opt/scandy/app/uploads
    mv /opt/scandy/app/uploads.backup /opt/scandy/app/uploads
    echo -e "${GREEN}✅ Uploads wieder hergestellt${NC}"
fi

if [ -d "/opt/scandy/app/backups.backup" ]; then
    rm -rf /opt/scandy/app/backups
    mv /opt/scandy/app/backups.backup /opt/scandy/app/backups
    echo -e "${GREEN}✅ Backups wieder hergestellt${NC}"
fi

# Starte Scandy-Service neu
echo -e "${BLUE}🚀 Starte Scandy-Service neu...${NC}"
systemctl daemon-reload
systemctl restart scandy

# Korrigiere Berechtigungen für Static Files
echo -e "${BLUE}🔧 Korrigiere Berechtigungen für Static Files...${NC}"
if [ -d "/opt/scandy/app/static" ]; then
    chmod -R 755 /opt/scandy/app/static/
    chown -R scandy:scandy /opt/scandy/app/static/
    echo -e "${GREEN}✅ Static Files Berechtigungen korrigiert${NC}"
fi

# Korrigiere Berechtigungen für Upload-Verzeichnis
if [ -d "/opt/scandy/app/uploads" ]; then
    chmod -R 755 /opt/scandy/app/uploads/
    chown -R scandy:scandy /opt/scandy/app/uploads/
    echo -e "${GREEN}✅ Upload-Verzeichnis Berechtigungen korrigiert${NC}"
fi

# Korrigiere Berechtigungen für Flask-Session
if [ -d "/opt/scandy/app/flask_session" ]; then
    chmod -R 755 /opt/scandy/app/flask_session/
    chown -R scandy:scandy /opt/scandy/app/flask_session/
    echo -e "${GREEN}✅ Flask-Session Berechtigungen korrigiert${NC}"
fi

# Warte auf Service-Start
echo -e "${BLUE}⏳ Warte auf Service-Start...${NC}"
sleep 5

# Prüfe Service-Status
echo -e "${BLUE}🔍 Prüfe Service-Status...${NC}"
if systemctl is-active --quiet scandy; then
    echo -e "${GREEN}✅ Scandy-Service läuft erfolgreich${NC}"
else
    echo -e "${RED}❌ Scandy-Service läuft nicht!${NC}"
    echo -e "${YELLOW}📋 Letzte Logs:${NC}"
    journalctl -u scandy --no-pager -n 10
    exit 1
fi

# Prüfe App-Verfügbarkeit
echo -e "${BLUE}🔍 Prüfe App-Verfügbarkeit...${NC}"
sleep 3

if curl -s http://localhost:5000 &> /dev/null; then
    echo -e "${GREEN}✅ Scandy-App läuft erfolgreich${NC}"
else
    echo -e "${YELLOW}⚠️  Scandy-App startet noch...${NC}"
    echo "   Bitte warten Sie einen Moment und prüfen Sie:"
    echo "   journalctl -u scandy -f"
fi

# Zeige finale Informationen
echo
echo "========================================"
echo -e "${GREEN}✅ UPDATE ABGESCHLOSSEN!${NC}"
echo "========================================"
echo
echo -e "${GREEN}🎉 Scandy wurde erfolgreich aktualisiert!${NC}"
echo
echo -e "${BLUE}🌐 Verfügbare Services:${NC}"
IP=$(hostname -I | awk '{print $1}')
echo "- Scandy App:     http://$IP/"
echo "- Scandy App:     http://localhost/"
echo
echo -e "${BLUE}💾 Datenbank-Status:${NC}"
echo "- MongoDB:        🔒 Unverändert (Daten erhalten)"
echo "- Datenbank:      🔒 Unverändert (Daten erhalten)"
echo
echo -e "${BLUE}🔐 Konfiguration:${NC}"
echo "- .env-Datei:     🔒 Unverändert (Einstellungen erhalten)"
echo "- Backup:         .env.backup (falls benötigt)"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Service-Status: systemctl status scandy"
echo "- Service-Logs:   journalctl -u scandy -f"
echo "- Service-Stop:   systemctl stop scandy"
echo "- Service-Start:  systemctl start scandy"
echo "- Service-Restart: systemctl restart scandy"
echo "- Nginx-Status:   systemctl status nginx"
echo "- Nginx-Logs:     journalctl -u nginx -f"
echo
echo -e "${BLUE}📁 Datenverzeichnisse (unverändert):${NC}"
echo "- App:            /opt/scandy/"
echo "- Uploads:        /opt/scandy/app/uploads/"
echo "- Backups:        /opt/scandy/app/backups/"
echo "- Logs:           journalctl -u scandy"
echo
echo -e "${YELLOW}⚠️  WICHTIG: Prüfe die Logs bei Problemen:${NC}"
echo "   journalctl -u scandy -f"
echo
echo "========================================"
