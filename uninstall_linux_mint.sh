#!/bin/bash

# Scandy Linux Mint Deinstaller
# Entfernt Scandy komplett vom System

set -e

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Bestätigung
confirm_deinstallation() {
    echo "=========================================="
    echo "    Scandy Deinstallation"
    echo "=========================================="
    echo
    print_warning "Dies wird Scandy komplett vom System entfernen!"
    print_warning "Alle Daten werden gelöscht!"
    echo
    read -p "Sind Sie sicher? (yes/NO): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Deinstallation abgebrochen."
        exit 0
    fi
}

# Stoppe Services
stop_services() {
    print_status "Stoppe Scandy Services..."
    
    # Stoppe Scandy Service
    if sudo systemctl is-active --quiet scandy.service; then
        sudo systemctl stop scandy.service
        print_success "Scandy Service gestoppt"
    fi
    
    # Deaktiviere Scandy Service
    if sudo systemctl is-enabled --quiet scandy.service; then
        sudo systemctl disable scandy.service
        print_success "Scandy Service deaktiviert"
    fi
    
    # Entferne Service-Datei
    if [ -f /etc/systemd/system/scandy.service ]; then
        sudo rm /etc/systemd/system/scandy.service
        print_success "Service-Datei entfernt"
    fi
    
    # Lade Systemd neu
    sudo systemctl daemon-reload
}

# Entferne Nginx-Konfiguration
remove_nginx() {
    print_status "Entferne Nginx-Konfiguration..."
    
    # Entferne Scandy Site
    if [ -f /etc/nginx/sites-enabled/scandy ]; then
        sudo rm /etc/nginx/sites-enabled/scandy
        print_success "Nginx Site entfernt"
    fi
    
    if [ -f /etc/nginx/sites-available/scandy ]; then
        sudo rm /etc/nginx/sites-available/scandy
        print_success "Nginx Konfiguration entfernt"
    fi
    
    # Teste Nginx-Konfiguration
    if command -v nginx &> /dev/null; then
        sudo nginx -t
        sudo systemctl reload nginx
        print_success "Nginx-Konfiguration aktualisiert"
    fi
}

# Entferne MongoDB (optional)
remove_mongodb() {
    print_status "Prüfe MongoDB..."
    
    read -p "Möchten Sie MongoDB auch entfernen? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Entferne MongoDB..."
        
        # Stoppe MongoDB
        if sudo systemctl is-active --quiet mongod; then
            sudo systemctl stop mongod
            print_success "MongoDB gestoppt"
        fi
        
        # Deaktiviere MongoDB
        if sudo systemctl is-enabled --quiet mongod; then
            sudo systemctl disable mongod
            print_success "MongoDB deaktiviert"
        fi
        
        # Entferne MongoDB-Pakete
        sudo apt remove --purge mongodb-org* -y
        print_success "MongoDB-Pakete entfernt"
        
        # Entferne MongoDB-Daten
        if [ -d /var/lib/mongodb ]; then
            sudo rm -rf /var/lib/mongodb
            print_success "MongoDB-Daten entfernt"
        fi
        
        if [ -d /var/log/mongodb ]; then
            sudo rm -rf /var/log/mongodb
            print_success "MongoDB-Logs entfernt"
        fi
        
        # Entferne Repository
        if [ -f /etc/apt/sources.list.d/mongodb-org-7.0.list ]; then
            sudo rm /etc/apt/sources.list.d/mongodb-org-7.0.list
            print_success "MongoDB Repository entfernt"
        fi
        
        # Aktualisiere Paketliste
        sudo apt update
    else
        print_status "MongoDB wird beibehalten"
    fi
}

# Entferne Firewall-Regeln
remove_firewall_rules() {
    print_status "Entferne Firewall-Regeln..."
    
    # Entferne Scandy-spezifische Regeln
    sudo ufw delete allow 5000 2>/dev/null || true
    print_success "Firewall-Regeln entfernt"
}

# Entferne Anwendungsverzeichnis
remove_application() {
    print_status "Entferne Anwendungsverzeichnis..."
    
    # Hole aktuelles Verzeichnis
    CURRENT_DIR=$(pwd)
    
    # Prüfe ob wir im Scandy-Verzeichnis sind
    if [ -f "requirements.txt" ] && [ -d "app" ]; then
        print_warning "Entferne aktuelles Verzeichnis: $CURRENT_DIR"
        
        # Wechsle ins übergeordnete Verzeichnis
        cd ..
        
        # Entferne Verzeichnis
        rm -rf "$CURRENT_DIR"
        print_success "Anwendungsverzeichnis entfernt"
    else
        print_warning "Kein Scandy-Verzeichnis gefunden"
    fi
}

# Entferne Management-Skripte
remove_scripts() {
    print_status "Entferne Management-Skripte..."
    
    # Entferne Skripte falls sie existieren
    rm -f backup_scandy.sh
    rm -f update_scandy.sh
    rm -f manage_scandy.sh
    
    print_success "Management-Skripte entfernt"
}

# Bereinige System
cleanup_system() {
    print_status "Bereinige System..."
    
    # Entferne nicht verwendete Pakete
    sudo apt autoremove -y
    
    # Bereinige Paket-Cache
    sudo apt autoclean
    
    print_success "System bereinigt"
}

# Hauptfunktion
main() {
    # Prüfe Root-Rechte
    if [[ $EUID -eq 0 ]]; then
        print_error "Dieses Skript sollte nicht als Root ausgeführt werden!"
        exit 1
    fi
    
    # Bestätigung
    confirm_deinstallation
    
    # Deinstallation
    stop_services
    remove_nginx
    remove_mongodb
    remove_firewall_rules
    remove_application
    remove_scripts
    cleanup_system
    
    echo
    echo "=========================================="
    echo "    Deinstallation abgeschlossen!"
    echo "=========================================="
    echo
    print_success "Scandy wurde erfolgreich entfernt!"
    echo
    echo "Entfernte Komponenten:"
    echo "  - Scandy Service"
    echo "  - Nginx-Konfiguration"
    echo "  - Anwendungsverzeichnis"
    echo "  - Management-Skripte"
    echo "  - Firewall-Regeln"
    echo
    print_warning "MongoDB wurde nur entfernt, wenn Sie es explizit gewählt haben."
    print_warning "Falls Sie MongoDB manuell entfernen möchten:"
    echo "  sudo apt remove --purge mongodb-org*"
    echo "  sudo rm -rf /var/lib/mongodb"
    echo
}

# Führe Deinstallation aus
main "$@" 