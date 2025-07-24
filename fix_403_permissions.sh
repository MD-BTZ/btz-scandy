#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy 403 Forbidden Fix"
echo "========================================"
echo "Dieses Skript behebt 403 Forbidden Fehler:"
echo "- ✅ Static Files Berechtigungen"
echo "- ✅ Upload-Verzeichnis Berechtigungen"
echo "- ✅ Container-Berechtigungen"
echo "- ✅ Flask-Session Berechtigungen"
echo "========================================"
echo

# 1. Static Files Berechtigungen
echo -e "${BLUE}🔧 1. Korrigiere Static Files Berechtigungen...${NC}"
if [ -d "app/static" ]; then
    chmod -R 755 app/static/
    echo -e "${GREEN}✅ Static Files: 755${NC}"
    ls -la app/static/ | head -5
else
    echo -e "${RED}❌ app/static Verzeichnis nicht gefunden${NC}"
fi

# 2. Upload-Verzeichnis Berechtigungen
echo -e "${BLUE}🔧 2. Korrigiere Upload-Verzeichnis Berechtigungen...${NC}"
if [ -d "data/uploads" ]; then
    chmod -R 755 data/uploads/
    echo -e "${GREEN}✅ Upload-Verzeichnis: 755${NC}"
    ls -la data/uploads/ | head -5
else
    echo -e "${YELLOW}⚠️  data/uploads Verzeichnis nicht gefunden${NC}"
fi

# 3. Flask-Session Berechtigungen
echo -e "${BLUE}🔧 3. Korrigiere Flask-Session Berechtigungen...${NC}"
if [ -d "app/flask_session" ]; then
    chmod -R 755 app/flask_session/
    echo -e "${GREEN}✅ Flask-Session: 755${NC}"
else
    echo -e "${YELLOW}⚠️  app/flask_session Verzeichnis nicht gefunden${NC}"
fi

# 4. Container-Berechtigungen (falls Docker läuft)
echo -e "${BLUE}🔧 4. Korrigiere Container-Berechtigungen...${NC}"
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo -e "${BLUE}🐳 Docker verfügbar - korrigiere Container-Berechtigungen...${NC}"
    
    # Prüfe ob Container läuft
    if docker compose ps | grep -q "scandy-app"; then
        echo -e "${BLUE}🔧 Korrigiere Berechtigungen im Container...${NC}"
        docker compose exec scandy-app chmod -R 755 /app/app/static/ 2>/dev/null || echo -e "${YELLOW}⚠️  Container-Berechtigungen konnten nicht korrigiert werden${NC}"
        docker compose exec scandy-app chmod -R 755 /app/data/uploads/ 2>/dev/null || echo -e "${YELLOW}⚠️  Upload-Berechtigungen konnten nicht korrigiert werden${NC}"
        echo -e "${GREEN}✅ Container-Berechtigungen korrigiert${NC}"
    else
        echo -e "${YELLOW}⚠️  Scandy-App Container läuft nicht${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker nicht verfügbar${NC}"
fi

# 5. Prüfe Static Files im Browser
echo -e "${BLUE}🔧 5. Prüfe Static Files Verfügbarkeit...${NC}"
if command -v curl &> /dev/null; then
    echo -e "${BLUE}🌐 Teste Static Files über HTTP...${NC}"
    
    # Teste verschiedene Static Files
    static_files=(
        "http://localhost:5000/static/css/main.css"
        "http://localhost:5000/static/js/main.js"
        "http://localhost:5000/static/images/scandy-logo.png"
    )
    
    for file in "${static_files[@]}"; do
        if curl -s -I "$file" | grep -q "200 OK"; then
            echo -e "${GREEN}✅ $file - OK${NC}"
        elif curl -s -I "$file" | grep -q "403 Forbidden"; then
            echo -e "${RED}❌ $file - 403 Forbidden${NC}"
        else
            echo -e "${YELLOW}⚠️  $file - Nicht erreichbar${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  curl nicht verfügbar - kann Static Files nicht testen${NC}"
fi

# 6. Debug-Informationen
echo -e "${BLUE}🔧 6. Debug-Informationen...${NC}"
echo -e "${BLUE}📁 Aktuelle Verzeichnisstruktur:${NC}"
ls -la app/static/ 2>/dev/null || echo "app/static/ nicht gefunden"
echo
echo -e "${BLUE}🐳 Container-Status:${NC}"
docker compose ps 2>/dev/null || echo "Docker nicht verfügbar"
echo
echo -e "${BLUE}📋 App-Logs (letzte 5 Zeilen):${NC}"
docker compose logs --tail=5 scandy-app 2>/dev/null || echo "Container-Logs nicht verfügbar"

echo
echo "========================================"
echo -e "${GREEN}✅ 403 Forbidden Fix abgeschlossen!${NC}"
echo "========================================"
echo
echo -e "${BLUE}🔧 Nächste Schritte:${NC}"
echo "1. Browser-Cache leeren (Ctrl+F5)"
echo "2. Seite neu laden"
echo "3. Falls Problem besteht: ./debug_lxc_layout.sh"
echo "4. Falls weiterhin Probleme: Container neu starten"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Container neu starten: docker compose restart scandy-app"
echo "- App-Logs: docker compose logs -f scandy-app"
echo "- Debug-Skript: ./debug_lxc_layout.sh"
echo
echo "========================================"
read -p "Drücke Enter zum Beenden..." 