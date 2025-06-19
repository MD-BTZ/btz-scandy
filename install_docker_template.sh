#!/bin/bash

# Scandy Docker-Installer (Template-basiert) - Linux Version
# MongoDB + App Container Setup mit Template-System

echo "========================================"
echo "   Scandy Docker-Installer (Template)"
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

# MongoDB-Port Abfrage
read -p "Bitte geben Sie den Port für MongoDB ein (Standard: 27017): " MONGO_PORT
MONGO_PORT=${MONGO_PORT:-27017}

# Mongo Express Port Abfrage
read -p "Bitte geben Sie den Port für Mongo Express (Web-UI) ein (Standard: 8081): " MONGO_EXPRESS_PORT
MONGO_EXPRESS_PORT=${MONGO_EXPRESS_PORT:-8081}

# MongoDB Credentials
read -p "MongoDB Admin Benutzername (Standard: admin): " MONGO_USER
MONGO_USER=${MONGO_USER:-admin}

read -p "MongoDB Admin Passwort (Standard: scandy123): " MONGO_PASS
MONGO_PASS=${MONGO_PASS:-scandy123}

# Datenverzeichnis
read -p "Datenverzeichnis (Standard: ./scandy_data): " DATA_DIR
DATA_DIR=${DATA_DIR:-./scandy_data}

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
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

echo "Erstelle Projektverzeichnis: $PROJECT_DIR"

# Kopiere Template-Dateien
echo "Kopiere Template-Dateien..."
cp "../docker-compose.template.yml" "."
cp "../process_template.py" "."

# Verarbeite Template
echo "Verarbeite Template..."
python3 process_template.py "$CONTAINER_NAME" "$APP_PORT" "$MONGO_PORT" "$MONGO_EXPRESS_PORT" "$MONGO_USER" "$MONGO_PASS" "$DATA_DIR"

if [ $? -ne 0 ]; then
    echo "FEHLER: Template-Verarbeitung fehlgeschlagen!"
    exit 1
fi

# Erstelle Dockerfile
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

# Erstelle Start-Skript
echo "Erstelle Start-Skript..."
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

# Erstelle Datenverzeichnisse
echo "Erstelle Datenverzeichnisse..."
mkdir -p "$DATA_DIR/mongodb"
mkdir -p "$DATA_DIR/uploads"
mkdir -p "$DATA_DIR/backups"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/static"

# Kopiere aktuelle Anwendung
echo "Kopiere Anwendung..."
# Das Template-System übernimmt das Kopieren und CSS-Build

# Baue und starte Container
echo "Baue Docker-Container..."
docker-compose build

echo "Starte Container..."
docker-compose up -d

# Warte auf Container-Start
echo "Warte auf Container-Start..."
sleep 15

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