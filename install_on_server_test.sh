#!/bin/bash

# Konfiguration
TARGET_DIR="/home/btz-admin/scandy_test"
TEST_PORT=5001
ARCHIVE_NAME="scandy_deploy.tar.gz"

echo "Starte Installation der Testumgebung..."

# Verzeichnisse vorbereiten
mkdir -p $TARGET_DIR
mkdir -p $TARGET_DIR/database $TARGET_DIR/backups $TARGET_DIR/logs $TARGET_DIR/tmp

# Archiv entpacken (nimmt an, dass das Archiv im gleichen Verzeichnis wie dieses Skript liegt)
echo "Entpacke Archiv..."
tar -xzf $ARCHIVE_NAME -C $TARGET_DIR

# Startskript ausführbar machen
chmod +x $TARGET_DIR/docker-start.sh

# Secret Key generieren falls nicht vorhanden
if [ ! -f $TARGET_DIR/.env ]; then
    echo "Generiere neue .env Datei..."
    echo "SECRET_KEY=$(openssl rand -hex 32)" > $TARGET_DIR/.env
fi

# Docker-Compose-Datei für Testumgebung anpassen
sed -i "s/\"5000:5000\"/\"$TEST_PORT:5000\"/" $TARGET_DIR/docker-compose.yml
sed -i "s/container_name: scandy/container_name: scandy_test/" $TARGET_DIR/docker-compose.yml

# Docker-Container bauen und starten
echo "Baue und starte Docker-Container..."
cd $TARGET_DIR
docker compose up -d --build

echo "Installation der Testumgebung abgeschlossen!"
echo "Die Anwendung sollte unter http://localhost:$TEST_PORT oder http://$(hostname -I | awk '{print $1}'):$TEST_PORT erreichbar sein." 