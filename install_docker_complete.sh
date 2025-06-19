#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktion zur Überprüfung, ob ein Befehl existiert
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Funktion zum Überprüfen, ob ein Port verfügbar ist
check_port() {
    if command_exists netstat; then
        netstat -tuln | grep -q ":$1 "
        return $?
    elif command_exists ss; then
        ss -tuln | grep -q ":$1 "
        return $?
    else
        echo -e "${YELLOW}WARNUNG: Kann Port-Verfügbarkeit nicht prüfen. Bitte stellen Sie sicher, dass Port $1 frei ist.${NC}"
        return 0
    fi
}

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Scandy Docker-Installer (Vollständig)${NC}"
echo -e "${GREEN}   MongoDB + App Container Setup${NC}"
echo -e "${GREEN}========================================${NC}"

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

# Container-Name Abfrage
while true; do
    read -p "Bitte geben Sie einen Namen für die Umgebung ein (z.B. scandy_prod): " CONTAINER_NAME
    if [[ -z "$CONTAINER_NAME" ]]; then
        echo -e "${RED}Der Name darf nicht leer sein.${NC}"
        continue
    fi
    # Konvertiere zu Kleinbuchstaben und ersetze ungültige Zeichen
    CONTAINER_NAME=$(echo "$CONTAINER_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/-/g')
    if [[ ! "$CONTAINER_NAME" =~ ^[a-z0-9_-]+$ ]]; then
        echo -e "${RED}Der Name darf nur Kleinbuchstaben, Zahlen, Unterstrich und Bindestrich enthalten.${NC}"
        continue
    fi
    break
done

# App-Port Abfrage
while true; do
    read -p "Bitte geben Sie den Port für die App ein (Standard: 5000): " APP_PORT
    APP_PORT=${APP_PORT:-5000}
    
    if ! [[ "$APP_PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Bitte geben Sie eine gültige Portnummer ein.${NC}"
        continue
    fi
    
    if [ "$APP_PORT" -lt 1024 ] || [ "$APP_PORT" -gt 65535 ]; then
        echo -e "${RED}Bitte geben Sie einen Port zwischen 1024 und 65535 ein.${NC}"
        continue
    fi
    
    if check_port "$APP_PORT"; then
        echo -e "${YELLOW}WARNUNG: Port $APP_PORT scheint bereits verwendet zu werden. Möchten Sie trotzdem fortfahren? (j/n)${NC}"
        read -p "> " answer
        if [[ "$answer" =~ ^[Jj]$ ]]; then
            break
        fi
    else
        break
    fi
done

# MongoDB-Port Abfrage
while true; do
    read -p "Bitte geben Sie den Port für MongoDB ein (Standard: 27017): " MONGO_PORT
    MONGO_PORT=${MONGO_PORT:-27017}
    
    if ! [[ "$MONGO_PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Bitte geben Sie eine gültige Portnummer ein.${NC}"
        continue
    fi
    
    if [ "$MONGO_PORT" -lt 1024 ] || [ "$MONGO_PORT" -gt 65535 ]; then
        echo -e "${RED}Bitte geben Sie einen Port zwischen 1024 und 65535 ein.${NC}"
        continue
    fi
    
    if check_port "$MONGO_PORT"; then
        echo -e "${YELLOW}WARNUNG: Port $MONGO_PORT scheint bereits verwendet zu werden. Möchten Sie trotzdem fortfahren? (j/n)${NC}"
        read -p "> " answer
        if [[ "$answer" =~ ^[Jj]$ ]]; then
            break
        fi
    else
        break
    fi
done

# Mongo Express Port Abfrage
while true; do
    read -p "Bitte geben Sie den Port für Mongo Express (Web-UI) ein (Standard: 8081): " MONGO_EXPRESS_PORT
    MONGO_EXPRESS_PORT=${MONGO_EXPRESS_PORT:-8081}
    
    if ! [[ "$MONGO_EXPRESS_PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Bitte geben Sie eine gültige Portnummer ein.${NC}"
        continue
    fi
    
    if [ "$MONGO_EXPRESS_PORT" -lt 1024 ] || [ "$MONGO_EXPRESS_PORT" -gt 65535 ]; then
        echo -e "${RED}Bitte geben Sie einen Port zwischen 1024 und 65535 ein.${NC}"
        continue
    fi
    
    if check_port "$MONGO_EXPRESS_PORT"; then
        echo -e "${YELLOW}WARNUNG: Port $MONGO_EXPRESS_PORT scheint bereits verwendet zu werden. Möchten Sie trotzdem fortfahren? (j/n)${NC}"
        read -p "> " answer
        if [[ "$answer" =~ ^[Jj]$ ]]; then
            break
        fi
    else
        break
    fi
done

# MongoDB Credentials
read -p "MongoDB Admin Benutzername (Standard: admin): " MONGO_USER
MONGO_USER=${MONGO_USER:-admin}

read -s -p "MongoDB Admin Passwort (Standard: scandy123): " MONGO_PASS
MONGO_PASS=${MONGO_PASS:-scandy123}
echo ""

# Datenverzeichnis
read -p "Datenverzeichnis (Standard: ./scandy_data): " DATA_DIR
DATA_DIR=${DATA_DIR:-./scandy_data}

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
cat > docker-compose.yml << EOL
version: '3.8'

services:
  ${CONTAINER_NAME}-mongodb:
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
      ME_CONFIG_MONGODB_ADMINUSERNAME: ${MONGO_USER}
      ME_CONFIG_MONGODB_ADMINPASSWORD: ${MONGO_PASS}
      ME_CONFIG_MONGODB_URL: mongodb://${MONGO_USER}:${MONGO_PASS}@${CONTAINER_NAME}-mongodb:27017/
      ME_CONFIG_BASICAUTH_USERNAME: ${MONGO_USER}
      ME_CONFIG_BASICAUTH_PASSWORD: ${MONGO_PASS}
    ports:
      - "${MONGO_EXPRESS_PORT}:8081"
    depends_on:
      ${CONTAINER_NAME}-mongodb:
        condition: service_healthy
    networks:
      - ${CONTAINER_NAME}-network

  ${CONTAINER_NAME}-app:
    build: .
    container_name: ${CONTAINER_NAME}-app
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASS}@${CONTAINER_NAME}-mongodb:27017/
      - MONGODB_DB=scandy
      - FLASK_ENV=production
      - SECRET_KEY=scandy-secret-key-$(date +%s)
      - SYSTEM_NAME=Scandy
      - TICKET_SYSTEM_NAME=Aufgaben
      - TOOL_SYSTEM_NAME=Werkzeuge
      - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
      - CONTAINER_NAME=${CONTAINER_NAME}
      - TZ=Europe/Berlin
    ports:
      - "${APP_PORT}:5000"
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

# Erstelle Dockerfile
echo -e "${GREEN}Erstelle Dockerfile...${NC}"
cat > Dockerfile << 'EOL'
FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    curl \
    build-essential \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Erstelle nicht-root Benutzer
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Kopiere Requirements zuerst für besseres Caching
COPY requirements.txt .

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Rest der Anwendung
COPY . .

# Installiere und baue CSS
RUN npm install && npm run build:css

# Erstelle notwendige Verzeichnisse und setze Berechtigungen
RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/static /app/tmp && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Wechsle zu nicht-root Benutzer
USER appuser

# Exponiere Port
EXPOSE 5000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Starte die Anwendung
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
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

# Erstelle .dockerignore
echo -e "${GREEN}Erstelle .dockerignore...${NC}"
cat > .dockerignore << EOL
.git
.gitignore
README.md
docs/
*.md
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
.DS_Store
Thumbs.db
EOL

# Erstelle Start-Skript
echo -e "${GREEN}Erstelle Start-Skript...${NC}"
cat > start.sh << EOL
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
EOL

# Erstelle Stop-Skript
echo -e "${GREEN}Erstelle Stop-Skript...${NC}"
cat > stop.sh << EOL
#!/bin/bash
echo "Stoppe Scandy Docker-Container..."
docker-compose down

echo "Container gestoppt."
EOL

# Erstelle Update-Skript
echo -e "${GREEN}Erstelle Update-Skript...${NC}"
cat > update.sh << EOL
#!/bin/bash
echo "Update Scandy Docker-Container..."

# Stoppe Container
docker-compose down

# Pull neueste Images
docker-compose pull

# Baue App neu
docker-compose build --no-cache

# Starte Container
docker-compose up -d

echo "Update abgeschlossen!"
EOL

# Erstelle Backup-Skript
echo -e "${GREEN}Erstelle Backup-Skript...${NC}"
cat > backup.sh << EOL
#!/bin/bash
BACKUP_DIR="${DATA_DIR}/backups"
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
tar -czf "\$BACKUP_DIR/app_data_\$TIMESTAMP.tar.gz" -C ${DATA_DIR} uploads backups logs

echo "Backup erstellt: \$BACKUP_DIR"
EOL

# Setze Berechtigungen
chmod +x start.sh stop.sh update.sh backup.sh

# Erstelle Datenverzeichnisse
echo -e "${GREEN}Erstelle Datenverzeichnisse...${NC}"
mkdir -p "${DATA_DIR}/mongodb"
mkdir -p "${DATA_DIR}/uploads"
mkdir -p "${DATA_DIR}/backups"
mkdir -p "${DATA_DIR}/logs"
mkdir -p "${DATA_DIR}/static"

# Kopiere aktuelle Anwendung
echo -e "${GREEN}Kopiere Anwendung...${NC}"
cp -r ../app .
cp ../requirements.txt .
cp ../package.json .
cp ../tailwind.config.js .

# Baue und starte Container
echo -e "${GREEN}Baue Docker-Container...${NC}"
docker-compose build

echo -e "${GREEN}Starte Container...${NC}"
docker-compose up -d

# Warte auf Container-Start
echo -e "${GREEN}Warte auf Container-Start...${NC}"
sleep 15

# Zeige Status
echo -e "${GREEN}Container-Status:${NC}"
docker-compose ps

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Installation abgeschlossen!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Scandy ist verfügbar unter:${NC}"
echo -e "${BLUE}App:${NC} http://localhost:${APP_PORT}"
echo -e "${BLUE}Mongo Express:${NC} http://localhost:${MONGO_EXPRESS_PORT}"
echo -e "${BLUE}MongoDB:${NC} localhost:${MONGO_PORT}"
echo ""
echo -e "${GREEN}Verfügbare Skripte:${NC}"
echo -e "${BLUE}start.sh${NC} - Container starten"
echo -e "${BLUE}stop.sh${NC} - Container stoppen"
echo -e "${BLUE}update.sh${NC} - Container aktualisieren"
echo -e "${BLUE}backup.sh${NC} - Backup erstellen"
echo ""
echo -e "${GREEN}Daten werden gespeichert in:${NC} ${DATA_DIR}"
echo -e "${GREEN}========================================${NC}" 