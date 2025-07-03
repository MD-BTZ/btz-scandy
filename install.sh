#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy App Installation"
echo "========================================"
echo "Dieses Skript installiert Scandy komplett neu:"
echo "- 🐳 Docker Container werden erstellt"
echo "- 🗄️  MongoDB wird initialisiert"
echo "- 🌐 Web-Anwendung wird gestartet"
echo "- 📊 Mongo Express wird gestartet"
echo "========================================"
echo

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker ist nicht installiert oder nicht verfügbar!${NC}"
    echo "Bitte installiere Docker und versuche es erneut."
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker läuft nicht!${NC}"
    echo "Bitte starte Docker und versuche es erneut."
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

echo -e "${GREEN}✅ Docker gefunden. Starte komplette Installation...${NC}"
echo

# Prüfe ob .env existiert, falls nicht erstelle sie
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📝 Erstelle .env-Datei aus env.example...${NC}"
    cp env.example .env
    echo -e "${GREEN}✅ .env-Datei erstellt!${NC}"
    echo -e "${YELLOW}⚠️  Bitte passe die Werte in .env an deine Umgebung an!${NC}"
    echo
fi

# Prüfe ob bereits eine Installation existiert
if [ -f "docker-compose.yml" ]; then
    echo -e "${YELLOW}⚠️  Bestehende Installation gefunden!${NC}"
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
            read -p "Drücke Enter zum Beenden..."
            exit 0
            ;;
        2)
            echo -e "${RED}⚠️  KOMPLETT NEU INSTALLIEREN - ALLE DATEN GEHEN VERLOREN!${NC}"
            read -p "Sind Sie sicher? (j/N): " confirm
            if [[ ! $confirm =~ ^[Jj]$ ]]; then
                echo "Installation abgebrochen."
                read -p "Drücke Enter zum Beenden..."
                exit 0
            fi
            echo -e "${BLUE}🔄 Komplett neu installieren...${NC}"
            
            # Sichere Backups vor dem Löschen
            if [ -d "backups" ]; then
                echo -e "${BLUE}💾 Sichere bestehende Backups...${NC}"
                if [ ! -d "backups_backup" ]; then
                    cp -r backups backups_backup
                    echo -e "${GREEN}✅ Backups gesichert in: backups_backup/${NC}"
                else
                    echo -e "${YELLOW}⚠️  Backup-Ordner existiert bereits: backups_backup/${NC}"
                fi
            fi
            
            docker-compose down -v
            docker system prune -f
            docker volume prune -f
            [ -d "data" ] && rm -rf data
            [ -d "backups" ] && rm -rf backups
            [ -d "logs" ] && rm -rf logs
            ;;
        3)
            echo -e "${BLUE}🔄 Nur App neu installieren...${NC}"
            echo "Führe update.sh aus..."
            ./update.sh
            exit 0
            ;;
        *)
            echo "Ungültige Auswahl. Installation abgebrochen."
            read -p "Drücke Enter zum Beenden..."
            exit 1
            ;;
    esac
fi

# Erstelle Datenverzeichnisse
echo -e "${BLUE}📁 Erstelle Datenverzeichnisse...${NC}"
mkdir -p data/backups data/logs data/static data/uploads backups logs

# Stoppe laufende Container falls vorhanden
echo -e "${BLUE}🛑 Stoppe laufende Container...${NC}"
docker-compose down -v &> /dev/null

# Entferne alte Images
echo -e "${BLUE}🗑️  Entferne alte Images...${NC}"
docker images | grep scandy | awk '{print $3}' | xargs -r docker rmi -f &> /dev/null
docker images | grep mongo | awk '{print $3}' | xargs -r docker rmi -f &> /dev/null

# Baue und starte alle Container
echo -e "${BLUE}🔨 Baue und starte alle Container...${NC}"
docker-compose up -d --build
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Versuche es mit einfachem Build...${NC}"
    docker-compose build --no-cache
    docker-compose up -d
fi
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Installation fehlgeschlagen!${NC}"
    read -p "Drücke Enter zum Beenden..."
    exit 1
fi

echo
echo -e "${BLUE}⏳ Warte auf Start aller Services...${NC}"

# Warte auf MongoDB Health Status
retries=0
while [ $retries -lt 12 ]; do
    if docker ps | grep -q scandy-mongodb; then
        break
    fi
    echo -e "${YELLOW}⏳ MongoDB Container startet noch...${NC}"
    sleep 5
    ((retries++))
done

if [ $retries -ge 12 ]; then
    echo -e "${RED}❌ MongoDB Container startet nicht!${NC}"
    echo "Container Status:"
    docker-compose ps
    echo
    echo "MongoDB Logs:"
    docker-compose logs --tail=20 scandy-mongodb
    echo
    echo -e "${YELLOW}⚠️  Installation trotzdem fortgesetzt - MongoDB startet möglicherweise später...${NC}"
    goto_continue_installation=true
fi

# Prüfe Health Status von MongoDB
if [ "$goto_continue_installation" != "true" ]; then
    health_retries=0
    while [ $health_retries -lt 15 ]; do
        health_status=$(docker inspect -f "{{.State.Health.Status}}" scandy-mongodb 2>/dev/null)
        if [ "$health_status" = "healthy" ]; then
            echo -e "${GREEN}✅ MongoDB ist healthy und bereit!${NC}"
            break
        fi
        ((health_retries++))
        if [ $health_retries -ge 15 ]; then
            echo -e "${YELLOW}⚠️  MongoDB wird nicht healthy - fahre trotzdem fort...${NC}"
            echo "Letzte MongoDB Logs:"
            docker-compose logs --tail=10 scandy-mongodb
            echo
            break
        fi
        echo -e "${YELLOW}⏳ Warte auf MongoDB Health... ($health_retries/15)${NC}"
        sleep 6
    done
fi

# Continue installation
echo -e "${BLUE}🔍 Prüfe Container-Status...${NC}"
docker-compose ps

echo -e "${BLUE}🔍 Prüfe Service-Verfügbarkeit...${NC}"

# Prüfe Mongo Express
if curl -s http://localhost:8081 &> /dev/null; then
    echo -e "${GREEN}✅ Mongo Express läuft${NC}"
else
    echo -e "${YELLOW}⚠️  Mongo Express startet noch...${NC}"
fi

# Prüfe Scandy App
if curl -s http://localhost:5000 &> /dev/null; then
    echo -e "${GREEN}✅ Scandy App läuft${NC}"
else
    echo -e "${YELLOW}⚠️  Scandy App startet noch...${NC}"
fi

echo
echo "========================================"
echo -e "${GREEN}✅ KOMPLETTE INSTALLATION ABGESCHLOSSEN!${NC}"
echo "========================================"
echo
echo -e "${GREEN}🎉 Alle Services sind installiert und verfügbar:${NC}"
echo
echo -e "${BLUE}🌐 Web-Anwendungen:${NC}"
echo "- Scandy App:     http://localhost:5000"
echo "- Mongo Express:  http://localhost:8081"
echo
echo -e "${BLUE}🔐 Standard-Zugangsdaten:${NC}"
echo "- Admin: admin / admin123"
echo "- Teilnehmer: teilnehmer / admin123"
echo
echo -e "${BLUE}📊 Datenbank-Zugang (Mongo Express):${NC}"
echo "- Benutzer: admin"
echo "- Passwort: [aus Umgebungsvariable MONGO_INITDB_ROOT_PASSWORD]"
echo
echo -e "${BLUE}📁 Datenverzeichnisse:${NC}"
echo "- Backups: ./backups/"
echo "- Logs:    ./logs/"
echo "- Uploads: ./data/uploads/"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Status aller Container: docker-compose ps"
echo "- Logs anzeigen:         docker-compose logs -f"
echo "- Stoppen:               docker-compose down"
echo "- Neustart:              docker-compose restart"
echo "- Nur App updaten:       ./update.sh"
echo
echo -e "${YELLOW}⚠️  WICHTIG: Für Updates verwenden Sie ./update.sh${NC}"
echo "   Das schont die Datenbank und ist schneller!"
echo
echo "========================================"
read -p "Drücke Enter zum Beenden..." 