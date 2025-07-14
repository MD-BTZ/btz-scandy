#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 MongoDB Debug-Tool${NC}"
echo "========================================"

# Prüfe Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker ist nicht installiert!${NC}"
    exit 1
fi

# Finde alle MongoDB Container
echo -e "${YELLOW}🔍 Suche MongoDB Container...${NC}"
mongodb_containers=$(docker ps -a --filter "name=scandy-mongodb" --format "{{.Names}}")

if [ -z "$mongodb_containers" ]; then
    echo -e "${YELLOW}⚠️  Keine MongoDB Container gefunden${NC}"
    exit 0
fi

echo -e "${GREEN}✅ Gefundene MongoDB Container:${NC}"
echo "$mongodb_containers"
echo ""

# Prüfe jeden Container
for container in $mongodb_containers; do
    echo -e "${BLUE}📊 Container: $container${NC}"
    echo "----------------------------------------"
    
    # Status
    status=$(docker inspect -f "{{.State.Status}}" "$container" 2>/dev/null)
    echo -e "Status: $status"
    
    # Health Status
    health=$(docker inspect -f "{{.State.Health.Status}}" "$container" 2>/dev/null)
    if [ "$health" != "<nil>" ]; then
        echo -e "Health: $health"
    else
        echo -e "Health: nicht konfiguriert"
    fi
    
    # Ports
    ports=$(docker port "$container" 2>/dev/null)
    if [ -n "$ports" ]; then
        echo -e "Ports: $ports"
    else
        echo -e "Ports: nicht verfügbar"
    fi
    
    # Logs (letzte 5 Zeilen)
    echo -e "${YELLOW}📋 Letzte Logs:${NC}"
    docker logs "$container" --tail 5 2>/dev/null || echo "Keine Logs verfügbar"
    
    echo ""
done

# Prüfe Docker Volumes
echo -e "${BLUE}💾 MongoDB Volumes:${NC}"
docker volume ls --filter "name=mongodb_data" 2>/dev/null || echo "Keine MongoDB Volumes gefunden"

# Prüfe Netzwerke
echo -e "${BLUE}🌐 Scandy Netzwerke:${NC}"
docker network ls --filter "name=scandy" 2>/dev/null || echo "Keine Scandy Netzwerke gefunden"

# Prüfe Port-Konflikte
echo -e "${BLUE}🔍 Port-Konflikte prüfen:${NC}"
for port in 27017 27018 27019 27020; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port $port ist belegt${NC}"
    else
        echo -e "${GREEN}✅ Port $port ist frei${NC}"
    fi
done

echo ""
echo -e "${BLUE}🔧 Debug-Befehle:${NC}"
echo "  docker logs <container-name> -f    # Live-Logs anzeigen"
echo "  docker exec -it <container-name> bash  # In Container wechseln"
echo "  docker stats <container-name>      # Ressourcen anzeigen"
echo "  docker inspect <container-name>    # Detaillierte Infos" 