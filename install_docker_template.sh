#!/bin/bash

# Scandy Docker-Installer (Vollständig) - Linux Version
# MongoDB + App Container Setup

echo "========================================"
echo "   Scandy Docker-Installer (Vollständig)"
echo "   MongoDB + App Container Setup"
echo "========================================"

# Prüfe Docker-Installation
if ! command -v docker &> /dev/null; then
    echo "FEHLER: Docker ist nicht installiert. Bitte installieren Sie Docker zuerst."
    echo "Installationsanleitung: https://docs.docker.com/engine/install/"
    exit 1
fi

# Prüfe Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "FEHLER: Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose zuerst."
    echo "Installationsanleitung: https://docs.docker.com/compose/install/"
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo "FEHLER: Docker läuft nicht. Bitte starten Sie Docker zuerst."
    exit 1
fi

echo "✓ Docker ist installiert und läuft"

# Container-Name Abfrage
while true; do
    read -p "Bitte geben Sie einen Namen für die Umgebung ein (z.B. scandy_prod): " CONTAINER_NAME
    if [ -n "$CONTAINER_NAME" ]; then
        break
    fi
    echo "Der Name darf nicht leer sein."
done

# Konvertiere zu Kleinbuchstaben und ersetze ungültige Zeichen
CONTAINER_NAME=$(echo "$CONTAINER_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]//g')

# App-Port Abfrage
read -p "Bitte geben Sie den Port für die App ein (Standard: 5000): " APP_PORT
APP_PORT=${APP_PORT:-5000}

# Berechne dynamische Ports basierend auf App-Port
MONGO_PORT=$((27017 + APP_PORT - 5000))
MONGO_EXPRESS_PORT=$((8081 + APP_PORT - 5000))

# Feste Werte für alle anderen Parameter
MONGO_USER=admin
MONGO_PASS=scandy123
DATA_DIR=./scandy_data

echo "========================================"
echo "   Konfiguration:"
echo "========================================"
echo "Container Name: $CONTAINER_NAME"
echo "App Port: $APP_PORT"
echo "MongoDB Port: $MONGO_PORT"
echo "Mongo Express Port: $MONGO_EXPRESS_PORT"
echo "MongoDB User: $MONGO_USER"
echo "Datenverzeichnis: $DATA_DIR"
echo "========================================"

read -p "Möchten Sie mit der Installation fortfahren? (j/n): " confirm
if [[ ! $confirm =~ ^[Jj]$ ]]; then
    echo "Installation abgebrochen."
    exit 0
fi

# Erstelle Projektverzeichnis
PROJECT_DIR="${CONTAINER_NAME}_project"
if [ -d "$PROJECT_DIR" ]; then
    echo "WARNING: Directory $PROJECT_DIR already exists!"
    echo "Overwriting existing directory..."
    rm -rf "$PROJECT_DIR"
fi
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "Erstelle Projektverzeichnis: $PROJECT_DIR"

# Erstelle feste docker-compose.yml
echo "Erstelle docker-compose.yml..."
cat > docker-compose.yml << EOF
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
      - ${CONTAINER_NAME}-network
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
      - ${CONTAINER_NAME}-network

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

networks:
  ${CONTAINER_NAME}-network:
    driver: bridge
EOF

# Erstelle verbessertes Dockerfile
echo "Erstelle Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    curl \
    build-essential \
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

# Stelle sicher, dass CSS-Dateien vorhanden sind
RUN if [ ! -f "app/static/css/main.css" ]; then \
    echo "CSS-Datei nicht gefunden, generiere sie..." && \
    npm install && npm run build:css; \
fi

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
EOF

# Erstelle MongoDB Init-Skript
echo "Erstelle MongoDB Init-Skript..."
mkdir -p mongo-init
cat > mongo-init/init.js << 'EOF'
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

# Erstelle .dockerignore
echo "Erstelle .dockerignore..."
cat > .dockerignore << 'EOF'
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
EOF

# Kopiere Anwendungsdateien
echo "Kopiere Anwendungsdateien..."
cp -r "../app" "."
cp "../requirements.txt" "."
cp "../package.json" "."
cp "../tailwind.config.js" "."
cp "../postcss.config.js" "."

# Generiere CSS vor dem Docker-Build
echo "Generiere CSS..."
echo "Installiere npm-Abhängigkeiten..."
if npm install > /dev/null 2>&1; then
    echo "Baue CSS..."
    if npm run build:css > /dev/null 2>&1; then
        echo "CSS erfolgreich generiert"
    else
        echo "WARNUNG: CSS-Build fehlgeschlagen, verwende vorhandene CSS-Dateien"
    fi
else
    echo "WARNUNG: npm install fehlgeschlagen, versuche ohne CSS-Build fortzufahren"
fi

# Erstelle Datenverzeichnisse
echo "Erstelle Datenverzeichnisse..."
mkdir -p "$DATA_DIR/mongodb"
mkdir -p "$DATA_DIR/uploads"
mkdir -p "$DATA_DIR/backups"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/static"

# Erstelle Start-Skript
echo "Erstelle Start-Skript..."
cat > start.sh << EOF
#!/bin/bash
echo "Starte Scandy Docker-Container..."
docker-compose up -d

echo "Warte auf Container-Start..."
sleep 15

echo "Container-Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "Scandy ist verfügbar unter:"
echo "App: http://localhost:$APP_PORT"
echo "Mongo Express: http://localhost:$MONGO_EXPRESS_PORT"
echo "MongoDB: localhost:$MONGO_PORT"
echo "=========================================="
EOF
chmod +x start.sh

# Erstelle Stop-Skript
echo "Erstelle Stop-Skript..."
cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stoppe Scandy Docker-Container..."
docker-compose down

echo "Container gestoppt."
EOF
chmod +x stop.sh

# Erstelle Update-Skript
echo "Erstelle Update-Skript..."
cat > update.sh << 'EOF'
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
EOF
chmod +x update.sh

# Erstelle Backup-Skript
echo "Erstelle Backup-Skript..."
cat > backup.sh << EOF
#!/bin/bash
BACKUP_DIR="$DATA_DIR/backups"
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
tar -czf "\$BACKUP_DIR/app_data_\$TIMESTAMP.tar.gz" -C "$DATA_DIR" uploads backups logs

echo "Backup erstellt: \$BACKUP_DIR"
EOF
chmod +x backup.sh

# Baue und starte Container
echo "Baue Docker-Container..."
if ! docker-compose build --no-cache; then
    echo "FEHLER: Docker-Build fehlgeschlagen!"
    exit 1
fi

echo "Starte Container..."
if ! docker-compose up -d; then
    echo "FEHLER: Container-Start fehlgeschlagen!"
    exit 1
fi

# Warte auf Container-Start
echo "Warte auf Container-Start..."
sleep 20

# Zeige Status
echo "Container-Status:"
docker-compose ps

echo "========================================"
echo "   Installation abgeschlossen!"
echo "========================================"
echo "Scandy ist verfügbar unter:"
echo "App: http://localhost:$APP_PORT"
echo "Mongo Express: http://localhost:$MONGO_EXPRESS_PORT"
echo "MongoDB: localhost:$MONGO_PORT"
echo ""
echo "Verfügbare Skripte:"
echo "start.sh - Container starten"
echo "stop.sh - Container stoppen"
echo "update.sh - Container aktualisieren"
echo "backup.sh - Backup erstellen"
echo ""
echo "Daten werden gespeichert in: $DATA_DIR"
echo "========================================" 