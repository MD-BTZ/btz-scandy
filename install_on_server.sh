#!/bin/bash

echo "----------------------------------------"
echo "   Scandy Docker-Installer (Linux)"
echo "----------------------------------------"

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

# Verzeichnis anlegen
mkdir -p "$DATA_DIR/database" "$DATA_DIR/backups" "$DATA_DIR/logs" "$DATA_DIR/tmp"

echo ""
echo "Starte den Container '$CONTAINER_NAME' auf Port $PORT ..."
echo "Daten werden gespeichert in: $DATA_DIR"
echo ""

# Container stoppen/löschen, falls er schon existiert
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
  echo "Ein alter Container mit diesem Namen wird gestoppt und gelöscht..."
  docker stop "$CONTAINER_NAME" >/dev/null 2>&1
  docker rm "$CONTAINER_NAME" >/dev/null 2>&1
fi

# Container starten
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:5000" \
  -v "$DATA_DIR/database:/app/database" \
  -v "$DATA_DIR/backups:/app/backups" \
  -v "$DATA_DIR/logs:/app/logs" \
  -v "$DATA_DIR/tmp:/app/tmp" \
  --restart unless-stopped \
  python:3.9-slim \
  bash -c "
    apt-get update && apt-get install -y git build-essential libsqlite3-dev && \
    git clone https://github.com/woschj/scandy2.git /app && \
    cd /app && \
    pip install --no-cache-dir -r requirements.txt && \
    mkdir -p /app/backups /app/database /app/logs /app/tmp && \
    touch /app/tmp/needs_restart && \
    gunicorn --bind 0.0.0.0:5000 --reload --reload-extra-file /app/tmp/needs_restart app.wsgi:application
  "

echo ""
echo "----------------------------------------"
echo "FERTIG! Die Scandy-App läuft jetzt auf Port $PORT."
echo "Öffne im Browser: http://localhost:$PORT"
echo "----------------------------------------" 