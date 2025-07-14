#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Fix: Benutzer-Erstellung in Multi-Instance Setup${NC}"
echo "========================================"

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -f "app/routes/admin.py" ]; then
    echo -e "${RED}❌ Bitte führen Sie dieses Skript im Scandy-Hauptverzeichnis aus!${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Prüfe Benutzer-Erstellungsprobleme...${NC}"

# Finde alle Instance-Verzeichnisse
instances=()
if [ -f ".env" ]; then
    instances+=("Haupt-Instanz (.)")
fi

for dir in */; do
    if [ -f "$dir/docker-compose.yml" ]; then
        instances+=("$dir")
    fi
done

echo -e "${GREEN}✅ Gefundene Instanzen:${NC}"
for instance in "${instances[@]}"; do
    echo "  - $instance"
done

echo ""
echo -e "${BLUE}🧹 Session-Bereinigung für alle Instanzen...${NC}"

# Bereinige Sessions für alle Instanzen
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📁 Bereinige Haupt-Instanz Sessions...${NC}"
        if [ -d "app/flask_session" ]; then
            find app/flask_session -name "*.session" -delete 2>/dev/null
            echo -e "${GREEN}✅ Haupt-Instanz Sessions bereinigt${NC}"
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📁 Bereinige $instance_dir Sessions...${NC}"
        if [ -d "$instance_dir/app/flask_session" ]; then
            find "$instance_dir/app/flask_session" -name "*.session" -delete 2>/dev/null
            echo -e "${GREEN}✅ $instance_dir Sessions bereinigt${NC}"
        fi
    fi
done

echo ""
echo -e "${BLUE}🐳 Container neu starten...${NC}"

# Stoppe alle Container
echo -e "${YELLOW}🛑 Stoppe alle Container...${NC}"
docker compose down 2>/dev/null

for dir in */; do
    if [ -f "$dir/docker-compose.yml" ]; then
        echo -e "${YELLOW}🛑 Stoppe Container in $dir${NC}"
        cd "$dir"
        docker compose down 2>/dev/null
        cd ..
    fi
done

# Starte Container neu
echo -e "${YELLOW}🚀 Starte Container neu...${NC}"

# Haupt-Instanz
if [ -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}🚀 Starte Haupt-Instanz...${NC}"
    docker compose up -d
fi

# Instance-Verzeichnisse
for dir in */; do
    if [ -f "$dir/docker-compose.yml" ]; then
        echo -e "${YELLOW}🚀 Starte $dir...${NC}"
        cd "$dir"
        docker compose up -d
        cd ..
    fi
done

echo ""
echo -e "${BLUE}⏳ Warte auf Container-Start...${NC}"
sleep 30

echo ""
echo -e "${BLUE}🔍 Prüfe Container-Status...${NC}"

# Prüfe Container-Status
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📊 Haupt-Instanz Status:${NC}"
        if [ -f "docker-compose.yml" ]; then
            docker compose ps
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📊 $instance_dir Status:${NC}"
        if [ -f "$instance_dir/docker-compose.yml" ]; then
            cd "$instance_dir"
            docker compose ps
            cd ..
        fi
    fi
done

echo ""
echo -e "${BLUE}🔧 Datenbank-Verbindungen prüfen...${NC}"

# Prüfe MongoDB-Verbindungen
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📊 Haupt-Instanz MongoDB:${NC}"
        if docker ps | grep -q "scandy-mongodb-scandy"; then
            echo "  ✅ MongoDB Container läuft"
            
            # Prüfe Admin-Benutzer
            echo "  📋 Admin-Benutzer:"
            docker exec scandy-mongodb-scandy mongosh --eval "db.users.find({role: 'admin'}, {username: 1, role: 1, is_active: 1}).pretty()" 2>/dev/null || echo "    Fehler beim Abfragen der Admin-Benutzer"
        else
            echo "  ❌ MongoDB Container läuft nicht"
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📊 $instance_dir MongoDB:${NC}"
        container_name="scandy-mongodb-$instance_dir"
        if docker ps | grep -q "$container_name"; then
            echo "  ✅ MongoDB Container läuft"
            
            # Prüfe Admin-Benutzer
            echo "  📋 Admin-Benutzer:"
            docker exec "$container_name" mongosh --eval "db.users.find({role: 'admin'}, {username: 1, role: 1, is_active: 1}).pretty()" 2>/dev/null || echo "    Fehler beim Abfragen der Admin-Benutzer"
        else
            echo "  ❌ MongoDB Container läuft nicht"
        fi
    fi
done

echo ""
echo -e "${GREEN}✅ Fix abgeschlossen!${NC}"
echo ""
echo -e "${YELLOW}💡 Nächste Schritte:${NC}"
echo ""
echo "1. Teste Benutzer-Erstellung:"
echo "   - Gehe zu Admin → Benutzerverwaltung"
echo "   - Klicke auf 'Neuen Benutzer hinzufügen'"
echo "   - Fülle das Formular aus und speichere"
echo ""
echo "2. Bei Problemen:"
echo "   ./debug_user_creation.sh    # Detailliertes Debug"
echo "   ./debug_mongodb.sh          # MongoDB-spezifisches Debug"
echo ""
echo "3. Logs prüfen:"
echo "   docker logs scandy-app-scandy -f"
echo "   docker logs scandy-app-verwaltung -f" 