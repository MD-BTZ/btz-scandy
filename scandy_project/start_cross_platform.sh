#!/bin/bash

echo "=========================================="
echo "Scandy - Plattformübergreifender Start"
echo "=========================================="
echo

# Prüfe Docker-Installation
echo "[1/5] Prüfe Docker-Installation..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker ist nicht installiert oder nicht verfügbar"
    echo "Bitte installieren Sie Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker ist verfügbar"

# Prüfe Docker-Compose
echo "[2/5] Prüfe Docker Compose..."
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose ist nicht verfügbar"
    exit 1
fi
echo "✅ Docker Compose ist verfügbar"

# Stoppe bestehende Container
echo "[3/5] Stoppe bestehende Container..."
$DOCKER_COMPOSE_CMD down >/dev/null 2>&1
echo "✅ Bestehende Container gestoppt"

# Starte Container
echo "[4/5] Starte Scandy-Container..."
$DOCKER_COMPOSE_CMD up -d --build
if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Starten der Container"
    echo
    echo "Versuche alternative Start-Methode..."
    docker-compose up -d --build
    if [ $? -ne 0 ]; then
        echo "❌ Container konnten nicht gestartet werden"
        exit 1
    fi
fi
echo "✅ Container gestartet"

# Warte auf Container-Start
echo "[5/5] Warte auf Container-Start..."
sleep 15

# Teste Verbindungen
echo
echo "=========================================="
echo "Verbindungstests"
echo "=========================================="

# Teste MongoDB
echo "Teste MongoDB-Verbindung..."
if curl -s http://127.0.0.1:27017 >/dev/null 2>&1; then
    echo "✅ MongoDB ist erreichbar"
else
    echo "⚠️  MongoDB nicht direkt erreichbar (normal in Docker)"
fi

# Teste App
echo "Teste Scandy-App..."
if curl -s http://127.0.0.1:5000 >/dev/null 2>&1; then
    echo "✅ App ist erreichbar"
else
    echo "⚠️  App noch nicht bereit, warte..."
    sleep 10
    if curl -s http://127.0.0.1:5000 >/dev/null 2>&1; then
        echo "✅ App ist erreichbar"
    else
        echo "❌ App ist nicht erreichbar"
        echo "Prüfe Logs mit: $DOCKER_COMPOSE_CMD logs scandy-app"
    fi
fi

# Teste Mongo Express
echo "Teste Mongo Express..."
if curl -s http://127.0.0.1:8081 >/dev/null 2>&1; then
    echo "✅ Mongo Express ist erreichbar"
else
    echo "⚠️  Mongo Express noch nicht bereit"
fi

echo
echo "=========================================="
echo "Scandy ist verfügbar unter:"
echo "=========================================="
echo
echo "🌐 Hauptanwendung: http://localhost:5000"
echo "🌐 Hauptanwendung: http://127.0.0.1:5000"
echo
echo "📊 Mongo Express: http://localhost:8081"
echo "📊 Mongo Express: http://127.0.0.1:8081"
echo
echo "🗄️  MongoDB: localhost:27017"
echo "🗄️  MongoDB: 127.0.0.1:27017"
echo
echo "=========================================="
echo "Container-Status:"
echo "=========================================="
$DOCKER_COMPOSE_CMD ps
echo
echo "=========================================="
echo "Nützliche Befehle:"
echo "=========================================="
echo "Container stoppen: $DOCKER_COMPOSE_CMD down"
echo "Logs anzeigen: $DOCKER_COMPOSE_CMD logs"
echo "App-Logs: $DOCKER_COMPOSE_CMD logs scandy-app"
echo "MongoDB-Logs: $DOCKER_COMPOSE_CMD logs scandy-mongodb"
echo 