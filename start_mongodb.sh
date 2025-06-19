#!/bin/bash

# MongoDB-Startskript für Scandy

echo "=== Scandy MongoDB Setup ==="

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "Docker ist nicht installiert. Bitte installieren Sie Docker zuerst."
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo "Docker läuft nicht. Bitte starten Sie Docker zuerst."
    exit 1
fi

echo "Docker ist verfügbar."

# Stoppe existierende Container
echo "Stoppe existierende MongoDB-Container..."
docker stop scandy-mongodb 2>/dev/null || true
docker rm scandy-mongodb 2>/dev/null || true

# Starte MongoDB-Container
echo "Starte MongoDB-Container..."
docker run -d \
  --name scandy-mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=scandy123 \
  -e MONGO_INITDB_DATABASE=scandy \
  mongo:7.0

# Warte bis MongoDB bereit ist
echo "Warte auf MongoDB..."
sleep 10

# Teste MongoDB-Verbindung
echo "Teste MongoDB-Verbindung..."
if docker exec scandy-mongodb mongosh --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
    echo "✓ MongoDB ist bereit!"
else
    echo "✗ MongoDB-Verbindung fehlgeschlagen"
    exit 1
fi

# Starte MongoDB Express (optional)
read -p "Möchten Sie MongoDB Express (Web-Interface) starten? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starte MongoDB Express..."
    docker stop scandy-mongo-express 2>/dev/null || true
    docker rm scandy-mongo-express 2>/dev/null || true
    
    docker run -d \
      --name scandy-mongo-express \
      -p 8081:8081 \
      -e ME_CONFIG_MONGODB_ADMINUSERNAME=admin \
      -e ME_CONFIG_MONGODB_ADMINPASSWORD=scandy123 \
      -e ME_CONFIG_MONGODB_URL=mongodb://admin:scandy123@scandy-mongodb:27017/ \
      -e ME_CONFIG_BASICAUTH_USERNAME=admin \
      -e ME_CONFIG_BASICAUTH_PASSWORD=scandy123 \
      --network host \
      mongo-express:1.0.0
    
    echo "✓ MongoDB Express gestartet: http://localhost:8081"
    echo "  Benutzername: admin"
    echo "  Passwort: scandy123"
fi

# Setze Umgebungsvariablen
echo ""
echo "=== Umgebungsvariablen ==="
echo "Setzen Sie folgende Umgebungsvariablen:"
echo ""
echo "export DATABASE_MODE=mongodb"
echo "export MONGODB_URI=mongodb://admin:scandy123@localhost:27017/"
echo "export MONGODB_DB=scandy"
echo ""
echo "Oder erstellen Sie eine .env Datei:"
echo ""
echo "DATABASE_MODE=mongodb"
echo "MONGODB_URI=mongodb://admin:scandy123@localhost:27017/"
echo "MONGODB_DB=scandy"
echo ""

# Starte Scandy-Anwendung
read -p "Möchten Sie Scandy mit MongoDB starten? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starte Scandy-Anwendung..."
    
    # Setze Umgebungsvariablen für diesen Prozess
    export DATABASE_MODE=mongodb
    export MONGODB_URI=mongodb://admin:scandy123@localhost:27017/
    export MONGODB_DB=scandy
    
    # Starte Flask-Anwendung
    python -m flask run --host=0.0.0.0 --port=5000
fi

echo ""
echo "=== MongoDB Setup abgeschlossen ==="
echo "MongoDB läuft auf: localhost:27017"
echo "Datenbank: scandy"
echo "Benutzer: admin"
echo "Passwort: scandy123" 