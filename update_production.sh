#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy Produktions-Update"
echo "========================================"
echo

# Sichere .env-Datei vor dem Update
if [ -f ".env" ]; then
    echo -e "${BLUE}💾 Sichere .env-Datei...${NC}"
    cp .env .env.backup
    echo -e "${GREEN}✅ .env gesichert als .env.backup${NC}"
fi

echo -e "${BLUE}🛑 Stoppe Container...${NC}"
docker compose down

echo
echo -e "${BLUE}📥 Hole neueste Version...${NC}"
git pull

echo
echo -e "${BLUE}🔨 Baue Container neu...${NC}"
docker compose build --no-cache

echo
echo -e "${BLUE}🚀 Starte Container...${NC}"
docker compose up -d

echo
echo -e "${BLUE}⏳ Warte auf Container-Start...${NC}"
sleep 10

echo
echo -e "${BLUE}🔍 Pruefe Status...${NC}"
docker compose ps

echo
echo -e "${BLUE}📋 Letzte Logs:${NC}"
docker compose logs --tail=10 scandy-app

echo
echo "========================================"
echo -e "${GREEN}✅ Update abgeschlossen!${NC}"
echo "========================================"
echo
echo -e "${BLUE}🌐 Verfügbare Services:${NC}"
echo "- Scandy App:     http://localhost:5000"
echo "- Mongo Express:  http://localhost:8081"
echo
echo -e "${BLUE}🔐 Konfiguration:${NC}"
echo "- .env-Datei:     🔒 Unverändert (Einstellungen erhalten)"
echo "- Backup:         .env.backup (falls benötigt)"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Logs anzeigen:  docker compose logs -f"
echo "- Status:         docker compose ps"
echo "- Neustart:       docker compose restart" 