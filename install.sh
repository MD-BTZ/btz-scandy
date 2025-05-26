#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

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
        echo "WARNUNG: Kann Port-Verfügbarkeit nicht prüfen. Bitte stellen Sie sicher, dass Port $1 frei ist."
        return 0
    fi
}

echo "Installiere Scandy Testumgebung..."

# Container-Name Abfrage
while true; do
    read -p "Bitte geben Sie einen Namen für die Testumgebung ein (z.B. scandy_test): " CONTAINER_NAME
    if [[ -z "$CONTAINER_NAME" ]]; then
        echo "Der Name darf nicht leer sein."
        continue
    fi
    # Konvertiere zu Kleinbuchstaben und ersetze ungültige Zeichen
    CONTAINER_NAME=$(echo "$CONTAINER_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/-/g')
    if [[ ! "$CONTAINER_NAME" =~ ^[a-z0-9_-]+$ ]]; then
        echo "Der Name darf nur Kleinbuchstaben, Zahlen, Unterstrich und Bindestrich enthalten."
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
        echo "Bitte geben Sie eine gültige Portnummer ein."
        continue
    fi
    
    # Prüfe ob Port im gültigen Bereich ist
    if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
        echo "Bitte geben Sie einen Port zwischen 1024 und 65535 ein."
        continue
    fi
    
    # Prüfe ob Port bereits verwendet wird
    if check_port "$PORT"; then
        echo "WARNUNG: Port $PORT scheint bereits verwendet zu werden. Möchten Sie trotzdem fortfahren? (j/n)"
        read -p "> " answer
        if [[ "$answer" =~ ^[Jj]$ ]]; then
            break
        fi
    else
        break
    fi
done

# Prüfe ob Docker installiert ist
if ! command_exists docker; then
    echo "Docker ist nicht installiert. Bitte installieren Sie Docker zuerst."
    exit 1
fi

# Prüfe ob Docker Compose installiert ist
if ! command_exists docker compose; then
    echo "Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose zuerst."
    exit 1
fi

# Erstelle Projektverzeichnis
PROJECT_DIR="${CONTAINER_NAME}"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Erstelle docker-compose.yml
cat > docker-compose.yml << EOL
services:
  ${CONTAINER_NAME}:
    build: .
    ports:
      - "${PORT}:5000"
    volumes:
      - ./database:/app/database
      - ./uploads:/app/uploads
      - ./backups:/app/backups
    environment:
      - FLASK_APP=app
      - FLASK_ENV=development
      - FLASK_DEBUG=1
    container_name: ${CONTAINER_NAME}
EOL

# Erstelle Dockerfile
cat > Dockerfile << 'EOL'
FROM python:3.11-slim

# Installiere Git und Node.js
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Klone das Repository
RUN git clone https://github.com/woschj/scandy2.git /app

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Installiere und baue CSS
RUN npm install && npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/database /app/uploads /app/backups
RUN chmod -R 777 /app/database /app/uploads /app/backups

# Setze Berechtigungen für das Update-Skript
RUN chmod +x /app/update.sh

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0"]
EOL

# Baue und starte die Container
echo "Baue und starte die Container..."
docker compose build --no-cache
docker compose up -d

echo "------------------------------------"
echo "Installation abgeschlossen!"
echo "Die Testumgebung ist unter http://localhost:${PORT} erreichbar"
echo "Container-Name: ${CONTAINER_NAME}"
echo "------------------------------------" 