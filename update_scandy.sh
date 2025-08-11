#!/bin/bash

# Scandy Update Skript für Linux Mint (ohne LXC)
# Aktualisiert Scandy von Git und startet den Service neu

set -e  # Beende bei Fehlern

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========================================"
echo "Scandy Update für Linux Mint"
echo "========================================"
echo "Aktualisiert Scandy von Git (Branch: $(git branch --show-current))"
echo "========================================"

print_status "Prüfe aktuellen Git-Status..."
git status --short

print_status "Sichere lokale Änderungen (falls vorhanden)..."
if [[ -n $(git status --porcelain) ]]; then
    print_warning "Lokale Änderungen gefunden - erstelle Backup..."
    git stash push -m "Auto-stash vor Update $(date)"
    print_success "Lokale Änderungen gesichert"
fi

print_status "Hole neueste Version vom aktuellen Branch..."
git pull origin $(git branch --show-current)

if [ $? -ne 0 ]; then
    print_error "Git pull fehlgeschlagen!"
    exit 1
fi

print_success "Code aktualisiert"

print_status "Stoppe Scandy Service..."
sudo systemctl stop scandy.service

if [ $? -ne 0 ]; then
    print_warning "Service konnte nicht gestoppt werden (möglicherweise nicht aktiv)"
fi

print_status "Aktiviere Virtual Environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    print_success "Virtual Environment aktiviert"
else
    print_error "Virtual Environment 'venv' nicht gefunden!"
    print_error "Bitte führen Sie zuerst das Install-Script aus."
    exit 1
fi

print_status "Aktualisiere Python-Pakete..."
pip install -r requirements.txt --upgrade

if [ $? -ne 0 ]; then
    print_error "Fehler beim Installieren der Python-Pakete!"
    exit 1
fi

print_success "Python-Pakete aktualisiert"

# CSS Build (falls Node.js verfügbar)
if command -v npm &> /dev/null; then
    print_status "Baue CSS neu (Tailwind)..."
    if [ -f "package.json" ]; then
        npm install
        npm run build 2>/dev/null || print_warning "CSS Build nicht verfügbar"
    fi
fi

print_status "Korrigiere Berechtigungen..."
if [ -d "app/static" ]; then
    chmod -R 755 app/static/
    print_success "Static Files Berechtigungen korrigiert"
fi

if [ -d "logs" ]; then
    chmod -R 755 logs/
    print_success "Log-Verzeichnis Berechtigungen korrigiert"
fi

print_status "Starte Scandy Service..."
sudo systemctl start scandy.service

if [ $? -ne 0 ]; then
    print_error "Fehler beim Starten des Services!"
    print_error "Prüfen Sie die Logs: sudo journalctl -u scandy.service -f"
    exit 1
fi

print_status "Warte auf Service-Start..."
sleep 5

print_status "Prüfe Service-Status..."
sudo systemctl status scandy.service --no-pager

print_status "Aktiviere Service für Autostart..."
sudo systemctl enable scandy.service

echo
echo "========================================"
print_success "✅ SCANDY UPDATE ABGESCHLOSSEN!"
echo "========================================"
echo
print_success "🎉 Scandy wurde erfolgreich aktualisiert!"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Service-Status:   sudo systemctl status scandy.service"
echo "- Service-Logs:     sudo journalctl -u scandy.service -f"
echo "- Service-Neustart: sudo systemctl restart scandy.service"
echo "- Service stoppen:  sudo systemctl stop scandy.service"
echo
echo -e "${BLUE}📁 Wichtige Verzeichnisse:${NC}"
echo "- Logs:    ./logs/"
echo "- Backups: ./backups/"
echo "- Static:  ./app/static/"
echo
if [[ -n $(git stash list) ]]; then
    echo -e "${YELLOW}💾 Git Stash verfügbar:${NC}"
    echo "- Lokale Änderungen wiederherstellen: git stash pop"
    echo "- Stash anzeigen: git stash list"
fi
echo "========================================"
