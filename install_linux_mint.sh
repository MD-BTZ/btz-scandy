#!/bin/bash

# Scandy Linux Mint Installer
# Installiert Scandy ohne Docker auf einem Linux Mint System

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

# Prüfe ob als Root ausgeführt
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "Dieses Skript sollte nicht als Root ausgeführt werden!"
        print_warning "Führe das Skript als normaler Benutzer aus."
        exit 1
    fi
}

# Prüfe Linux Mint
check_linux_mint() {
    if ! grep -q "Linux Mint" /etc/os-release; then
        print_warning "Dieses Skript wurde für Linux Mint entwickelt."
        print_warning "Es könnte auch auf anderen Ubuntu-basierten Systemen funktionieren."
        read -p "Möchten Sie fortfahren? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Aktualisiere System
update_system() {
    print_status "Aktualisiere System-Pakete..."
    sudo apt update
    sudo apt upgrade -y
    print_success "System aktualisiert"
}

# Installiere Abhängigkeiten
install_dependencies() {
    print_status "Installiere System-Abhängigkeiten..."
    
    # Python und pip
    sudo apt install -y python3 python3-pip python3-venv
    
    # MongoDB
    print_status "Installiere MongoDB..."
    wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    sudo apt update
    sudo apt install -y mongodb-org
    
    # Weitere Abhängigkeiten
    sudo apt install -y curl wget git build-essential
    
    # Node.js für Tailwind CSS (falls benötigt)
    print_status "Installiere Node.js für CSS-Build..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
    
    print_success "Alle Abhängigkeiten installiert"
}

# Starte MongoDB
setup_mongodb() {
    print_status "Konfiguriere MongoDB..."
    
    # Starte MongoDB Service
    sudo systemctl enable mongod
    sudo systemctl start mongod
    
    # Warte kurz bis MongoDB läuft
    sleep 3
    
    # Prüfe MongoDB Status
    if sudo systemctl is-active --quiet mongod; then
        print_success "MongoDB läuft"
    else
        print_error "MongoDB konnte nicht gestartet werden"
        exit 1
    fi
}

# Erstelle Python Virtual Environment
setup_python_env() {
    print_status "Erstelle Python Virtual Environment..."
    
    # Erstelle venv
    python3 -m venv venv
    
    # Aktiviere venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    print_success "Python Environment erstellt"
}

# Installiere Python-Pakete
install_python_packages() {
    print_status "Installiere Python-Pakete..."
    
    # Aktiviere venv falls nicht aktiv
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        source venv/bin/activate
    fi
    
    # Installiere Requirements
    pip install -r requirements.txt
    
    print_success "Python-Pakete installiert"
}

# Erstelle notwendige Verzeichnisse
create_directories() {
    print_status "Erstelle notwendige Verzeichnisse..."
    
    # Erstelle Upload-Verzeichnisse
    mkdir -p app/uploads
    mkdir -p app/static/uploads
    
    # Erstelle Backup-Verzeichnis
    mkdir -p backups
    
    # Erstelle Log-Verzeichnisse
    mkdir -p logs
    mkdir -p app/logs
    
    # Erstelle Session-Verzeichnis
    mkdir -p app/flask_session
    
    # Setze Berechtigungen
    chmod 755 app/uploads
    chmod 755 app/static/uploads
    chmod 755 backups
    chmod 755 logs
    chmod 755 app/logs
    chmod 755 app/flask_session
    
    print_success "Verzeichnisse erstellt"
}

# Erstelle .env Datei
create_env_file() {
    print_status "Erstelle .env Konfigurationsdatei..."
    
    # Generiere Secret Key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Erstelle .env Datei
    cat > .env << EOF
# Scandy Konfiguration
FLASK_ENV=production
FLASK_CONFIG=production

# MongoDB Konfiguration
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=scandy
MONGODB_COLLECTION_PREFIX=

# Sicherheit
SECRET_KEY=$SECRET_KEY

# Session Konfiguration
SESSION_TYPE=filesystem
SESSION_FILE_DIR=app/flask_session
SESSION_PERMANENT=True
PERMANENT_SESSION_LIFETIME=86400

# Server Einstellungen
HOST=0.0.0.0
PORT=5000

# Email Konfiguration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Base URL (wird automatisch erkannt)
BASE_URL=

# Cookie Sicherheit (für lokale Entwicklung)
SESSION_COOKIE_SECURE=False
REMEMBER_COOKIE_SECURE=False
EOF

    print_success ".env Datei erstellt"
    print_warning "Bitte bearbeiten Sie die .env Datei und konfigurieren Sie Ihre E-Mail-Einstellungen"
}

# Erstelle Systemd Service
create_systemd_service() {
    print_status "Erstelle Systemd Service..."
    
    # Hole aktuellen Benutzer
    USER=$(whoami)
    WORKING_DIR=$(pwd)
    
    # Erstelle Service-Datei
    sudo tee /etc/systemd/system/scandy.service > /dev/null << EOF
[Unit]
Description=Scandy Web Application
After=network.target mongod.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$WORKING_DIR
Environment=PATH=$WORKING_DIR/venv/bin
ExecStart=$WORKING_DIR/venv/bin/python app/wsgi.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Lade Systemd neu
    sudo systemctl daemon-reload
    
    # Aktiviere Service
    sudo systemctl enable scandy.service
    
    print_success "Systemd Service erstellt"
}

# Erstelle Nginx Konfiguration (optional)
create_nginx_config() {
    print_status "Erstelle Nginx Konfiguration..."
    
    # Installiere Nginx falls nicht vorhanden
    if ! command -v nginx &> /dev/null; then
        sudo apt install -y nginx
    fi
    
    # Erstelle Nginx Konfiguration
    sudo tee /etc/nginx/sites-available/scandy > /dev/null << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $WORKING_DIR/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Aktiviere Site
    sudo ln -sf /etc/nginx/sites-available/scandy /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Teste Nginx Konfiguration
    sudo nginx -t
    
    # Starte Nginx
    sudo systemctl enable nginx
    sudo systemctl restart nginx
    
    print_success "Nginx konfiguriert"
}

# Erstelle Firewall-Regeln
setup_firewall() {
    print_status "Konfiguriere Firewall..."
    
    # Erlaube SSH (falls nicht bereits erlaubt)
    sudo ufw allow ssh
    
    # Erlaube HTTP und HTTPS
    sudo ufw allow 80
    sudo ufw allow 443
    
    # Erlaube Scandy Port (falls nicht über Nginx)
    sudo ufw allow 5000
    
    # Aktiviere Firewall
    echo "y" | sudo ufw enable
    
    print_success "Firewall konfiguriert"
}

# Erstelle Backup-Skript
create_backup_script() {
    print_status "Erstelle Backup-Skript..."
    
    cat > backup_scandy.sh << 'EOF'
#!/bin/bash

# Scandy Backup Skript
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="scandy_backup_$DATE"

echo "Erstelle Backup: $BACKUP_NAME"

# Erstelle Backup-Verzeichnis
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup MongoDB
mongodump --db scandy --out "$BACKUP_DIR/$BACKUP_NAME/mongodb"

# Backup Uploads
cp -r app/uploads "$BACKUP_DIR/$BACKUP_NAME/"

# Backup Konfiguration
cp .env "$BACKUP_DIR/$BACKUP_NAME/"

# Erstelle Archiv
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

echo "Backup erstellt: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
EOF

    chmod +x backup_scandy.sh
    print_success "Backup-Skript erstellt"
}

# Erstelle Update-Skript
create_update_script() {
    print_status "Erstelle Update-Skript..."
    
    cat > update_scandy.sh << 'EOF'
#!/bin/bash

# Scandy Update Skript
echo "Aktualisiere Scandy..."

# Stoppe Service
sudo systemctl stop scandy.service

# Aktiviere Virtual Environment
source venv/bin/activate

# Update Python-Pakete
pip install -r requirements.txt --upgrade

# Starte Service
sudo systemctl start scandy.service

echo "Scandy aktualisiert"
EOF

    chmod +x update_scandy.sh
    print_success "Update-Skript erstellt"
}

# Erstelle Management-Skript
create_management_script() {
    print_status "Erstelle Management-Skript..."
    
    cat > manage_scandy.sh << 'EOF'
#!/bin/bash

# Scandy Management Skript
case "$1" in
    start)
        echo "Starte Scandy..."
        sudo systemctl start scandy.service
        ;;
    stop)
        echo "Stoppe Scandy..."
        sudo systemctl stop scandy.service
        ;;
    restart)
        echo "Starte Scandy neu..."
        sudo systemctl restart scandy.service
        ;;
    status)
        echo "Scandy Status:"
        sudo systemctl status scandy.service
        ;;
    logs)
        echo "Scandy Logs:"
        sudo journalctl -u scandy.service -f
        ;;
    backup)
        echo "Erstelle Backup..."
        ./backup_scandy.sh
        ;;
    update)
        echo "Update Scandy..."
        ./update_scandy.sh
        ;;
    *)
        echo "Verwendung: $0 {start|stop|restart|status|logs|backup|update}"
        exit 1
        ;;
esac
EOF

    chmod +x manage_scandy.sh
    print_success "Management-Skript erstellt"
}

# Hauptinstallation
main() {
    echo "=========================================="
    echo "    Scandy Linux Mint Installer"
    echo "=========================================="
    echo
    
    # Prüfungen
    check_root
    check_linux_mint
    
    # Installation
    update_system
    install_dependencies
    setup_mongodb
    setup_python_env
    install_python_packages
    create_directories
    create_env_file
    create_systemd_service
    
    # Optionale Komponenten
    read -p "Möchten Sie Nginx als Reverse Proxy installieren? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_status "Nginx wird übersprungen"
    else
        create_nginx_config
    fi
    
    setup_firewall
    create_backup_script
    create_update_script
    create_management_script
    
    # Finale Schritte
    print_status "Starte Scandy Service..."
    sudo systemctl start scandy.service
    
    # Prüfe Status
    if sudo systemctl is-active --quiet scandy.service; then
        print_success "Scandy läuft erfolgreich!"
    else
        print_error "Scandy konnte nicht gestartet werden"
        print_status "Prüfen Sie die Logs mit: sudo journalctl -u scandy.service"
        exit 1
    fi
    
    echo
    echo "=========================================="
    echo "    Installation abgeschlossen!"
    echo "=========================================="
    echo
    echo "Scandy ist jetzt verfügbar unter:"
    echo "  - Lokal: http://localhost:5000"
    echo "  - Netzwerk: http://$(hostname -I | awk '{print $1}'):5000"
    if command -v nginx &> /dev/null; then
        echo "  - Über Nginx: http://$(hostname -I | awk '{print $1}')"
    fi
    echo
    echo "Verwaltung:"
    echo "  - Status prüfen: ./manage_scandy.sh status"
    echo "  - Logs anzeigen: ./manage_scandy.sh logs"
    echo "  - Backup erstellen: ./manage_scandy.sh backup"
    echo "  - Update: ./manage_scandy.sh update"
    echo
    echo "Wichtige Hinweise:"
    echo "  1. Bearbeiten Sie die .env Datei für Ihre E-Mail-Konfiguration"
    echo "  2. Erstellen Sie einen ersten Admin-Benutzer über die Web-Oberfläche"
    echo "  3. Regelmäßige Backups sind wichtig!"
    echo
}

# Führe Installation aus
main "$@" 