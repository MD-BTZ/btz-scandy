#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Farben für die Ausgabe
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
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

# Funktion zum Prüfen der Docker-Version
check_docker_version() {
    local version=$(docker --version | cut -d' ' -f3 | cut -d'.' -f1)
    if [ "$version" -lt 20 ]; then
        echo -e "${RED}WARNUNG: Docker Version $version ist veraltet. Version 20 oder höher wird empfohlen.${NC}"
        read -p "Möchten Sie trotzdem fortfahren? (j/n) " answer
        if [[ ! "$answer" =~ ^[Jj]$ ]]; then
            exit 1
        fi
    fi
}

echo -e "${GREEN}----------------------------------------${NC}"
echo -e "${GREEN}   Scandy Docker-Installer${NC}"
echo -e "${GREEN}----------------------------------------${NC}"

# Prüfe Docker-Installation
if ! command_exists docker; then
    echo -e "${RED}Docker ist nicht installiert. Bitte installieren Sie Docker zuerst.${NC}"
    echo "Installationsanleitung: https://docs.docker.com/get-docker/"
    exit 1
fi

# Prüfe Docker-Version
check_docker_version

# Container-Name Abfrage
while true; do
    read -p "Bitte geben Sie einen Namen für die Testumgebung ein (z.B. scandy_test): " CONTAINER_NAME
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

# Port-Abfrage
while true; do
    read -p "Bitte geben Sie den gewünschten Port ein (Standard: 5002): " PORT
    PORT=${PORT:-5002}
    
    # Prüfe ob Port eine Zahl ist
    if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Bitte geben Sie eine gültige Portnummer ein.${NC}"
        continue
    fi
    
    # Prüfe ob Port im gültigen Bereich ist
    if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
        echo -e "${RED}Bitte geben Sie einen Port zwischen 1024 und 65535 ein.${NC}"
        continue
    fi
    
    # Prüfe ob Port bereits verwendet wird
    if check_port "$PORT"; then
        echo -e "${YELLOW}WARNUNG: Port $PORT scheint bereits verwendet zu werden. Möchten Sie trotzdem fortfahren? (j/n)${NC}"
        read -p "> " answer
        if [[ "$answer" =~ ^[Jj]$ ]]; then
            break
        fi
    else
        break
    fi
done

# Erstelle Projektverzeichnis
PROJECT_DIR="${CONTAINER_NAME}"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Erstelle docker-compose.yml
cat > docker-compose.yml << EOL
version: '3.8'

services:
  ${CONTAINER_NAME}:
    build: .
    ports:
      - "${PORT}:5000"
    volumes:
      - ./database:/app/database
      - ./uploads:/app/uploads
      - ./backups:/app/backups
      - ./logs:/app/logs
    environment:
      - FLASK_APP=app
      - FLASK_ENV=development
      - FLASK_DEBUG=1
      - SYSTEM_NAME=Scandy
      - TICKET_SYSTEM_NAME=Aufgaben
      - TOOL_SYSTEM_NAME=Werkzeuge
      - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
      - CONTAINER_NAME=${CONTAINER_NAME}
      - TZ=Europe/Berlin
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 512M
    security_opt:
      - no-new-privileges:true
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
    container_name: ${CONTAINER_NAME}
EOL

# Erstelle Dockerfile
cat > Dockerfile << 'EOL'
FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    curl \
    build-essential \
    libsqlite3-dev \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Erstelle nicht-root Benutzer
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Klone das Repository
RUN git clone https://github.com/woschj/scandy2.git /app

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt docker

# Installiere und baue CSS
RUN npm install && npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/database /app/uploads /app/backups /app/logs /app/tmp
RUN chmod -R 777 /app/database /app/uploads /app/backups /app/logs /app/tmp

# Setze Berechtigungen für das Update-Skript
RUN chmod +x /app/update.sh

# Wechsle zu nicht-root Benutzer
USER appuser

EXPOSE 5000

# Starte Gunicorn mit mehreren Workers
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--reload", "--reload-extra-file", "tmp/needs_restart", "--log-level", "debug", "app.wsgi:application"]
EOL

# Erstelle .env Datei
cat > .env << EOL
FLASK_APP=app
FLASK_ENV=development
FLASK_DEBUG=1
SYSTEM_NAME=Scandy
TICKET_SYSTEM_NAME=Aufgaben
TOOL_SYSTEM_NAME=Werkzeuge
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
CONTAINER_NAME=${CONTAINER_NAME}
TZ=Europe/Berlin
EOL

# Erstelle Verzeichnisse
mkdir -p database uploads backups logs

# Erstelle .dockerignore
cat > .dockerignore << EOL
.git
.gitignore
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.env
*.log
database/
uploads/
backups/
logs/
tmp/
EOL

# Baue und starte die Container
echo -e "${GREEN}Baue und starte die Container...${NC}"
docker compose build --no-cache
docker compose up -d

# Warte auf Container-Start
echo -e "${GREEN}Warte auf Container-Start...${NC}"
sleep 10

# Prüfe Container-Status
if docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${GREEN}----------------------------------------${NC}"
    echo -e "${GREEN}Installation erfolgreich abgeschlossen!${NC}"
    echo -e "${GREEN}Die Anwendung ist unter http://localhost:${PORT} erreichbar${NC}"
    echo -e "${GREEN}Container-Name: ${CONTAINER_NAME}${NC}"
    echo -e "${GREEN}----------------------------------------${NC}"
    
    # Zeige Container-Logs
    echo -e "${YELLOW}Container-Logs:${NC}"
    docker logs "$CONTAINER_NAME" --tail 20
    
    # Zeige Container-Status
    echo -e "${YELLOW}Container-Status:${NC}"
    docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME"
else
    echo -e "${RED}Fehler: Container konnte nicht gestartet werden.${NC}"
    echo -e "${YELLOW}Container-Logs:${NC}"
    docker logs "$CONTAINER_NAME"
    exit 1
fi 