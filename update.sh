#!/bin/bash

echo "========================================"
echo "Scandy App Update"
echo "========================================"
echo "Dieses Skript aktualisiert die Scandy-App:"
echo "- 📥 Holt neuesten Code von GitHub"
echo "- ✅ Scandy App wird neu gebaut und aktualisiert"
echo "- 🔒 MongoDB bleibt unverändert"
echo "- 🔒 Mongo Express bleibt unverändert"
echo "- 💾 Alle Daten bleiben erhalten"
echo "========================================"
echo

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker ist nicht installiert oder nicht verfügbar!"
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo "❌ ERROR: Docker läuft nicht!"
    exit 1
fi

# Prüfe ob docker-compose.yml existiert
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ ERROR: docker-compose.yml nicht gefunden!"
    echo "Bitte führen Sie zuerst ./install.sh aus."
    exit 1
fi

# Prüfe ob Git installiert ist
if ! command -v git &> /dev/null; then
    echo "❌ ERROR: Git ist nicht installiert!"
    echo "Bitte installieren Sie Git und versuchen Sie es erneut."
    exit 1
fi

# Prüfe ob wir in einem Git-Repository sind
if [ ! -d ".git" ]; then
    echo "❌ ERROR: Kein Git-Repository gefunden!"
    echo "Bitte stellen Sie sicher, dass Sie in einem Scandy Git-Repository sind."
    exit 1
fi

echo "🔍 Prüfe bestehende Installation..."
docker-compose ps

echo
echo "⚠️  WARNUNG: Dieses Update betrifft NUR die Scandy-App!"
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

# Git-Pull: Hole neuesten Code
echo "📥 Hole neuesten Code von GitHub..."
git pull origin main

if [ $? -ne 0 ]; then
    echo "⚠️  Git-Pull fehlgeschlagen. Versuche mit master Branch..."
    git pull origin master
fi

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Git-Pull fehlgeschlagen!"
    echo "Bitte prüfen Sie Ihre Internetverbindung und Git-Konfiguration."
    exit 1
fi

echo "✅ Code erfolgreich aktualisiert!"

# Stoppe nur die App-Container
echo "🛑 Stoppe App-Container..."
docker-compose stop scandy-app 2>/dev/null || true

# Entferne nur die App-Container
echo "🗑️  Entferne alte App-Container..."
docker-compose rm -f scandy-app 2>/dev/null || true

# Entferne alte App-Images und Build-Cache
echo "🗑️  Entferne alte App-Images und Build-Cache..."
docker images | grep scandy-local | awk '{print $3}' | xargs -r docker rmi -f
docker images | grep scandy-app | awk '{print $3}' | xargs -r docker rmi -f

# Entferne ungenutzte Images (dangling images)
echo "🧹 Entferne ungenutzte Images..."
docker image prune -f

# Entferne Build-Cache für besseren Neubau
echo "🧹 Entferne Build-Cache..."
docker builder prune -f

# Baue nur die App neu
echo "🔨 Baue neue App-Version..."
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
echo "🚀 Starte neue App-Version..."
docker-compose up -d scandy-app

if [ $? -ne 0 ]; then
    echo "❌ Fehler beim Starten der App!"
    exit 1
fi

echo
echo "⏳ Warte auf App-Start..."
sleep 10

# Prüfe App-Status
echo "🔍 Prüfe App-Status..."
docker-compose ps scandy-app

# Prüfe App-Logs
echo
echo "📋 Letzte App-Logs:"
docker-compose logs --tail=10 scandy-app

# Prüfe ob App läuft
echo
echo "🔍 Prüfe App-Verfügbarkeit..."
sleep 5

if curl -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Scandy App läuft erfolgreich"
else
    echo "⚠️  Scandy App startet noch..."
    echo "   Bitte warten Sie einen Moment und prüfen Sie:"
    echo "   docker-compose logs scandy-app"
fi

echo
echo "========================================"
echo "✅ APP-UPDATE ABGESCHLOSSEN!"
echo "========================================"
echo
echo "🎉 Die Scandy-App wurde erfolgreich aktualisiert!"
echo "📥 Neuester Code von GitHub wurde eingespielt."
echo
echo "🌐 Verfügbare Services:"
echo "- Scandy App:     http://localhost:5000 ✅ AKTUALISIERT"
echo "- Mongo Express:  http://localhost:8081 🔒 UNVERÄNDERT"
echo
echo "💾 Datenbank-Status:"
echo "- MongoDB:        🔒 Unverändert (Daten erhalten)"
echo "- Mongo Express:  🔒 Unverändert (Daten erhalten)"
echo
echo "🔧 Nützliche Befehle:"
echo "- App-Logs:       docker-compose logs -f scandy-app"
echo "- App-Status:     docker-compose ps scandy-app"
echo "- App-Neustart:   docker-compose restart scandy-app"
echo "- Alle Container: docker-compose ps"
echo
echo "📁 Datenverzeichnisse (unverändert):"
echo "- Backups: ./backups/"
echo "- Logs:    ./logs/"
echo "- Uploads: ./data/uploads/"
echo
echo "🧹 Optional: Docker-System bereinigen"
echo "   Falls Sie Speicherplatz freigeben möchten:"
echo "   docker system prune -f"
echo
echo "========================================" 