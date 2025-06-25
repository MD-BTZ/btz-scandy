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
echo "App: http://localhost:5000"
echo "Mongo Express: http://localhost:8081"
echo "MongoDB: localhost:27017"
echo "=========================================="
