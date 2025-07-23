#!/bin/bash

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Instance-Name aus .env extrahieren
INSTANCE_NAME=$(grep "DEPARTMENT=" .env | cut -d'=' -f2)
WEB_PORT=$(grep "WEB_PORT=" .env | cut -d'=' -f2)
MONGO_EXPRESS_PORT=$(grep "MONGO_EXPRESS_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "8081")

show_help() {
    echo "========================================"
    echo "Scandy $INSTANCE_NAME - Management"
    echo "========================================"
    echo
    echo "Verwendung: ./manage.sh [BEFEHL]"
    echo
    echo "Befehle:"
    echo "  start     - Container starten"
    echo "  stop      - Container stoppen"
    echo "  restart   - Container neustarten"
    echo "  status    - Status anzeigen"
    echo "  logs      - Logs anzeigen"
    echo "  update    - App aktualisieren"
    echo "  backup    - Backup erstellen"
    echo "  shell     - In App-Container wechseln"
    echo "  clean     - Container und Volumes löschen"
    echo "  info      - Instance-Informationen anzeigen"
    echo "  help      - Diese Hilfe anzeigen"
}

case "$1" in
    start)
        echo -e "${BLUE}🚀 Starte $INSTANCE_NAME...${NC}"
        docker compose up -d
        echo
        echo -e "${GREEN}✅ $INSTANCE_NAME gestartet!${NC}"
        echo
        echo "🌐 Verfügbare Services:"
        echo "- Web-App:     http://localhost:$WEB_PORT"
        echo "- Mongo Express: http://localhost:$MONGO_EXPRESS_PORT"
        echo
        echo "🔐 Standard-Zugangsdaten:"
        echo "- Benutzer: admin"
        echo "- Passwort: admin123"
        ;;
    stop)
        echo -e "${BLUE}🛑 Stoppe $INSTANCE_NAME...${NC}"
        docker compose down
        echo -e "${GREEN}✅ $INSTANCE_NAME gestoppt!${NC}"
        ;;
    restart)
        echo -e "${BLUE}🔄 Starte $INSTANCE_NAME neu...${NC}"
        docker compose restart
        echo -e "${GREEN}✅ $INSTANCE_NAME neugestartet!${NC}"
        ;;
    status)
        echo -e "${BLUE}📊 Status von $INSTANCE_NAME:${NC}"
        docker compose ps
        ;;
    logs)
        echo -e "${BLUE}📋 Logs von $INSTANCE_NAME:${NC}"
        docker compose logs -f
        ;;
    update)
        echo -e "${BLUE}🔄 Update $INSTANCE_NAME...${NC}"
        docker compose down
        docker compose build --no-cache
        docker compose up -d
        echo -e "${GREEN}✅ Update abgeschlossen!${NC}"
        ;;
    backup)
        echo -e "${BLUE}💾 Backup erstellen...${NC}"
        docker compose exec scandy-mongodb-$INSTANCE_NAME mongodump --out /backup
        echo -e "${GREEN}✅ Backup erstellt!${NC}"
        ;;
    shell)
        echo -e "${BLUE}🐚 Wechsle in App-Container...${NC}"
        docker compose exec scandy-app-$INSTANCE_NAME bash
        ;;
    clean)
        echo -e "${RED}⚠️  WARNUNG: Alle Daten werden gelöscht!${NC}"
        read -p "Sind Sie sicher? (j/N): " confirm
        if [[ $confirm =~ ^[Jj]$ ]]; then
            echo -e "${BLUE}🧹 Lösche Container und Volumes...${NC}"
            docker compose down -v
            docker system prune -f
            echo -e "${GREEN}✅ Bereinigung abgeschlossen!${NC}"
        else
            echo "Bereinigung abgebrochen."
        fi
        ;;
    info)
        echo -e "${BLUE}📋 Informationen zu $INSTANCE_NAME:${NC}"
        echo "Instance-Name: $INSTANCE_NAME"
        echo "Web-Port: $WEB_PORT"
        echo "MongoDB-Port: $(grep "MONGODB_PORT=" .env | cut -d'=' -f2)"
        echo "Mongo Express-Port: $MONGO_EXPRESS_PORT"
        echo "Datenbank: $(grep "MONGODB_DB=" .env | cut -d'=' -f2)"
        echo ""
        echo "Container:"
        docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        ;;
    help|*)
        show_help
        ;;
esac
