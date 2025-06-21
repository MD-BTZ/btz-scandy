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
echo -e "${GREEN}   Scandy Cleanup-Skript${NC}"
echo -e "${GREEN}   Entfernt alle Container und Daten${NC}"
echo -e "${GREEN}========================================${NC}"

# Container stoppen und entfernen
echo -e "${GREEN}Stoppe und entferne Container...${NC}"
docker-compose down --volumes --remove-orphans 2>/dev/null || true

# Entferne Container mit Scandy-Namen
echo -e "${GREEN}Entferne Scandy-Container...${NC}"
docker rm -f scandy-mongodb scandy-app scandy-mongo-express 2>/dev/null || true
docker rm -f scandyneu-app 2>/dev/null || true

# Entferne Images
echo -e "${GREEN}Entferne Scandy-Images...${NC}"
docker rmi scandyneu-app:latest 2>/dev/null || true

# Entferne Netzwerke
echo -e "${GREEN}Entferne Scandy-Netzwerke...${NC}"
docker network rm scandyneu_scandy-network 2>/dev/null || true
docker network rm scandy_scandy-network 2>/dev/null || true

# Entferne Volumes
echo -e "${GREEN}Entferne Scandy-Volumes...${NC}"
docker volume rm scandy_css_test-mongodb-data 2>/dev/null || true

# Entferne Datenverzeichnisse (optional)
read -p "Möchten Sie auch die Datenverzeichnisse entfernen? (j/n): " remove_data
if [[ "$remove_data" =~ ^[Jj]$ ]]; then
    echo -e "${GREEN}Entferne Datenverzeichnisse...${NC}"
    rm -rf scandy_data 2>/dev/null || true
    rm -rf backups 2>/dev/null || true
    rm -rf logs 2>/dev/null || true
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Cleanup abgeschlossen!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Alle Scandy-Container und Daten wurden entfernt."
echo -e "Sie können jetzt eine neue Installation durchführen."
echo -e "${GREEN}========================================${NC}" 