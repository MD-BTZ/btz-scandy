#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
show_help() {
    echo "========================================"
    echo "Scandy Installer"
    echo "========================================"
    echo
    echo "Verwendung: ./install_unified.sh [OPTIONEN]"
    echo
    echo "Optionen:"
    echo "  -h, --help              Diese Hilfe anzeigen"
    echo "  -n, --name NAME         Instance-Name (Standard: scandy)"
    echo "  -p, --port PORT         Web-App Port (Standard: 5000)"
    echo "  -m, --mongodb-port PORT MongoDB Port (Standard: 27017)"
    echo "  -e, --express-port PORT Mongo Express Port (Standard: 8081)"
    echo "  -f, --force             Bestehende Installation überschreiben"
    echo "  -u, --update            Nur App aktualisieren"
    echo
    echo "Beispiele:"
    echo "  ./install_unified.sh                    # Standard-Installation"
    echo "  ./install_unified.sh -n verwaltung     # Instance 'verwaltung'"
    echo "  ./install_unified.sh -p 8080 -m 27018  # Custom Ports"
    echo "  ./install_unified.sh -u                # Nur Update"
}

# Variablen initialisieren
WEB_PORT=5000
MONGODB_PORT=27017
MONGO_EXPRESS_PORT=8081
INSTANCE_NAME="scandy"
FORCE=false
UPDATE_ONLY=false

# Argumente parsen
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--name)
            INSTANCE_NAME="$2"
            shift 2
            ;;
        -p|--port)
            WEB_PORT="$2"
            shift 2
            ;;
        -m|--mongodb-port)
            MONGODB_PORT="$2"
            shift 2
            ;;
        -e|--express-port)
            MONGO_EXPRESS_PORT="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -u|--update)
            UPDATE_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unbekannte Option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Logging-Funktion
log() {
    echo -e "$1"
}

# Prüfe Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        log "${RED}❌ ERROR: Docker ist nicht installiert!${NC}"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log "${RED}❌ ERROR: Docker läuft nicht!${NC}"
        exit 1
    fi
    
    log "${GREEN}✅ Docker ist verfügbar${NC}"
}

# Automatische Port-Berechnung
calculate_ports() {
    if [ "$INSTANCE_NAME" != "scandy" ]; then
        # Extrahiere Nummer aus Instance-Name
        INSTANCE_NUMBER=$(echo "$INSTANCE_NAME" | tr -cd '0-9' | sed 's/^0*//')
        if [ -z "$INSTANCE_NUMBER" ]; then
            INSTANCE_NUMBER=1
        fi
        
        # Berechne Ports nur wenn sie nicht explizit gesetzt wurden
        if [ "$WEB_PORT" = "5000" ]; then
            WEB_PORT=$((5000 + INSTANCE_NUMBER))
        fi
        if [ "$MONGODB_PORT" = "27017" ]; then
            MONGODB_PORT=$((27017 + INSTANCE_NUMBER))
        fi
        if [ "$MONGO_EXPRESS_PORT" = "8081" ]; then
            MONGO_EXPRESS_PORT=$((8081 + INSTANCE_NUMBER))
        fi
    fi
}

# Prüfe Port-Konflikte
check_port_conflicts() {
    log "${BLUE}🔍 Prüfe Port-Verfügbarkeit...${NC}"
    
    local conflicts=()
    
    # Prüfe Web-Port
    if lsof -Pi :$WEB_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        conflicts+=("Web-App Port $WEB_PORT")
    fi
    
    # Prüfe MongoDB-Port
    if lsof -Pi :$MONGODB_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        conflicts+=("MongoDB Port $MONGODB_PORT")
    fi
    
    # Prüfe Mongo Express-Port
    if lsof -Pi :$MONGO_EXPRESS_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        conflicts+=("Mongo Express Port $MONGO_EXPRESS_PORT")
    fi
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        log "${YELLOW}⚠️  Port-Konflikte gefunden:${NC}"
        for conflict in "${conflicts[@]}"; do
            log "${YELLOW}   - $conflict${NC}"
        done
        
        if [ "$FORCE" = false ]; then
            log "${RED}❌ Installation abgebrochen. Verwende --force zum Überschreiben.${NC}"
            exit 1
        else
            log "${YELLOW}⚠️  Fahre mit --force fort...${NC}"
        fi
    else
        log "${GREEN}✅ Alle Ports verfügbar${NC}"
    fi
}

# Erstelle .env-Datei
create_env() {
    log "${BLUE}📝 Erstelle .env-Datei...${NC}"
    
    # Generiere sicheres Passwort
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    
    cat > .env << EOF
# Scandy $INSTANCE_NAME Konfiguration
DEPARTMENT=$INSTANCE_NAME
DEPARTMENT_NAME=$INSTANCE_NAME
WEB_PORT=$WEB_PORT
MONGODB_PORT=$MONGODB_PORT

# MongoDB Konfiguration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=$DB_PASSWORD
MONGO_INITDB_DATABASE=${INSTANCE_NAME}_scandy
MONGODB_URI=mongodb://admin:$DB_PASSWORD@scandy-mongodb-$INSTANCE_NAME:27017/${INSTANCE_NAME}_scandy?authSource=admin
MONGODB_DB=${INSTANCE_NAME}_scandy

# System-Namen
SYSTEM_NAME=Scandy $INSTANCE_NAME
TICKET_SYSTEM_NAME=Aufgaben $INSTANCE_NAME
TOOL_SYSTEM_NAME=Werkzeuge $INSTANCE_NAME
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter $INSTANCE_NAME

# Sicherheit
SECRET_KEY=$SECRET_KEY
SESSION_COOKIE_SECURE=False
REMEMBER_COOKIE_SECURE=False

# Container-Namen
CONTAINER_NAME=scandy-$INSTANCE_NAME
TZ=Europe/Berlin
FLASK_ENV=production
DATABASE_MODE=mongodb
EOF

    log "${GREEN}✅ .env-Datei erstellt${NC}"
}

# Erstelle docker-compose.yml
create_docker_compose() {
    log "${BLUE}🐳 Erstelle docker-compose.yml...${NC}"
    
    cat > docker-compose.yml << EOF
services:
  scandy-mongodb-$INSTANCE_NAME:
    image: mongo:7
    container_name: scandy-mongodb-$INSTANCE_NAME
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      MONGO_INITDB_DATABASE: \${MONGO_INITDB_DATABASE}
    ports:
      - "$MONGODB_PORT:27017"
    volumes:
      - mongodb_data_$INSTANCE_NAME:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - scandy-network-$INSTANCE_NAME
    command: mongod --bind_ip_all
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 10s
      retries: 15
      start_period: 30s
    env_file:
      - .env

  scandy-mongo-express-$INSTANCE_NAME:
    image: mongo-express:1.0.0
    container_name: scandy-mongo-express-$INSTANCE_NAME
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      ME_CONFIG_MONGODB_URL: mongodb://admin:\${MONGO_INITDB_ROOT_PASSWORD}@scandy-mongodb-$INSTANCE_NAME:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
    ports:
      - "$MONGO_EXPRESS_PORT:8081"
    depends_on:
      scandy-mongodb-$INSTANCE_NAME:
        condition: service_healthy
    networks:
      - scandy-network-$INSTANCE_NAME
    env_file:
      - .env

  scandy-app-$INSTANCE_NAME:
    build:
      context: .
      dockerfile: Dockerfile
    image: scandy-local:dev-$INSTANCE_NAME
    container_name: scandy-app-$INSTANCE_NAME
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=\${MONGODB_URI}
      - MONGODB_DB=\${MONGODB_DB}
      - FLASK_ENV=production
      - SECRET_KEY=\${SECRET_KEY}
      - SYSTEM_NAME=\${SYSTEM_NAME}
      - TICKET_SYSTEM_NAME=\${TICKET_SYSTEM_NAME}
      - TOOL_SYSTEM_NAME=\${TOOL_SYSTEM_NAME}
      - CONSUMABLE_SYSTEM_NAME=\${CONSUMABLE_SYSTEM_NAME}
      - CONTAINER_NAME=\${CONTAINER_NAME}
      - TZ=Europe/Berlin
      - SESSION_COOKIE_SECURE=False
      - REMEMBER_COOKIE_SECURE=False
    ports:
      - "$WEB_PORT:5000"
    volumes:
      - ./app:/app/app
      - app_uploads_$INSTANCE_NAME:/app/app/uploads
      - app_backups_$INSTANCE_NAME:/app/app/backups
      - app_logs_$INSTANCE_NAME:/app/app/logs
      - app_sessions_$INSTANCE_NAME:/app/app/flask_session
    depends_on:
      scandy-mongodb-$INSTANCE_NAME:
        condition: service_healthy
    networks:
      - scandy-network-$INSTANCE_NAME
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    env_file:
      - .env

volumes:
  mongodb_data_$INSTANCE_NAME:
    driver: local
  app_uploads_$INSTANCE_NAME:
    driver: local
  app_backups_$INSTANCE_NAME:
    driver: local
  app_logs_$INSTANCE_NAME:
    driver: local
  app_sessions_$INSTANCE_NAME:
    driver: local

networks:
  scandy-network-$INSTANCE_NAME:
    driver: bridge
EOF

    log "${GREEN}✅ docker-compose.yml erstellt${NC}"
}

# Erstelle Management-Skript
create_management_script() {
    log "${BLUE}🔧 Erstelle Management-Skript...${NC}"
    
    cat > manage.sh << 'EOF'
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
EOF

    chmod +x manage.sh
    log "${GREEN}✅ Management-Skript erstellt${NC}"
}

# Erstelle Verzeichnisse
create_directories() {
    log "${BLUE}📁 Erstelle Verzeichnisse...${NC}"
    mkdir -p data/backups data/logs data/static data/uploads backups logs mongo-init
    log "${GREEN}✅ Verzeichnisse erstellt${NC}"
}

# Installiere Container
install_containers() {
    log "${BLUE}🔨 Baue und starte Container...${NC}"
    
    # Stoppe bestehende Container
    docker compose down -v &> /dev/null
    
    # Baue und starte
    docker compose up -d --build
    
    if [ $? -ne 0 ]; then
        log "${RED}❌ ERROR: Installation fehlgeschlagen!${NC}"
        exit 1
    fi
    
    log "${GREEN}✅ Container gestartet${NC}"
    
    # Korrigiere Berechtigungen für Static Files
    log "${BLUE}🔧 Korrigiere Berechtigungen für Static Files...${NC}"
    if [ -d "app/static" ]; then
        chmod -R 755 app/static/
        log "${GREEN}✅ Static Files Berechtigungen korrigiert${NC}"
    fi
    
    # Korrigiere Berechtigungen für Upload-Verzeichnis
    if [ -d "data/uploads" ]; then
        chmod -R 755 data/uploads/
        log "${GREEN}✅ Upload-Verzeichnis Berechtigungen korrigiert${NC}"
    fi
}

# Warte auf Services
wait_for_services() {
    log "${BLUE}⏳ Warte auf Service-Start...${NC}"
    
    # Warte auf MongoDB
    local retries=0
    while [ $retries -lt 12 ]; do
        if docker ps | grep -q scandy-mongodb-$INSTANCE_NAME; then
            break
        fi
        log "${YELLOW}⏳ MongoDB Container startet noch...${NC}"
        sleep 5
        ((retries++))
    done
    
    # Prüfe Health Status
    local health_retries=0
    while [ $health_retries -lt 15 ]; do
        health_status=$(docker inspect -f "{{.State.Health.Status}}" scandy-mongodb-$INSTANCE_NAME 2>/dev/null)
        if [ "$health_status" = "healthy" ]; then
            log "${GREEN}✅ MongoDB ist healthy!${NC}"
            break
        fi
        ((health_retries++))
        if [ $health_retries -ge 15 ]; then
            log "${YELLOW}⚠️  MongoDB wird nicht healthy - fahre trotzdem fort...${NC}"
            break
        fi
        log "${YELLOW}⏳ Warte auf MongoDB Health... ($health_retries/15)${NC}"
        sleep 6
    done
}

# Zeige finale Informationen
show_final_info() {
    log ""
    log "========================================"
    log "${GREEN}✅ INSTALLATION ABGESCHLOSSEN!${NC}"
    log "========================================"
    log ""
    log "${GREEN}🎉 $INSTANCE_NAME ist installiert und verfügbar:${NC}"
    log ""
    log "${BLUE}🌐 Web-Anwendungen:${NC}"
    log "- Scandy App:     http://localhost:$WEB_PORT"
    log "- Mongo Express:  http://localhost:$MONGO_EXPRESS_PORT"
    log ""
    log "${BLUE}🔐 Standard-Zugangsdaten:${NC}"
    log "- Admin: admin / admin123"
    log "- Teilnehmer: teilnehmer / admin123"
    log ""
    log "${BLUE}🔧 Management-Befehle:${NC}"
    log "- Status:         ./manage.sh status"
    log "- Logs:           ./manage.sh logs"
    log "- Stoppen:        ./manage.sh stop"
    log "- Neustart:       ./manage.sh restart"
    log "- Update:         ./manage.sh update"
    log "- Backup:         ./manage.sh backup"
    log "- Shell:          ./manage.sh shell"
    log "- Info:           ./manage.sh info"
    log "- Bereinigung:    ./manage.sh clean"
    log ""
    log "${YELLOW}⚠️  WICHTIG: Ändere die Passwörter in .env für Produktion!${NC}"
    log ""
    log "========================================"
}

# Hauptfunktion
main() {
    log "========================================"
    log "Scandy Installer"
    log "========================================"
    log "Instance: $INSTANCE_NAME"
    log "Web-Port: $WEB_PORT"
    log "MongoDB-Port: $MONGODB_PORT"
    log "Mongo Express-Port: $MONGO_EXPRESS_PORT"
    log "========================================"
    log ""
    
    # Prüfe Docker
    check_docker
    
    # Update-Modus
    if [ "$UPDATE_ONLY" = true ]; then
        log "${BLUE}🔄 Update-Modus: Nur App aktualisieren...${NC}"
        if [ -f "docker-compose.yml" ]; then
            docker compose down
            docker compose build --no-cache
            docker compose up -d
            log "${GREEN}✅ Update abgeschlossen!${NC}"
        else
            log "${RED}❌ Keine bestehende Installation gefunden!${NC}"
            exit 1
        fi
        return
    fi
    
    # Berechne Ports
    calculate_ports
    
    # Prüfe Port-Konflikte
    check_port_conflicts
    
    # Prüfe bestehende Installation
    if [ -f "docker-compose.yml" ] && [ "$FORCE" = false ]; then
        log "${YELLOW}⚠️  Bestehende Installation gefunden!${NC}"
        log ""
        log "Optionen:"
        log "1 = Abbrechen"
        log "2 = Komplett neu installieren (ALLE Daten gehen verloren!)"
        log "3 = Nur App neu installieren (Daten bleiben erhalten)"
        log ""
        read -p "Wählen Sie (1-3): " choice
        
        case $choice in
            1)
                log "Installation abgebrochen."
                exit 0
                ;;
            2)
                log "${RED}⚠️  KOMPLETT NEU INSTALLIEREN - ALLE DATEN GEHEN VERLOREN!${NC}"
                read -p "Sind Sie sicher? (j/N): " confirm
                if [[ ! $confirm =~ ^[Jj]$ ]]; then
                    log "Installation abgebrochen."
                    exit 0
                fi
                log "${BLUE}🔄 Komplett neu installieren...${NC}"
                docker compose down -v
                docker system prune -f
                [ -d "data" ] && rm -rf data
                [ -d "backups" ] && rm -rf backups
                [ -d "logs" ] && rm -rf logs
                ;;
            3)
                log "${BLUE}🔄 Nur App neu installieren...${NC}"
                docker compose down
                docker compose build --no-cache
                docker compose up -d
                log "${GREEN}✅ Update abgeschlossen!${NC}"
                exit 0
                ;;
            *)
                log "Ungültige Auswahl. Installation abgebrochen."
                exit 1
                ;;
        esac
    fi
    
    # Erstelle Verzeichnisse
    create_directories
    
    # Erstelle Konfigurationsdateien
    create_env
    create_docker_compose
    create_management_script
    
    # Installiere Container
    install_containers
    
    # Warte auf Services
    wait_for_services
    
    # Zeige finale Informationen
    show_final_info
}

# Skript ausführen
main "$@" 