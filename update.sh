#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy App Update"
echo "========================================"
echo "Dieses Skript aktualisiert NUR die Scandy-App:"
echo "- ✅ Scandy App wird aktualisiert"
echo "- 🔒 MongoDB bleibt unverändert"
echo "- 🔒 Mongo Express bleibt unverändert"
echo "- 💾 Alle Daten bleiben erhalten"
echo "- 🔐 .env-Einstellungen bleiben erhalten"
echo "========================================"
echo

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker ist nicht installiert oder nicht verfügbar!${NC}"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker läuft nicht!${NC}"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

# Prüfe ob .env existiert, falls nicht erstelle sie
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📝 Erstelle .env-Datei aus env.example...${NC}"
    cp env.example .env
    echo -e "${GREEN}✅ .env-Datei erstellt!${NC}"
    echo -e "${YELLOW}⚠️  Bitte passe die Werte in .env an deine Umgebung an!${NC}"
    echo
fi

# Sichere .env-Datei vor dem Update
if [ -f ".env" ]; then
    echo -e "${BLUE}💾 Sichere .env-Datei...${NC}"
    cp .env .env.backup
    echo -e "${GREEN}✅ .env gesichert als .env.backup${NC}"
fi

# Prüfe ob docker-compose.yml existiert
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ ERROR: docker-compose.yml nicht gefunden!${NC}"
    echo "Bitte führen Sie zuerst ./install.sh aus."
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

echo -e "${BLUE}🔍 Prüfe bestehende Installation...${NC}"
docker compose ps

echo
echo -e "${YELLOW}⚠️  WARNUNG: Dieses Update betrifft NUR die Scandy-App!${NC}"
echo "   MongoDB und Mongo Express bleiben unverändert."
echo "   Alle Daten bleiben erhalten."
echo "   .env-Einstellungen bleiben erhalten."
echo

read -p "Möchten Sie fortfahren? (j/N): " confirm
if [[ ! $confirm =~ ^[Jj]$ ]]; then
    echo "Update abgebrochen."
    read -p "Drücke Enter zum Beenden..."
    exit 0
fi

echo
echo -e "${BLUE}🔄 Starte App-Update...${NC}"

# Stoppe nur die App-Container
echo -e "${BLUE}🛑 Stoppe App-Container...${NC}"
docker compose stop scandy-app &> /dev/null

# Entferne nur die App-Container
echo -e "${BLUE}🗑️  Entferne alte App-Container...${NC}"
docker compose rm -f scandy-app &> /dev/null

# Entferne alte App-Images
echo -e "${BLUE}🗑️  Entferne alte App-Images...${NC}"
docker images | grep scandy-local | awk '{print $3}' | xargs -r docker rmi -f &> /dev/null

# Baue nur die App neu
echo -e "${BLUE}🔨 Baue neue App-Version...${NC}"
docker compose build --no-cache scandy-app

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Versuche es mit einfachem Build...${NC}"
    docker compose build scandy-app
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ App-Update fehlgeschlagen!${NC}"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

# Starte nur die App
echo -e "${BLUE}🚀 Starte neue App-Version...${NC}"
docker compose up -d scandy-app

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Fehler beim Starten der App!${NC}"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

# Korrigiere Berechtigungen für Static Files
echo -e "${BLUE}🔧 Korrigiere Berechtigungen für Static Files...${NC}"
if [ -d "app/static" ]; then
    chmod -R 755 app/static/
    echo -e "${GREEN}✅ Static Files Berechtigungen korrigiert${NC}"
fi

# Korrigiere Berechtigungen für Upload-Verzeichnis
if [ -d "data/uploads" ]; then
    chmod -R 755 data/uploads/
    echo -e "${GREEN}✅ Upload-Verzeichnis Berechtigungen korrigiert${NC}"
fi

echo
echo -e "${BLUE}⏳ Warte auf App-Start...${NC}"
sleep 10

# Prüfe App-Status
echo -e "${BLUE}🔍 Prüfe App-Status...${NC}"
docker compose ps scandy-app

# Prüfe App-Logs
echo
echo -e "${BLUE}📋 Letzte App-Logs:${NC}"
docker compose logs --tail=10 scandy-app

# Prüfe ob App läuft
echo
echo -e "${BLUE}🔍 Prüfe App-Verfügbarkeit...${NC}"
sleep 5

if curl -s http://localhost:5000 &> /dev/null; then
    echo -e "${GREEN}✅ Scandy App läuft erfolgreich${NC}"
else
    echo -e "${YELLOW}⚠️  Scandy App startet noch...${NC}"
    echo "   Bitte warten Sie einen Moment und prüfen Sie:"
    echo "   docker compose logs scandy-app"
fi

echo
echo "========================================"
echo -e "${GREEN}✅ APP-UPDATE ABGESCHLOSSEN!${NC}"
echo "========================================"
echo
echo -e "${GREEN}🎉 Die Scandy-App wurde erfolgreich aktualisiert!${NC}"
echo
echo -e "${BLUE}🌐 Verfügbare Services:${NC}"
echo "- Scandy App:     http://localhost:5000 ✅ AKTUALISIERT"
echo "- Mongo Express:  http://localhost:8081 🔒 UNVERÄNDERT"
echo
echo -e "${BLUE}💾 Datenbank-Status:${NC}"
echo "- MongoDB:        🔒 Unverändert (Daten erhalten)"
echo "- Mongo Express:  🔒 Unverändert (Daten erhalten)"
echo
echo -e "${BLUE}🔐 Konfiguration:${NC}"
echo "- .env-Datei:     🔒 Unverändert (Einstellungen erhalten)"
echo "- Backup:         .env.backup (falls benötigt)"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- App-Logs:       docker compose logs -f scandy-app"
echo "- App-Status:     docker compose ps scandy-app"
echo "- App-Neustart:   docker compose restart scandy-app"
echo "- Alle Container: docker compose ps"
echo
echo -e "${BLUE}📁 Datenverzeichnisse (unverändert):${NC}"
echo "- Backups: ./backups/"
echo "- Logs:    ./logs/"
echo "- Uploads: ./data/uploads/"
echo
echo "========================================"
read -p "Drücke Enter zum Beenden..." 