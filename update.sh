#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Scandy Auto-Updater${NC}"
echo -e "${GREEN}   Automatisches Update ohne Abfragen${NC}"
echo -e "${GREEN}========================================${NC}"

# Prüfe ob docker-compose.yml existiert
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}docker-compose.yml nicht gefunden. Bitte führen Sie zuerst die Installation aus.${NC}"
    exit 1
fi

# Container stoppen
echo -e "${GREEN}Stoppe Container...${NC}"
docker-compose down

# Git-Pull für Updates
echo -e "${GREEN}Hole Updates...${NC}"
git pull origin main

# Container neu bauen und starten
echo -e "${GREEN}Baue und starte Container neu...${NC}"
docker-compose up -d --build

# Warte auf Container-Start
echo -e "${GREEN}Warte auf Container-Start...${NC}"
sleep 30

# Prüfe Container-Status
echo -e "${GREEN}Prüfe Container-Status...${NC}"
docker-compose ps

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Update abgeschlossen!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Scandy-Anwendung: ${BLUE}http://localhost:5000${NC}"
echo -e "MongoDB Express: ${BLUE}http://localhost:8081${NC}"
echo -e "${GREEN}========================================${NC}" 