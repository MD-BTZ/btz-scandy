#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 E-Mail Session-Fix Tool${NC}"
echo "========================================"

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -f "app/routes/admin.py" ]; then
    echo -e "${RED}❌ Bitte führen Sie dieses Skript im Scandy-Hauptverzeichnis aus!${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Suche Session-Probleme...${NC}"

# Finde alle Session-Verzeichnisse
session_dirs=()
if [ -d "app/flask_session" ]; then
    session_dirs+=("app/flask_session")
fi

# Finde Instance-Session-Verzeichnisse
for dir in */; do
    if [ -d "$dir/app/flask_session" ]; then
        session_dirs+=("$dir/app/flask_session")
    fi
done

if [ ${#session_dirs[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Keine Session-Verzeichnisse gefunden${NC}"
    exit 0
fi

echo -e "${GREEN}✅ Gefundene Session-Verzeichnisse:${NC}"
for dir in "${session_dirs[@]}"; do
    echo "  - $dir"
done

echo ""
echo -e "${BLUE}🧹 Bereinige Session-Dateien...${NC}"

# Bereinige Session-Dateien
for dir in "${session_dirs[@]}"; do
    echo -e "${YELLOW}📁 Bereinige $dir...${NC}"
    
    # Lösche beschädigte Session-Dateien
    find "$dir" -name "*.session" -size 0 -delete 2>/dev/null
    find "$dir" -name "*.session" -mtime +7 -delete 2>/dev/null
    
    # Zähle verbleibende Session-Dateien
    session_count=$(find "$dir" -name "*.session" 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ $session_count Session-Dateien in $dir${NC}"
done

echo ""
echo -e "${BLUE}🐳 Stoppe Container für Session-Reset...${NC}"

# Stoppe alle Container
docker compose down 2>/dev/null

# Stoppe Instance-Container
for dir in */; do
    if [ -f "$dir/docker-compose.yml" ]; then
        echo -e "${YELLOW}🛑 Stoppe Container in $dir${NC}"
        cd "$dir"
        docker compose down 2>/dev/null
        cd ..
    fi
done

echo ""
echo -e "${BLUE}🔧 Session-Konfiguration prüfen...${NC}"

# Prüfe Session-Konfiguration in der App
if grep -q "SESSION_FILE_DIR" app/config/config.py; then
    echo -e "${GREEN}✅ Session-Konfiguration gefunden${NC}"
else
    echo -e "${YELLOW}⚠️  Session-Konfiguration nicht gefunden${NC}"
fi

echo ""
echo -e "${GREEN}✅ Session-Fix abgeschlossen!${NC}"
echo ""
echo -e "${YELLOW}💡 Nächste Schritte:${NC}"
echo "1. Starte die Instanzen neu:"
echo "   ./manage.sh start                    # Haupt-Instanz"
echo "   cd verwaltung && ./manage.sh start   # Verwaltung-Instanz"
echo "   cd werkstatt && ./manage.sh start    # Werkstatt-Instanz"
echo ""
echo "2. Teste E-Mail-Einstellungen:"
echo "   - Gehe zu Admin → E-Mail-Einstellungen"
echo "   - Speichere Einstellungen"
echo "   - Prüfe ob Session erhalten bleibt"
echo ""
echo "3. Bei Problemen:"
echo "   ./cleanup_sessions.sh               # Vollständige Session-Bereinigung" 