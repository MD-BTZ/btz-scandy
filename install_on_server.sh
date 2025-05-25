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

# Container-Name abfragen
read -p "Wie soll der Container heißen? [scandy]: " CONTAINER_NAME
CONTAINER_NAME=${CONTAINER_NAME:-scandy}

# Port abfragen
read -p "Welcher Port soll nach außen freigegeben werden? [5000]: " PORT
PORT=${PORT:-5000}

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

echo -e "${GREEN}Starte den Container '$CONTAINER_NAME' auf Port $PORT ...${NC}"
echo -e "${GREEN}Daten werden gespeichert in: $DATA_DIR${NC}"

# Container stoppen/löschen, falls er schon existiert
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
  echo "Ein alter Container mit diesem Namen wird gestoppt und gelöscht..."
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1
  docker rm "$CONTAINER_NAME" >/dev/null 2>&1
fi

# Container starten und Repo als Volume mounten
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:5000" \
  -v "$PWD/scandy2:/app" \
  -v "$PWD/$DATA_DIR:/app/data" \
  python:3.9-slim \
  bash -c "
    apt-get update && apt-get install -y git build-essential libsqlite3-dev && \
    cd /app && \
    pip install -r requirements.txt && \
    export FLASK_DEBUG=1 && \
    export FLASK_ENV=development && \
    gunicorn -w 4 -b 0.0.0.0:5000 --reload --reload-extra-file tmp/needs_restart --log-level debug app.wsgi:application
  "

echo -e "${GREEN}----------------------------------------${NC}"
echo -e "${GREEN}FERTIG! Die Scandy-App läuft jetzt auf Port $PORT.${NC}"
echo -e "${GREEN}Öffne im Browser: http://localhost:$PORT${NC}"
echo -e "${GREEN}----------------------------------------${NC}" 