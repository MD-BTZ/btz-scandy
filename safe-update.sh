#!/bin/bash

echo "🔄 Sicheres Scandy Update"
echo "========================="

# Prüfe ob Docker läuft
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker läuft nicht. Bitte starten Sie Docker zuerst."
    exit 1
fi

echo "✓ Docker ist verfügbar"

# Finde alle Scandy-Projekte
echo "🔍 Suche Scandy-Installationen..."
FOUND_PROJECTS=0

for dir in *_project; do
    if [[ -d "$dir" && -f "$dir/docker-compose.yml" ]]; then
        echo "📁 Gefunden: $dir"
        ((FOUND_PROJECTS++))
        PROJECT_DIR="$dir"
    fi
done

if [[ $FOUND_PROJECTS -eq 0 ]]; then
    echo "❌ Keine Scandy-Installation gefunden!"
    echo "💡 Führen Sie zuerst install.sh aus."
    exit 1
fi

if [[ $FOUND_PROJECTS -eq 1 ]]; then
    echo "✅ Verwende Projekt: $PROJECT_DIR"
else
    echo "⚠️  Mehrere Projekte gefunden. Bitte wählen Sie eines:"
    for dir in *_project; do
        if [[ -d "$dir" && -f "$dir/docker-compose.yml" ]]; then
            echo "- $dir"
        fi
    done
    read -p "Projekt-Verzeichnis: " PROJECT_DIR
    if [[ ! -f "$PROJECT_DIR/docker-compose.yml" ]]; then
        echo "❌ Ungültiges Projekt-Verzeichnis!"
        exit 1
    fi
fi

cd "$PROJECT_DIR"

echo ""
echo "📋 Update-Optionen:"
echo "1. Sicheres Update (empfohlen) - Backup + Update"
echo "2. Schnelles Update - Nur App-Container"
echo "3. Vollständiges Update - Alle Container"
echo "4. Abbrechen"
echo ""
read -p "Wählen Sie eine Option (1-4): " update_choice

case $update_choice in
    1)
        echo "🔄 Sicheres Update wird durchgeführt..."
        echo ""
        
        echo "📦 Erstelle Backup..."
        if ! ./backup.sh; then
            echo "❌ Backup fehlgeschlagen! Update abgebrochen."
            exit 1
        fi
        echo "✅ Backup erfolgreich!"
        
        echo ""
        echo "🔄 Stoppe Container..."
        docker-compose down
        
        echo ""
        echo "📥 Lade neue Images..."
        docker-compose pull
        
        echo ""
        echo "🏗️  Baue App-Container neu..."
        docker-compose build --no-cache scandy-app
        
        echo ""
        echo "🚀 Starte Container..."
        docker-compose up -d
        
        echo ""
        echo "✅ Sicheres Update abgeschlossen!"
        echo "📋 Container-Status:"
        docker-compose ps
        ;;
    2)
        echo "🔄 Schnelles Update wird durchgeführt..."
        echo ""
        
        echo "🔄 Stoppe App-Container..."
        docker-compose stop scandy-app
        
        echo ""
        echo "📥 Lade neues App-Image..."
        docker-compose pull scandy-app
        
        echo ""
        echo "🏗️  Baue App-Container neu..."
        docker-compose build --no-cache scandy-app
        
        echo ""
        echo "🚀 Starte App-Container..."
        docker-compose up -d scandy-app
        
        echo ""
        echo "✅ Schnelles Update abgeschlossen!"
        echo "📋 Container-Status:"
        docker-compose ps
        ;;
    3)
        echo "🔄 Vollständiges Update wird durchgeführt..."
        echo ""
        
        echo "⚠️  WARNUNG: Dies stoppt alle Container und lädt alle Images neu!"
        read -p "Sind Sie sicher? (j/n): " confirm
        if [[ ! $confirm =~ ^[Jj]$ ]]; then
            echo "Update abgebrochen."
            exit 0
        fi
        
        echo ""
        echo "🔄 Stoppe alle Container..."
        docker-compose down
        
        echo ""
        echo "📥 Lade alle Images neu..."
        docker-compose pull
        
        echo ""
        echo "🏗️  Baue alle Container neu..."
        docker-compose build --no-cache
        
        echo ""
        echo "🚀 Starte alle Container..."
        docker-compose up -d
        
        echo ""
        echo "✅ Vollständiges Update abgeschlossen!"
        echo "📋 Container-Status:"
        docker-compose ps
        ;;
    4)
        echo "Update abgebrochen."
        ;;
    *)
        echo "Ungültige Auswahl."
        ;;
esac

echo ""
echo "📋 Nächste Schritte:"
echo "- Prüfen Sie die Anwendung: http://localhost:5000"
echo "- Prüfen Sie die Logs: docker-compose logs"
echo "- Bei Problemen: ./troubleshoot.sh"
echo "" 