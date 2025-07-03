#!/bin/bash

echo "========================================"
echo "Scandy Produktions-Update"
echo "========================================"
echo

echo "Stoppe Container..."
docker-compose down

echo
echo "Hole neueste Version..."
git pull

echo
echo "Baue Container neu..."
docker-compose build --no-cache

echo
echo "Starte Container..."
docker-compose up -d

echo
echo "Warte auf Container-Start..."
sleep 10

echo
echo "Pruefe Status..."
docker-compose ps

echo
echo "========================================"
echo "Update abgeschlossen!"
echo "========================================"
echo 