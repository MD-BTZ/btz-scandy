#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starte Docker-Update-Prozess...${NC}"

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker ist nicht installiert!${NC}"
    exit 1
fi

# Prüfe ob docker compose installiert ist
if ! docker compose version &> /dev/null; then
    echo -e "${RED}docker compose ist nicht installiert!${NC}"
    exit 1
fi

# Hole die neuesten Änderungen
echo -e "${GREEN}Pulling latest changes from git...${NC}"
git pull origin main

# Stoppe die Container
echo -e "${GREEN}Stopping containers...${NC}"
docker compose down
docker compose -f docker-compose.test.yml down

# Baue die Container neu
echo -e "${GREEN}Building new containers...${NC}"
docker compose build --no-cache
docker compose -f docker-compose.test.yml build --no-cache

# Starte die Container neu
echo -e "${GREEN}Starting containers...${NC}"
docker compose up -d
docker compose -f docker-compose.test.yml up -d

# Prüfe ob alles läuft
echo -e "${GREEN}Checking container status...${NC}"
echo -e "${GREEN}Main instance:${NC}"
docker compose ps
echo -e "${GREEN}Test instance:${NC}"
docker compose -f docker-compose.test.yml ps

echo -e "${GREEN}Update completed!${NC}" 