#!/bin/bash

echo "========================================"
echo "Scandy Komplette Installation"
echo "========================================"
echo "Dieses Skript installiert Scandy komplett neu:"
echo "- Scandy App"
echo "- MongoDB Datenbank"
echo "- Mongo Express (Datenbank-Verwaltung)"
echo "========================================"
echo

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "❌ ERROR: Docker ist nicht installiert oder nicht verfügbar!"
    echo "Bitte installiere Docker und starte es neu."
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo "❌ ERROR: Docker läuft nicht!"
    echo "Bitte starte Docker und versuche es erneut."
    exit 1
fi

echo "✅ Docker gefunden. Starte komplette Installation..."
echo

# Prüfe ob .env existiert, falls nicht erstelle sie
if [ ! -f ".env" ]; then
    echo "📝 Erstelle .env-Datei aus env.example..."
    cp env.example .env
    echo "✅ .env-Datei erstellt!"
    echo "⚠️  Bitte passe die Werte in .env an deine Umgebung an!"
    echo
fi

# Prüfe ob bereits eine Installation existiert
if [ -f "docker-compose.yml" ]; then
    echo "⚠️  Bestehende Installation gefunden!"
    echo
    echo "Optionen:"
    echo "1 = Abbrechen"
    echo "2 = Komplett neu installieren (ALLE Daten gehen verloren!)"
    echo "3 = Nur App neu installieren (Daten bleiben erhalten)"
    echo
    read -p "Wählen Sie (1-3): " choice
    case $choice in
        1) 
            echo "Installation abgebrochen."
            exit 0 
            ;;
        2) 
            echo "⚠️  KOMPLETT NEU INSTALLIEREN - ALLE DATEN GEHEN VERLOREN!"
            read -p "Sind Sie sicher? (j/N): " confirm
            if [[ ! $confirm =~ ^[Jj]$ ]]; then
                echo "Installation abgebrochen."
                exit 0
            fi
            echo "🔄 Komplett neu installieren..."
            docker-compose down -v
            docker system prune -f
            docker volume prune -f
            rm -rf data/
            rm -rf backups/
            rm -rf logs/
            ;;
        3) 
            echo "🔄 Nur App neu installieren..."
            echo "Führe update.sh aus..."
            ./update.sh
            exit 0
            ;;
        *) 
            echo "Ungültige Auswahl. Installation abgebrochen."
            exit 1
            ;;
    esac
fi

# Erstelle Datenverzeichnisse
echo "📁 Erstelle Datenverzeichnisse..."
mkdir -p data/{backups,logs,static,uploads}
mkdir -p backups/
mkdir -p logs/

# Stoppe laufende Container falls vorhanden
echo "🛑 Stoppe laufende Container..."
docker-compose down -v 2>/dev/null || true

# Entferne alte Images
echo "🗑️  Entferne alte Images..."
docker images | grep scandy | awk '{print $3}' | xargs -r docker rmi -f
docker images | grep mongo | awk '{print $3}' | xargs -r docker rmi -f

# Baue und starte alle Container
echo "🔨 Baue und starte alle Container..."
docker-compose up -d --build

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Fehler beim Bauen der Container!"
    echo "Versuche es mit einfachem Build..."
    docker-compose build --no-cache
    docker-compose up -d
fi

if [ $? -ne 0 ]; then
    echo "❌ ERROR: Installation fehlgeschlagen!"
    exit 1
fi

echo
echo "⏳ Warte auf Start aller Services..."
sleep 20

# Prüfe Container-Status
echo "🔍 Prüfe Container-Status..."
docker-compose ps

# Prüfe ob alle Container laufen
echo
echo "🔍 Prüfe Service-Verfügbarkeit..."
sleep 5

# Prüfe MongoDB
if docker-compose exec -T scandy-mongodb mongosh --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
    echo "✅ MongoDB läuft"
else
    echo "⚠️  MongoDB startet noch..."
fi

# Prüfe Mongo Express
if curl -s http://localhost:8081 >/dev/null 2>&1; then
    echo "✅ Mongo Express läuft"
else
    echo "⚠️  Mongo Express startet noch..."
fi

# Prüfe Scandy App
if curl -s http://localhost:5000 >/dev/null 2>&1; then
    echo "✅ Scandy App läuft"
else
    echo "⚠️  Scandy App startet noch..."
fi

echo
echo "========================================"
echo "✅ KOMPLETTE INSTALLATION ABGESCHLOSSEN!"
echo "========================================"
echo
echo "🎉 Alle Services sind installiert und verfügbar:"
echo
echo "🌐 Web-Anwendungen:"
echo "- Scandy App:     http://localhost:5000"
echo "- Mongo Express:  http://localhost:8081"
echo
echo "🔐 Standard-Zugangsdaten:"
echo "- Admin: admin / admin123"
echo "- Teilnehmer: teilnehmer / admin123"
echo
echo "📊 Datenbank-Zugang (Mongo Express):"
echo "- Benutzer: admin"
echo "- Passwort: [aus Umgebungsvariable MONGO_INITDB_ROOT_PASSWORD]"
echo
echo "📁 Datenverzeichnisse:"
echo "- Backups: ./backups/"
echo "- Logs:    ./logs/"
echo "- Uploads: ./data/uploads/"
echo
echo "🔧 Nützliche Befehle:"
echo "- Status aller Container: docker-compose ps"
echo "- Logs anzeigen:         docker-compose logs -f"
echo "- Stoppen:               docker-compose down"
echo "- Neustart:              docker-compose restart"
echo "- Nur App updaten:       ./update.sh"
echo
echo "⚠️  WICHTIG: Für Updates verwenden Sie ./update.sh"
echo "   Das schont die Datenbank und ist schneller!"
echo
echo "========================================" 