#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Session-Cleanup für Multi-Instance Setup${NC}"
echo "========================================"

# Finde alle Session-Verzeichnisse
echo -e "${YELLOW}🔍 Suche Session-Verzeichnisse...${NC}"

# Hauptverzeichnis
if [ -d "app/flask_session" ]; then
    echo -e "${BLUE}📁 Hauptverzeichnis: app/flask_session${NC}"
    find app/flask_session -name "*.session" -delete 2>/dev/null
    echo -e "${GREEN}✅ Session-Dateien im Hauptverzeichnis gelöscht${NC}"
fi

# Instance-Verzeichnisse
for dir in */; do
    if [ -d "$dir/app/flask_session" ]; then
        echo -e "${BLUE}📁 Instance $dir: app/flask_session${NC}"
        find "$dir/app/flask_session" -name "*.session" -delete 2>/dev/null
        echo -e "${GREEN}✅ Session-Dateien in $dir gelöscht${NC}"
    fi
done

# Docker Container Session-Volumes
echo -e "${YELLOW}🐳 Stoppe Container für Session-Reset...${NC}"
docker compose down 2>/dev/null

# Finde alle Instance-Verzeichnisse mit docker-compose.yml
for dir in */; do
    if [ -f "$dir/docker-compose.yml" ]; then
        echo -e "${BLUE}🛑 Stoppe Container in $dir${NC}"
        cd "$dir"
        docker compose down 2>/dev/null
        cd ..
    fi
done

echo -e "${GREEN}✅ Session-Cleanup abgeschlossen!${NC}"
echo ""
echo -e "${YELLOW}💡 Tipp: Starte die Instanzen neu mit:${NC}"
echo "  ./manage.sh start                    # Haupt-Instanz"
echo "  cd verwaltung && ./manage.sh start   # Verwaltung-Instanz"
echo "  cd werkstatt && ./manage.sh start    # Werkstatt-Instanz" 