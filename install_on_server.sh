#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}----------------------------------------${NC}"
echo -e "${GREEN}   Scandy Docker-Installer (Linux)${NC}"
echo -e "${GREEN}----------------------------------------${NC}"

# Prüfe, ob Docker installiert ist
if ! command -v docker >/dev/null 2>&1; then
  echo "FEHLER: Docker ist nicht installiert!"
  echo "Bitte installiere Docker zuerst: https://docs.docker.com/get-docker/"
  exit 1
fi

# Prüfe, ob Docker Compose installiert ist
if ! command -v docker-compose >/dev/null 2>&1; then
  echo "FEHLER: Docker Compose ist nicht installiert!"
  echo "Bitte installiere Docker Compose zuerst: https://docs.docker.com/compose/install/"
  exit 1
fi

# Container-Name abfragen
read -p "Wie soll der Container heißen? [scandy]: " CONTAINER_NAME
CONTAINER_NAME=${CONTAINER_NAME:-scandy}

# Port abfragen
read -p "Welcher Port soll für die App freigegeben werden? [5000]: " PORT
PORT=${PORT:-5000}

# MongoDB Port abfragen
read -p "Welcher Port soll für MongoDB freigegeben werden? [27017]: " MONGO_PORT
MONGO_PORT=${MONGO_PORT:-27017}

# Mongo Express Port abfragen
read -p "Welcher Port soll für Mongo Express freigegeben werden? [8081]: " MONGO_EXPRESS_PORT
MONGO_EXPRESS_PORT=${MONGO_EXPRESS_PORT:-8081}

# Datenverzeichnis abfragen
read -p "Wo sollen die Daten (Datenbank/Backups) gespeichert werden? [./scandy_data]: " DATA_DIR
DATA_DIR=${DATA_DIR:-./scandy_data}

# Repo auf dem Host klonen
if [ ! -d "scandy2" ]; then
  echo -e "${GREEN}Klone das Repository...${NC}"
  git clone https://github.com/woschj/scandy2.git scandy2
else
  echo -e "${GREEN}Repository existiert bereits. Überspringe Klonen.${NC}"
fi

# Datenverzeichnis erstellen
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/mongodb"
mkdir -p "$DATA_DIR/uploads"
mkdir -p "$DATA_DIR/backups"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/static"

# Kopiere statische Dateien
echo -e "${GREEN}Kopiere statische Dateien...${NC}"
cp -r scandy2/app/static/* "$DATA_DIR/static/"

# Erstelle docker-compose.yml
echo -e "${GREEN}Erstelle docker-compose.yml...${NC}"
cat > docker-compose.yml << EOL
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
      - ${DATA_DIR}/mongodb:/data/db
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
    build: ./scandy2
    container_name: ${CONTAINER_NAME}-app
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=mongodb://admin:scandy123@${CONTAINER_NAME}-mongodb:27017/
      - MONGODB_DB=scandy
      - FLASK_ENV=production
      - SECRET_KEY=scandy-secret-key-fixed
      - SYSTEM_NAME=Scandy
      - TICKET_SYSTEM_NAME=Aufgaben
      - TOOL_SYSTEM_NAME=Werkzeuge
      - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
      - TZ=Europe/Berlin
    ports:
      - "${PORT}:5000"
    volumes:
      - ${DATA_DIR}/uploads:/app/app/uploads
      - ${DATA_DIR}/backups:/app/app/backups
      - ${DATA_DIR}/logs:/app/app/logs
      - ${DATA_DIR}/static:/app/app/static
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
  ${CONTAINER_NAME}-mongodb-data:
    driver: local

networks:
  ${CONTAINER_NAME}-network:
    driver: bridge
EOL

# Erstelle MongoDB Init-Skript
echo -e "${GREEN}Erstelle MongoDB Init-Skript...${NC}"
mkdir -p mongo-init
cat > mongo-init/init.js << EOL
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
EOL

# Container stoppen/löschen, falls sie schon existieren
echo -e "${GREEN}Stoppe alte Container...${NC}"
docker-compose down --volumes --remove-orphans 2>/dev/null || true

echo -e "${GREEN}Starte alle Container (MongoDB, Mongo Express, App)...${NC}"
echo -e "${GREEN}Daten werden gespeichert in: $DATA_DIR${NC}"

# Starte alle Container mit Docker Compose
docker-compose up -d --build

echo -e "${GREEN}----------------------------------------${NC}"
echo -e "${GREEN}FERTIG! Alle Scandy-Container laufen jetzt:${NC}"
echo -e "${GREEN}• App: http://localhost:$PORT${NC}"
echo -e "${GREEN}• MongoDB: localhost:$MONGO_PORT${NC}"
echo -e "${GREEN}• Mongo Express (Web-UI): http://localhost:$MONGO_EXPRESS_PORT${NC}"
echo -e "${GREEN}----------------------------------------${NC}"