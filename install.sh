#!/bin/bash

# Scandy Universal Installer für Linux/macOS
# Kombiniert alle Funktionen in einem Script

set -e

echo "🚀 Scandy Installation (Linux/macOS)"
echo "================================="

# Prüfe Docker
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker läuft nicht. Bitte starten Sie Docker zuerst."
    exit 1
fi

echo "✅ Docker ist verfügbar"

# Konfiguration
CONTAINER_NAME="scandy"
APP_PORT="5000"
MONGO_PORT="27017"
MONGO_EXPRESS_PORT="8081"
MONGO_USER="admin"
MONGO_PASS="scandy123"
DATA_DIR="./scandy_data"

echo "========================================"
echo "   Konfiguration:"
echo "========================================"
echo "Container Name: $CONTAINER_NAME"
echo "App Port: $APP_PORT"
echo "MongoDB Port: $MONGO_PORT"
echo "Mongo Express Port: $MONGO_EXPRESS_PORT"
echo "Datenverzeichnis: $DATA_DIR"
echo "========================================"

# Prüfe bestehende Installation
if [ -d "$DATA_DIR/mongodb" ]; then
    echo "⚠️  Bestehende Installation gefunden!"
    echo "Optionen: 1=Abbrechen, 2=Backup+Neu, 3=Überschreiben"
    read -p "Wählen Sie (1-3): " choice
    case $choice in
        1) exit 0 ;;
        2) 
            echo "Erstelle Backup..."
            mkdir -p "$DATA_DIR/backups"
            ;;
        3) 
            echo "Lösche alte Daten..."
            rm -rf "$DATA_DIR"
            ;;
    esac
fi

# Erstelle Projektverzeichnis
PROJECT_DIR="${CONTAINER_NAME}_project"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Erstelle Datenverzeichnisse
mkdir -p "$DATA_DIR/mongodb" "$DATA_DIR/uploads" "$DATA_DIR/backups" "$DATA_DIR/logs" "$DATA_DIR/static"

# Kopiere statische Dateien
if [ -d "../app/static" ]; then
    cp -r ../app/static/* "$DATA_DIR/static/"
fi

# Erstelle docker-compose.yml
cat > docker-compose.yml << EOF
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
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ${CONTAINER_NAME}-app
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=mongodb://${MONGO_USER}:${MONGO_PASS}@${CONTAINER_NAME}-mongodb:27017/
      - MONGODB_DB=scandy
      - FLASK_ENV=production
      - SECRET_KEY=scandy-secret-key-production
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

volumes:
  ${CONTAINER_NAME}-mongodb-data:
    driver: local

networks:
  ${CONTAINER_NAME}-network:
    driver: bridge
EOF

# Kopiere Dateien
cp ../Dockerfile . 2>/dev/null || echo "WARNUNG: Dockerfile nicht gefunden"
cp ../requirements.txt . 2>/dev/null || echo "WARNUNG: requirements.txt nicht gefunden"
cp ../package.json . 2>/dev/null || echo "WARNUNG: package.json nicht gefunden"
[ -f "../tailwind.config.js" ] && cp ../tailwind.config.js .
[ -f "../postcss.config.js" ] && cp ../postcss.config.js .
[ -f "../.dockerignore" ] && cp ../.dockerignore .

# Kopiere App
if [ -d "../app" ]; then
    cp -r ../app .
else
    echo "ERROR: app-Verzeichnis nicht gefunden!"
    exit 1
fi

# Erstelle MongoDB Init
mkdir -p mongo-init
cat > mongo-init/init.js << 'EOF'
db = db.getSiblingDB('scandy');
db.createCollection('tools');
db.createCollection('consumables');
db.createCollection('workers');
db.createCollection('lendings');
db.createCollection('users');
db.createCollection('tickets');
db.createCollection('settings');
db.createCollection('system_logs');
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

# Erstelle Management-Scripts
cat > start.sh << EOF
#!/bin/bash
echo "Starte Scandy..."
docker-compose up -d
sleep 10
docker-compose ps
echo ""
echo "Scandy: http://localhost:${APP_PORT}"
echo "Mongo Express: http://localhost:${MONGO_EXPRESS_PORT}"
EOF

cat > stop.sh << EOF
#!/bin/bash
echo "Stoppe Scandy..."
docker-compose down
EOF

cat > update.sh << EOF
#!/bin/bash
echo "Update Scandy..."
docker-compose down
docker-compose pull
docker-compose build --no-cache
docker-compose up -d
EOF

chmod +x start.sh stop.sh update.sh

# Baue und starte
echo "🏗️  Baue Container..."
docker-compose build --no-cache

if [ $? -ne 0 ]; then
    echo "⚠️  Standard-Build fehlgeschlagen, verwende einfache Version..."
    if [ -f "../Dockerfile.simple" ]; then
        cp ../Dockerfile.simple Dockerfile
        docker-compose build --no-cache
    fi
fi

if [ $? -ne 0 ]; then
    echo "❌ Build fehlgeschlagen!"
    exit 1
fi

echo "✅ Build erfolgreich!"

echo "🚀 Starte Container..."
docker-compose up -d

echo "⏳ Warte auf Start..."
sleep 15

echo "========================================"
echo "✅ Installation abgeschlossen!"
echo "========================================"
echo "Scandy: http://localhost:${APP_PORT}"
echo "Mongo Express: http://localhost:${MONGO_EXPRESS_PORT}"
echo "========================================"
echo ""
echo "📋 Scripts:"
echo "- start.sh: Container starten"
echo "- stop.sh: Container stoppen"
echo "- update.sh: System aktualisieren"
echo "========================================"

echo ""
echo "🔄 Richte automatische Backups ein..."
echo "Erstelle Backup-Script..."

cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="${DATA_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Erstelle Backup..."
mkdir -p "$BACKUP_DIR"
docker exec ${CONTAINER_NAME}-mongodb mongodump --out /tmp/backup
docker cp ${CONTAINER_NAME}-mongodb:/tmp/backup "$BACKUP_DIR/mongodb_$TIMESTAMP"
tar -czf "$BACKUP_DIR/app_data_$TIMESTAMP.tar.gz" -C "$DATA_DIR" uploads backups logs
echo "Backup erstellt: $BACKUP_DIR"
EOF

chmod +x backup.sh

echo "✅ Automatische Backups eingerichtet!"
echo "💡 Backups werden bei jedem Start erstellt"
echo "" 