#!/bin/bash

#####################################################################
# Scandy Quick Update Script
# Schnelles Update nur für Code-Änderungen ohne vollständigen Rebuild
#####################################################################

set -e

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Prüfe ob wir im Scandy-Verzeichnis sind
if [ ! -f "docker-compose.yml" ]; then
    log_error "Bitte führen Sie dieses Script im Scandy-Verzeichnis aus!"
    exit 1
fi

# Prüfe ob .env existiert
if [ ! -f ".env" ]; then
    log_error ".env Datei nicht gefunden!"
    exit 1
fi

# Lade Umgebungsvariablen
source .env

log_info "Scandy Quick Update gestartet..."

# Git Pull
log_info "Aktualisiere Code von Git..."
git pull origin main || git pull origin master || {
    log_warning "Git pull fehlgeschlagen, verwende aktuellen Code"
}

# Prüfe ob Docker läuft
if command -v docker &> /dev/null && docker info &> /dev/null; then
    log_info "Docker-Installation erkannt"
    
    # Container-Namen ermitteln
    INSTANCE_NAME=${INSTANCE_NAME:-scandy}
    CONTAINER_NAME="scandy-app-${INSTANCE_NAME}"
    
    # Prüfe ob Container läuft
    if docker ps | grep -q "$CONTAINER_NAME"; then
        log_info "Container läuft, starte neu..."
        
        # Container neu starten
        docker compose restart "$CONTAINER_NAME"
        
        # Warte auf Service
        log_info "Warte auf Service..."
        for i in {1..15}; do
            if curl -f http://localhost:${WEB_PORT:-5000}/health &>/dev/null; then
                log_success "Quick Update abgeschlossen!"
                log_info "Service ist verfügbar unter: http://localhost:${WEB_PORT:-5000}"
                exit 0
            fi
            sleep 2
        done
        
        log_warning "Service braucht länger zum Starten"
    else
        log_info "Container läuft nicht, starte Services..."
        docker compose up -d
    fi
    
elif systemctl is-active --quiet scandy-${INSTANCE_NAME:-scandy} 2>/dev/null; then
    log_info "Native-Installation erkannt"
    
    # Service neu starten
    log_info "Starte Service neu..."
    sudo systemctl restart scandy-${INSTANCE_NAME:-scandy}
    
    # Warte auf Service
    sleep 3
    if systemctl is-active --quiet scandy-${INSTANCE_NAME:-scandy}; then
        log_success "Quick Update abgeschlossen!"
    else
        log_error "Service konnte nicht gestartet werden"
        sudo systemctl status scandy-${INSTANCE_NAME:-scandy}
    fi
    
else
    log_info "LXC-Installation erkannt"
    
    # Prozess neu starten
    log_info "Starte Scandy-Prozess neu..."
    pkill -f "gunicorn.*scandy" || true
    sleep 2
    
    # Starte Scandy
    if [ -f "start_scandy.sh" ]; then
        sudo -u scandy ./start_scandy.sh &
    else
        cd /opt/scandy
        sudo -u scandy ./start_scandy.sh &
    fi
    
    # Warte auf Service
    sleep 5
    if curl -f http://localhost:${WEB_PORT:-5000}/health &>/dev/null; then
        log_success "Quick Update abgeschlossen!"
    else
        log_warning "Service braucht länger zum Starten"
    fi
fi

log_info "Update abgeschlossen!" 