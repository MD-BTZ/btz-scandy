#!/bin/bash

echo "========================================"
echo "Scandy Installation - Linux/macOS"
echo "========================================"
echo

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker ist nicht installiert oder nicht verfügbar!"
    echo "Bitte installiere Docker und starte es neu."
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo "ERROR: Docker läuft nicht!"
    echo "Bitte starte Docker und versuche es erneut."
    exit 1
fi

echo "Docker gefunden. Starte Installation..."
echo

# Prüfe ob bereits eine Installation existiert
if [ -f "docker-compose.yml" ]; then
    echo "⚠️  Bestehende Installation gefunden!"
    echo "Optionen: 1=Abbrechen, 2=Update/Neuinstallation, 3=Komplett neu"
    read -p "Wählen Sie (1-3): " choice
    case $choice in
        1) 
            echo "Installation abgebrochen."
            exit 0 
            ;;
        2) 
            echo "Update/Neuinstallation..."
            docker-compose down
            docker-compose build --no-cache
            docker-compose up -d
            ;;
        3) 
            echo "Komplett neu installieren..."
            docker-compose down
            docker system prune -f
            rm -rf scandy_data
            ;;
    esac
fi

# Erstelle Datenverzeichnisse falls nicht vorhanden
mkdir -p scandy_data/{mongodb,uploads,backups,logs,static}

# Stoppe laufende Container falls vorhanden
echo "Stoppe laufende Container..."
docker-compose down 2>/dev/null || true

# Baue und starte Container
echo "Baue und starte Container..."
docker-compose up -d --build

if [ $? -ne 0 ]; then
    echo "ERROR: Fehler beim Bauen der Container!"
    echo "Versuche es mit einfachem Build..."
    docker-compose build --no-cache
    docker-compose up -d
fi

if [ $? -ne 0 ]; then
    echo "ERROR: Installation fehlgeschlagen!"
    exit 1
fi

echo
echo "⏳ Warte auf Start der Services..."
sleep 15

# Prüfe Container-Status
echo "Prüfe Container-Status..."
docker-compose ps

echo
echo "========================================"
echo "✅ Installation abgeschlossen!"
echo "========================================"
echo
echo "Die Scandy-App ist jetzt verfügbar unter:"
echo "- Web-App: http://localhost:5000"
echo "- Mongo Express: http://localhost:8081"
echo
echo "Standard-Zugangsdaten:"
echo "- Benutzer: admin"
echo "- Passwort: admin123"
echo
echo "Nützliche Befehle:"
echo "- Container-Status: docker-compose ps"
echo "- Logs anzeigen: docker-compose logs -f"
echo "- Stoppen: docker-compose down"
echo "- Neustart: docker-compose restart"
echo
echo "========================================" 