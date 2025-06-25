#!/bin/bash

# Scandy Ein-Klick-Installation
# MongoDB + App Container Setup

set -e

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Scandy Ein-Klick-Installation${NC}"
echo -e "${GREEN}   MongoDB + App Container Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Prüfe Docker-Installation
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker ist nicht installiert. Bitte installieren Sie Docker zuerst.${NC}"
    echo "Installationsanleitung: https://docs.docker.com/get-docker/"
    exit 1
fi

# Prüfe Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose zuerst.${NC}"
    echo "Installationsanleitung: https://docs.docker.com/compose/install/"
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker läuft nicht. Bitte starten Sie Docker zuerst.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker ist installiert und läuft${NC}"

# Container-Name Abfrage
read -p "Bitte geben Sie einen Namen für die Umgebung ein (Standard: scandy): " CONTAINER_NAME
if [ -z "$CONTAINER_NAME" ]; then
    CONTAINER_NAME="scandy"
fi

# App-Port Abfrage
read -p "Bitte geben Sie den Port für die App ein (Standard: 5000): " APP_PORT
if [ -z "$APP_PORT" ]; then
    APP_PORT="5000"
fi

# MongoDB-Port Abfrage
read -p "Bitte geben Sie den Port für MongoDB ein (Standard: 27017): " MONGO_PORT
if [ -z "$MONGO_PORT" ]; then
    MONGO_PORT="27017"
fi

# Mongo Express Port Abfrage
read -p "Bitte geben Sie den Port für Mongo Express (Web-UI) ein (Standard: 8081): " MONGO_EXPRESS_PORT
if [ -z "$MONGO_EXPRESS_PORT" ]; then
    MONGO_EXPRESS_PORT="8081"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Konfiguration:${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Container Name: ${GREEN}$CONTAINER_NAME${NC}"
echo -e "App Port: ${GREEN}$APP_PORT${NC}"
echo -e "MongoDB Port: ${GREEN}$MONGO_PORT${NC}"
echo -e "Mongo Express Port: ${GREEN}$MONGO_EXPRESS_PORT${NC}"
echo -e "${BLUE}========================================${NC}"

read -p "Möchten Sie mit der Installation fortfahren? (j/n): " confirm
if [[ ! "$confirm" =~ ^[Jj]$ ]]; then
    echo -e "${YELLOW}Installation abgebrochen.${NC}"
    exit 0
fi

# Erstelle Projektverzeichnis
PROJECT_DIR="${CONTAINER_NAME}_project"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo -e "${GREEN}Erstelle Projektverzeichnis: $PROJECT_DIR${NC}"

# Erstelle docker-compose.yml
echo -e "${GREEN}Erstelle docker-compose.yml...${NC}"
cat > docker-compose.yml << EOF
version: '3.8'

services:
  ${CONTAINER_NAME}-mongodb:
    image: mongo:7.0
    container_name: ${CONTAINER_NAME}-mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: scandy123
      MONGO_INITDB_DATABASE: scandy
    ports:
      - "${MONGO_PORT}:27017"
    volumes:
      - mongodb_data:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - ${CONTAINER_NAME}-network
    command: mongod --auth --bind_ip_all
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  ${CONTAINER_NAME}-mongo-express:
    image: mongo-express:1.0.0
    container_name: ${CONTAINER_NAME}-mongo-express
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: scandy123
      ME_CONFIG_MONGODB_URL: mongodb://admin:scandy123@${CONTAINER_NAME}-mongodb:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: scandy123
    ports:
      - "${MONGO_EXPRESS_PORT}:8081"
    depends_on:
      ${CONTAINER_NAME}-mongodb:
        condition: service_healthy
    networks:
      - ${CONTAINER_NAME}-network

  ${CONTAINER_NAME}-app:
    image: woschj/scandy:latest
    container_name: ${CONTAINER_NAME}-app
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=mongodb://admin:scandy123@${CONTAINER_NAME}-mongodb:27017/
      - MONGODB_DB=scandy
      - FLASK_ENV=production
      - SECRET_KEY=scandy-secret-key-change-in-production
      - SYSTEM_NAME=Scandy
      - TICKET_SYSTEM_NAME=Aufgaben
      - TOOL_SYSTEM_NAME=Werkzeuge
      - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
      - TZ=Europe/Berlin
    ports:
      - "${APP_PORT}:5000"
    volumes:
      - app_uploads:/app/app/uploads
      - app_backups:/app/app/backups
      - app_logs:/app/app/logs
      - app_static:/app/app/static
    depends_on:
      ${CONTAINER_NAME}-mongodb:
        condition: service_healthy
    networks:
      - ${CONTAINER_NAME}-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  mongodb_data:
    driver: local
  app_uploads:
    driver: local
  app_backups:
    driver: local
  app_logs:
    driver: local
  app_static:
    driver: local

networks:
  ${CONTAINER_NAME}-network:
    driver: bridge
EOF

# Erstelle MongoDB Init-Skript
echo -e "${GREEN}Erstelle MongoDB Init-Skript...${NC}"
mkdir -p mongo-init
cat > mongo-init/init.js << EOF
// MongoDB Initialisierung für Scandy
db = db.getSiblingDB('scandy');

// Erstelle Collections
db.createCollection('tools');
db.createCollection('consumables');
db.createCollection('workers');
db.createCollection('lendings');
db.createCollection('users');
db.createCollection('tickets');
db.createCollection('settings');
db.createCollection('system_logs');

// Erstelle Indizes
db.tools.createIndex({ "barcode": 1 }, { unique: true });
db.tools.createIndex({ "deleted": 1 });
db.tools.createIndex({ "status": 1 });

db.consumables.createIndex({ "barcode": 1 }, { unique: true });
db.consumables.createIndex({ "deleted": 1 });

db.workers.createIndex({ "barcode": 1 }, { unique: true });
db.workers.createIndex({ "deleted": 1 });

db.lendings.createIndex({ "tool_barcode": 1 });
db.lendings.createIndex({ "worker_barcode": 1 });
db.lendings.createIndex({ "returned_at": 1 });

db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { sparse: true });

db.tickets.createIndex({ "created_at": 1 });
db.tickets.createIndex({ "status": 1 });
db.tickets.createIndex({ "assigned_to": 1 });

print('MongoDB für Scandy initialisiert!');
EOF

# Erstelle Verwaltungsskripte
echo -e "${GREEN}Erstelle Verwaltungsskripte...${NC}"

# Start-Skript
cat > start.sh << EOF
#!/bin/bash
echo "Starte Scandy Docker-Container..."
docker-compose up -d

echo "Warte auf Container-Start..."
sleep 10

echo "Container-Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "Scandy ist verfügbar unter:"
echo "App: http://localhost:${APP_PORT}"
echo "Mongo Express: http://localhost:${MONGO_EXPRESS_PORT}"
echo "MongoDB: localhost:${MONGO_PORT}"
echo "=========================================="
EOF

# Stop-Skript
cat > stop.sh << EOF
#!/bin/bash
echo "Stoppe Scandy Docker-Container..."
docker-compose down

echo "Container gestoppt."
EOF

# Update-Skript
cat > update.sh << EOF
#!/bin/bash
echo "Update Scandy Docker-Container..."

# Stoppe Container
docker-compose down

# Pull neueste Images
docker-compose pull

# Starte Container
docker-compose up -d

echo "Update abgeschlossen!"
EOF

# Backup-Skript
cat > backup.sh << EOF
#!/bin/bash
BACKUP_DIR="./backups"
TIMESTAMP=\$(date +%Y%m%d_%H%M%S)

echo "Erstelle Backup..."

# Erstelle Backup-Verzeichnis
mkdir -p "\$BACKUP_DIR"

# MongoDB Backup
echo "Backup MongoDB..."
docker exec ${CONTAINER_NAME}-mongodb mongodump --out /tmp/backup
docker cp ${CONTAINER_NAME}-mongodb:/tmp/backup "\$BACKUP_DIR/mongodb_\$TIMESTAMP"

# App-Daten Backup
echo "Backup App-Daten..."
docker run --rm -v ${CONTAINER_NAME}_app_uploads:/data -v \$(pwd)/\$BACKUP_DIR:/backup alpine tar -czf /backup/app_data_\$TIMESTAMP.tar.gz -C /data .

echo "Backup erstellt: \$BACKUP_DIR"
EOF

# Setze Berechtigungen
chmod +x start.sh stop.sh update.sh backup.sh

# Baue und starte Container
echo -e "${GREEN}Baue und starte Container...${NC}"
docker-compose down --volumes --remove-orphans
docker-compose up -d

echo "========================================"
echo -e "${GREEN}Installation abgeschlossen!${NC}"
echo "Die Anwendung ist unter http://localhost:${APP_PORT} erreichbar"
echo "Container-Name: ${CONTAINER_NAME}"
echo "MongoDB Port: ${MONGO_PORT}"
echo "Mongo Express Port: ${MONGO_EXPRESS_PORT}"
echo "========================================"
echo ""
echo -e "${YELLOW}Verwaltung:${NC}"
echo "  Starten: ./start.sh"
echo "  Stoppen: ./stop.sh"
echo "  Update:  ./update.sh"
echo "  Backup:  ./backup.sh" 