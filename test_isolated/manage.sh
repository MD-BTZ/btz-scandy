#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTANCE_NAME=$(basename "$PWD")

show_usage() {
    echo "Verwendung: $0 [BEFEHL]"
    echo ""
    echo "BEFEHLE:"
    echo "  start     Starte alle Container"
    echo "  stop      Stoppe alle Container"
    echo "  restart   Starte alle Container neu"
    echo "  status    Zeige Status aller Container"
    echo "  logs      Zeige Logs aller Container"
    echo "  shell     Öffne Shell im App-Container"
    echo "  backup    Erstelle Backup"
    echo "  update    Update die App"
    echo "  clean     Bereinige alte Daten"
    echo "  help      Zeige diese Hilfe"
}

case "$1" in
    start)
        echo -e "${BLUE}🚀 Starte $INSTANCE_NAME...${NC}"
        docker compose up -d
        ;;
    stop)
        echo -e "${BLUE}🛑 Stoppe $INSTANCE_NAME...${NC}"
        docker compose down
        ;;
    restart)
        echo -e "${BLUE}🔄 Starte $INSTANCE_NAME neu...${NC}"
        docker compose down
        docker compose up -d
        ;;
    status)
        echo -e "${BLUE}📊 Status von $INSTANCE_NAME:${NC}"
        docker compose ps
        ;;
    logs)
        echo -e "${BLUE}📋 Logs von $INSTANCE_NAME:${NC}"
        docker compose logs -f
        ;;
    shell)
        echo -e "${BLUE}🐚 Öffne Shell in $INSTANCE_NAME...${NC}"
        docker compose exec app-$INSTANCE_NAME bash
        ;;
    backup)
        echo -e "${BLUE}💾 Erstelle Backup von $INSTANCE_NAME...${NC}"
        docker compose exec app-$INSTANCE_NAME python -c "
from app.utils.backup_manager import backup_manager
backup_manager.create_backup()
print('Backup erstellt')
"
        ;;
    update)
        echo -e "${BLUE}🔄 Update $INSTANCE_NAME...${NC}"
        docker compose down
        docker compose build --no-cache app-$INSTANCE_NAME
        docker compose up -d
        ;;
    clean)
        echo -e "${BLUE}🧹 Bereinige $INSTANCE_NAME...${NC}"
        docker compose down
        docker volume prune -f
        docker compose up -d
        ;;
    help|*)
        show_usage
        ;;
esac
