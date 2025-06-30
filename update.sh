#!/bin/bash

echo "========================================"
echo "Scandy App Update"
echo "========================================"
echo

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker ist nicht installiert oder nicht verfügbar!"
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo "ERROR: Docker läuft nicht!"
    exit 1
fi

# Prüfe ob docker-compose.yml existiert
if [ ! -f "docker-compose.yml" ]; then
    echo "ERROR: docker-compose.yml nicht gefunden!"
    echo "Bitte führen Sie zuerst ./install.sh aus."
    exit 1
fi

echo "🔍 Prüfe bestehende Installation..."
docker-compose ps

echo
echo "⚠️  WARNUNG: Dieses Update betrifft nur die Scandy-App!"
echo "   MongoDB und Mongo Express bleiben unverändert."
echo "   Alle Daten bleiben erhalten."
echo

read -p "Möchten Sie fortfahren? (j/N): " confirm
if [[ ! $confirm =~ ^[Jj]$ ]]; then
    echo "Update abgebrochen."
    exit 0
fi

echo
echo "🔄 Starte App-Update..."

# Stoppe nur die App-Container
echo "Stoppe App-Container..."
docker-compose stop scandy-app 2>/dev/null || true

# Entferne nur die App-Container
echo "Entferne alte App-Container..."
docker-compose rm -f scandy-app 2>/dev/null || true

# Entferne alte App-Images
echo "Entferne alte App-Images..."
docker images | grep scandy-app | awk '{print $3}' | xargs -r docker rmi -f

# Baue nur die App neu
echo "Baue neue App-Version..."
docker-compose build --no-cache scandy-app

if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Bauen der App!"
    echo "Versuche es mit einfachem Build..."
    docker-compose build scandy-app
fi

if [ $? -ne 0 ]; then
    echo "❌ App-Update fehlgeschlagen!"
    exit 1
fi

# Starte nur die App
echo "Starte neue App-Version..."
docker-compose up -d scandy-app

if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Starten der App!"
    exit 1
fi

echo
echo "⏳ Warte auf App-Start..."
sleep 10

# Prüfe App-Status
echo "Prüfe App-Status..."
docker-compose ps scandy-app

# Prüfe App-Logs
echo
echo "📋 Letzte App-Logs:"
docker-compose logs --tail=10 scandy-app

echo
echo "========================================"
echo "✅ App-Update abgeschlossen!"
echo "========================================"
echo
echo "Die aktualisierte Scandy-App ist verfügbar unter:"
echo "- Web-App: http://localhost:5000"
echo
echo "Datenbank-Container sind unverändert:"
echo "- MongoDB: läuft weiter"
echo "- Mongo Express: läuft weiter"
echo
echo "Nützliche Befehle:"
echo "- App-Logs: docker-compose logs -f scandy-app"
echo "- App-Status: docker-compose ps scandy-app"
echo "- App-Neustart: docker-compose restart scandy-app"
echo "- Alle Container: docker-compose ps"
echo
echo "========================================" 