#!/bin/bash

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "Docker ist nicht installiert. Bitte installieren Sie Docker zuerst."
    exit 1
fi

# Prüfe ob Docker Compose installiert ist
if ! docker compose version &> /dev/null; then
    echo "Docker Compose ist nicht installiert. Bitte installieren Sie Docker Compose zuerst."
    exit 1
fi

# Erstelle notwendige Verzeichnisse
mkdir -p database backups logs

# Generiere einen sicheren Secret Key falls nicht vorhanden
if [ ! -f .env ]; then
    echo "Generiere neue .env Datei..."
    echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
fi

# Baue und starte die Container
echo "Baue und starte die Scandy-Container..."
docker compose up -d --build

# Warte kurz bis der Container gestartet ist
sleep 5

# Prüfe ob der Container läuft
if docker ps | grep -q scandy; then
    echo "Scandy wurde erfolgreich gestartet!"
    echo "Die Anwendung ist unter http://localhost:5000 erreichbar"
else
    echo "Es gab ein Problem beim Starten der Anwendung."
    echo "Bitte überprüfen Sie die Logs mit: docker compose logs"
fi 