#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starte Update-Prozess...${NC}"

# Git-Repository aktualisieren
echo -e "${GREEN}Pulling latest changes from git...${NC}"
git pull origin main

# Docker-Container stoppen
echo -e "${GREEN}Stopping containers...${NC}"
docker-compose down

# Neue Images pullen
echo -e "${GREEN}Pulling new images...${NC}"
docker-compose pull

# Container neu bauen und starten
echo -e "${GREEN}Building and starting containers...${NC}"
docker-compose up -d --build

# Prüfen ob alles läuft
echo -e "${GREEN}Checking container status...${NC}"
docker-compose ps

echo -e "${GREEN}Update completed!${NC}" 