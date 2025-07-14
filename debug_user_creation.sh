#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Debug: Benutzer-Erstellung in Multi-Instance Setup${NC}"
echo "========================================"

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -f "app/routes/admin.py" ]; then
    echo -e "${RED}❌ Bitte führen Sie dieses Skript im Scandy-Hauptverzeichnis aus!${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Prüfe Multi-Instance Setup...${NC}"

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
echo -e "${BLUE}🐳 Container-Status prüfen...${NC}"

# Prüfe Container-Status für alle Instanzen
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📊 Haupt-Instanz:${NC}"
        if [ -f "docker-compose.yml" ]; then
            docker compose ps 2>/dev/null || echo "  Keine Container gefunden"
        else
            echo "  Keine docker-compose.yml gefunden"
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📊 $instance_dir:${NC}"
        if [ -f "$instance_dir/docker-compose.yml" ]; then
            cd "$instance_dir"
            docker compose ps 2>/dev/null || echo "  Keine Container gefunden"
            cd ..
        else
            echo "  Keine docker-compose.yml gefunden"
        fi
    fi
done

echo ""
echo -e "${BLUE}💾 Datenbank-Verbindungen prüfen...${NC}"

# Prüfe MongoDB-Verbindungen
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📊 Haupt-Instanz MongoDB:${NC}"
        if [ -f ".env" ]; then
            mongo_port=$(grep "MONGODB_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "27017")
            echo "  Port: $mongo_port"
            
            # Prüfe MongoDB-Verbindung
            if docker ps | grep -q "scandy-mongodb"; then
                echo "  ✅ MongoDB Container läuft"
                
                # Prüfe Benutzer in der Datenbank
                echo "  📋 Benutzer in der Datenbank:"
                docker exec scandy-mongodb-scandy mongosh --eval "db.users.find({}, {username: 1, role: 1, is_active: 1}).pretty()" 2>/dev/null || echo "    Fehler beim Abfragen der Benutzer"
            else
                echo "  ❌ MongoDB Container läuft nicht"
            fi
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📊 $instance_dir MongoDB:${NC}"
        if [ -f "$instance_dir/.env" ]; then
            mongo_port=$(grep "MONGODB_PORT=" "$instance_dir/.env" | cut -d'=' -f2 2>/dev/null || echo "27017")
            echo "  Port: $mongo_port"
            
            # Prüfe MongoDB-Verbindung
            container_name="scandy-mongodb-$instance_dir"
            if docker ps | grep -q "$container_name"; then
                echo "  ✅ MongoDB Container läuft"
                
                # Prüfe Benutzer in der Datenbank
                echo "  📋 Benutzer in der Datenbank:"
                docker exec "$container_name" mongosh --eval "db.users.find({}, {username: 1, role: 1, is_active: 1}).pretty()" 2>/dev/null || echo "    Fehler beim Abfragen der Benutzer"
            else
                echo "  ❌ MongoDB Container läuft nicht"
            fi
        fi
    fi
done

echo ""
echo -e "${BLUE}🔧 Session-Status prüfen...${NC}"

# Prüfe Session-Verzeichnisse
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📊 Haupt-Instanz Sessions:${NC}"
        if [ -d "app/flask_session" ]; then
            session_count=$(find app/flask_session -name "*.session" 2>/dev/null | wc -l)
            echo "  Session-Dateien: $session_count"
        else
            echo "  Kein Session-Verzeichnis gefunden"
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📊 $instance_dir Sessions:${NC}"
        if [ -d "$instance_dir/app/flask_session" ]; then
            session_count=$(find "$instance_dir/app/flask_session" -name "*.session" 2>/dev/null | wc -l)
            echo "  Session-Dateien: $session_count"
        else
            echo "  Kein Session-Verzeichnis gefunden"
        fi
    fi
done

echo ""
echo -e "${BLUE}🌐 Web-App-Status prüfen...${NC}"

# Prüfe Web-App-Verfügbarkeit
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📊 Haupt-Instanz Web-App:${NC}"
        if [ -f ".env" ]; then
            web_port=$(grep "WEB_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "5000")
            echo "  Port: $web_port"
            
            # Prüfe Web-App-Verfügbarkeit
            if curl -s "http://localhost:$web_port/health" >/dev/null 2>&1; then
                echo "  ✅ Web-App erreichbar"
            else
                echo "  ❌ Web-App nicht erreichbar"
            fi
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📊 $instance_dir Web-App:${NC}"
        if [ -f "$instance_dir/.env" ]; then
            web_port=$(grep "WEB_PORT=" "$instance_dir/.env" | cut -d'=' -f2 2>/dev/null || echo "5000")
            echo "  Port: $web_port"
            
            # Prüfe Web-App-Verfügbarkeit
            if curl -s "http://localhost:$web_port/health" >/dev/null 2>&1; then
                echo "  ✅ Web-App erreichbar"
            else
                echo "  ❌ Web-App nicht erreichbar"
            fi
        fi
    fi
done

echo ""
echo -e "${GREEN}✅ Debug abgeschlossen!${NC}"
echo ""
echo -e "${YELLOW}💡 Mögliche Lösungen:${NC}"
echo ""
echo "1. Bei Session-Problemen:"
echo "   ./fix_email_session.sh"
echo "   ./cleanup_sessions.sh"
echo ""
echo "2. Bei Container-Problemen:"
echo "   ./manage.sh restart"
echo "   cd verwaltung && ./manage.sh restart"
echo ""
echo "3. Bei Datenbank-Problemen:"
echo "   ./debug_mongodb.sh"
echo ""
echo "4. Bei Web-App-Problemen:"
echo "   docker logs scandy-app-scandy -f"
echo "   docker logs scandy-app-verwaltung -f" 