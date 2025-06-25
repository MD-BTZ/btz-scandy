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
