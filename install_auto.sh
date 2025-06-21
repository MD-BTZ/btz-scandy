#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Feste Konfigurationswerte (keine Abfragen)
CONTAINER_NAME="scandy"
APP_PORT="5000"
MONGO_PORT="27017"
MONGO_EXPRESS_PORT="8081"
MONGO_USER="admin"
MONGO_PASS="scandy123"
DATA_DIR="./scandy_data"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Scandy Auto-Installer${NC}"
echo -e "${GREEN}   Automatische Installation ohne Abfragen${NC}"
echo -e "${GREEN}========================================${NC}"

# Funktion zur Überprüfung, ob ein Befehl existiert
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Prüfe Docker-Installation
if ! command_exists docker; then
    echo -e "${RED}Docker ist nicht installiert. Bitte installieren Sie Docker zuerst.${NC}"
    echo "Installationsanleitung: https://docs.docker.com/get-docker/"
    exit 1
fi

# Prüfe Docker Compose
if ! command_exists docker-compose; then
    echo -e "${RED}Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose zuerst.${NC}"
    echo "Installationsanleitung: https://docs.docker.com/compose/install/"
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Docker läuft nicht. Bitte starten Sie Docker zuerst.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker ist installiert und läuft${NC}"

# Zeige Konfiguration
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Konfiguration:${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Container Name: ${GREEN}$CONTAINER_NAME${NC}"
echo -e "App Port: ${GREEN}$APP_PORT${NC}"
echo -e "MongoDB Port: ${GREEN}$MONGO_PORT${NC}"
echo -e "Mongo Express Port: ${GREEN}$MONGO_EXPRESS_PORT${NC}"
echo -e "MongoDB User: ${GREEN}$MONGO_USER${NC}"
echo -e "Datenverzeichnis: ${GREEN}$DATA_DIR${NC}"
echo -e "${BLUE}========================================${NC}"

# Erstelle Datenverzeichnisse
echo -e "${GREEN}Erstelle Datenverzeichnisse...${NC}"
mkdir -p "${DATA_DIR}/mongodb"
mkdir -p "${DATA_DIR}/uploads"
mkdir -p "${DATA_DIR}/backups"
mkdir -p "${DATA_DIR}/logs"
mkdir -p "${DATA_DIR}/static"

# Kopiere statische Dateien
echo -e "${GREEN}Kopiere statische Dateien...${NC}"
cp -r app/static/* "${DATA_DIR}/static/" 2>/dev/null || echo -e "${YELLOW}Statische Dateien nicht gefunden, überspringe...${NC}"

# Erstelle docker-compose.yml
echo -e "${GREEN}Erstelle docker-compose.yml...${NC}"
cat > docker-compose.yml << EOL
version: '3.8'

services:
  mongodb:
    image: mongo:7.0
    container_name: ${CONTAINER_NAME}-mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASS}
      MONGO_INITDB_DATABASE: scandy
    ports:
      - "${MONGO_PORT}:27017"
    volumes:
      - ${DATA_DIR}/mongodb:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - scandy-network
    command: mongod --auth --bind_ip_all
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  mongo-express:
    image: mongo-express:1.0.0
    container_name: ${CONTAINER_NAME}-mongo-express
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: ${MONGO_USER}
      ME_CONFIG_MONGODB_ADMINPASSWORD: ${MONGO_PASS}
      ME_CONFIG_MONGODB_URL: mongodb://${MONGO_USER}:${MONGO_PASS}@mongodb:27017/
      ME_CONFIG_BASICAUTH_USERNAME: ${MONGO_USER}
      ME_CONFIG_BASICAUTH_PASSWORD: ${MONGO_PASS}
    ports:
      - "${MONGO_EXPRESS_PORT}:8081"
    depends_on:
      - mongodb
    networks:
      - scandy-network

  app:
    build: .
    container_name: ${CONTAINER_NAME}-app
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASS}@mongodb:27017/
      - MONGODB_DB=scandy
      - FLASK_ENV=production
      - SECRET_KEY=scandy-secret-key-fixed
      - SYSTEM_NAME=Scandy
      - TICKET_SYSTEM_NAME=Aufgaben
      - TOOL_SYSTEM_NAME=Werkzeuge
      - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
      - TZ=Europe/Berlin
    ports:
      - "${APP_PORT}:5000"
    volumes:
      - ${DATA_DIR}/uploads:/app/app/uploads
      - ${DATA_DIR}/backups:/app/app/backups
      - ${DATA_DIR}/logs:/app/app/logs
      - ${DATA_DIR}/static:/app/app/static
    depends_on:
      - mongodb
    networks:
      - scandy-network
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
  scandy_css_test-mongodb-data:
    driver: local

networks:
  scandy-network:
    driver: bridge
EOL

# Erstelle MongoDB Init-Skript
echo -e "${GREEN}Erstelle MongoDB Init-Skript...${NC}"
mkdir -p mongo-init
cat > mongo-init/init.js << EOL
// MongoDB Initialisierung
db = db.getSiblingDB('scandy');

// Erstelle Collections
db.createCollection('users');
db.createCollection('tools');
db.createCollection('consumables');
db.createCollection('workers');
db.createCollection('settings');
db.createCollection('tickets');
db.createCollection('lendings');

// Erstelle Indizes
db.users.createIndex({ "username": 1 }, { unique: true });
db.tools.createIndex({ "barcode": 1 }, { unique: true });
db.consumables.createIndex({ "barcode": 1 }, { unique: true });
db.workers.createIndex({ "barcode": 1 }, { unique: true });
db.tickets.createIndex({ "ticket_id": 1 }, { unique: true });

print('MongoDB Initialisierung abgeschlossen');
EOL

# Container stoppen falls vorhanden
echo -e "${GREEN}Stoppe vorhandene Container...${NC}"
docker-compose down --volumes --remove-orphans 2>/dev/null || true

# Entferne Container mit gleichen Namen falls vorhanden
echo -e "${GREEN}Bereinige vorhandene Container...${NC}"
docker rm -f ${CONTAINER_NAME}-mongodb ${CONTAINER_NAME}-app ${CONTAINER_NAME}-mongo-express 2>/dev/null || true

# Container bauen und starten
echo -e "${GREEN}Baue und starte Container...${NC}"
docker-compose up -d --build

# Warte auf Container-Start
echo -e "${GREEN}Warte auf Container-Start...${NC}"
sleep 30

# Prüfe Container-Status
echo -e "${GREEN}Prüfe Container-Status...${NC}"
docker-compose ps

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Installation abgeschlossen!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Scandy-Anwendung: ${BLUE}http://localhost:${APP_PORT}${NC}"
echo -e "MongoDB Express: ${BLUE}http://localhost:${MONGO_EXPRESS_PORT}${NC}"
echo -e "MongoDB Express Login: ${YELLOW}${MONGO_USER} / ${MONGO_PASS}${NC}"
echo -e ""
echo -e "Nützliche Befehle:"
echo -e "  Container-Status: ${YELLOW}docker-compose ps${NC}"
echo -e "  Logs anzeigen: ${YELLOW}docker-compose logs -f${NC}"
echo -e "  Container stoppen: ${YELLOW}docker-compose down${NC}"
echo -e "  Container neu starten: ${YELLOW}docker-compose restart${NC}"
echo -e "${GREEN}========================================${NC}" 