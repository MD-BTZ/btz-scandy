#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Scandy Container Rebuild Script${NC}"
echo "=================================="

# Prüfe ob Parameter übergeben wurde
if [ "$1" = "--full" ]; then
    echo -e "${YELLOW}🔄 Vollständiger Rebuild (mit Cache-Invalidierung)${NC}"
    FULL_REBUILD=true
else
    echo -e "${YELLOW}⚡ Schneller Rebuild (nur lokale Änderungen)${NC}"
    echo -e "${BLUE}Verwenden Sie './rebuild.sh --full' für vollständigen Rebuild${NC}"
    FULL_REBUILD=false
fi

echo ""

# Funktion für Fehlerbehandlung
handle_error() {
    echo -e "${RED}❌ Fehler aufgetreten!${NC}"
    echo -e "${YELLOW}Versuche Container zu stoppen...${NC}"
    docker-compose down
    exit 1
}

# Fehlerbehandlung aktivieren
set -e
trap handle_error ERR

# 1. Container stoppen
echo -e "${YELLOW}📦 Stoppe Container...${NC}"
docker-compose down
echo -e "${GREEN}✅ Container gestoppt${NC}"

# 2. Container bauen (mit oder ohne Cache)
if [ "$FULL_REBUILD" = true ]; then
    echo -e "${YELLOW}🔨 Baue Container neu (ohne Cache)...${NC}"
    docker-compose build --no-cache
    echo -e "${GREEN}✅ Container neu gebaut (ohne Cache)${NC}"
else
    echo -e "${YELLOW}🔨 Baue Container neu (mit Cache)...${NC}"
    docker-compose build
    echo -e "${GREEN}✅ Container neu gebaut (mit Cache)${NC}"
fi

# 3. Container starten
echo -e "${YELLOW}🚀 Starte Container...${NC}"
docker-compose up -d
echo -e "${GREEN}✅ Container gestartet${NC}"

# 4. Status anzeigen
echo -e "${YELLOW}📊 Container Status:${NC}"
docker-compose ps

echo ""
echo -e "${GREEN}🎉 Rebuild abgeschlossen!${NC}"
echo -e "${BLUE}Die Anwendung sollte jetzt unter http://localhost:5000 verfügbar sein.${NC}"
echo ""
echo -e "${YELLOW}📝 Nützliche Befehle:${NC}"
echo -e "  • Logs anzeigen: ${BLUE}docker-compose logs -f app${NC}"
echo -e "  • Vollständiger Rebuild: ${BLUE}./rebuild.sh --full${NC}"
echo -e "  • Container stoppen: ${BLUE}docker-compose down${NC}" 