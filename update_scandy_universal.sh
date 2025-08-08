#!/bin/bash

#####################################################################
# Scandy Universal Updater
# Vereinheitlichtes Update-Skript für alle Installationsmodi:
# - Docker Container
# - LXC Container 
# - Native Linux Installation
#####################################################################

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    SCANDY UNIVERSAL UPDATER                   ║"
    echo "║                         Version 1.0.0                        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# Hilfe
show_help() {
    show_banner
    echo
    echo -e "${WHITE}VERWENDUNG:${NC}"
    echo "  ./update_scandy_universal.sh [OPTIONEN]"
    echo
    echo -e "${WHITE}OPTIONEN:${NC}"
    echo "  --docker          Docker-Update erzwingen"
    echo "  --lxc            LXC-Update erzwingen" 
    echo "  --native         Native Update erzwingen"
    echo "  --auto           Automatische Erkennung (Standard)"
    echo "  --backup         Backup vor Update erstellen"
    echo "  --force          Update ohne Bestätigung"
    echo "  --rollback       Auf vorherige Version zurücksetzen"
    echo "  --ssl            SSL-Zertifikat erstellen"
    echo "  --local-ssl      Lokales SSL-Setup (für Entwicklung)"
    echo "  -h, --help       Diese Hilfe anzeigen"
    echo
    echo -e "${WHITE}BEISPIELE:${NC}"
    echo "  ./update_scandy_universal.sh --auto --backup"
    echo "  ./update_scandy_universal.sh --docker --force"
    echo "  ./update_scandy_universal.sh --rollback"
}

# Variablen
UPDATE_MODE=""
CREATE_BACKUP=false
FORCE_UPDATE=false
ROLLBACK=false
ENABLE_SSL=false
LOCAL_SSL=false
ENABLE_HTTPS=false

# Argumente parsen
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help) show_help; exit 0 ;;
            --docker) UPDATE_MODE="docker"; shift ;;
            --lxc) UPDATE_MODE="lxc"; shift ;;
            --native) UPDATE_MODE="native"; shift ;;
            --auto) UPDATE_MODE="auto"; shift ;;
            --backup) CREATE_BACKUP=true; shift ;;
            --force) FORCE_UPDATE=true; shift ;;
            --rollback) ROLLBACK=true; shift ;;
            --ssl) ENABLE_SSL=true; shift ;;
            --local-ssl) LOCAL_SSL=true; ENABLE_SSL=true; shift ;;
            --https) ENABLE_HTTPS=true; shift ;;
            *) log_error "Unbekannte Option: $1"; show_help; exit 1 ;;
        esac
    done
}

# Installationsmodus erkennen
detect_install_mode() {
    log_step "Erkenne Installationsmodus..."
    
    if [ -f "docker-compose.yml" ]; then
        log_success "Docker-Installation erkannt"
        UPDATE_MODE="docker"
    elif systemctl list-units --type=service | grep -q scandy; then
        log_success "Native Installation erkannt"
        UPDATE_MODE="native"
    elif [ -f "/opt/scandy/start_scandy.sh" ]; then
        log_success "LXC-Installation erkannt"
        UPDATE_MODE="lxc"
    else
        log_warning "Keine bekannte Installation gefunden"
        UPDATE_MODE="unknown"
    fi
}

# Service-Namen für systemd bestimmen (einheitlich)
get_service_name() {
    local instance_name="$1"
    if [ -z "$instance_name" ] || [ "$instance_name" = "scandy" ]; then
        echo "scandy"
    else
        echo "scandy-$instance_name"
    fi
}

# Git Safe Directory setzen (für Root und scandy)
ensure_git_safe_dir() {
    local dir="$1"
    git config --global --add safe.directory "$dir" 2>/dev/null || true
    if id scandy &>/dev/null; then
        sudo -u scandy git config --global --add safe.directory "$dir" 2>/dev/null || true
    fi
}

# Sitzungspfad und Berechtigungen sicherstellen
ensure_runtime_dirs() {
    local base="/opt/scandy/app"
    sudo -u scandy mkdir -p "$base/flask_session" 2>/dev/null || sudo mkdir -p "$base/flask_session"
    sudo chown -R scandy:scandy "$base/flask_session" 2>/dev/null || true
    sudo find "$base/flask_session" -type d -exec chmod 700 {} + 2>/dev/null || true
    sudo find "$base/flask_session" -type f -exec chmod 600 {} + 2>/dev/null || true
    # häufig benötigte Verzeichnisse
    for d in uploads backups logs; do
        sudo -u scandy mkdir -p "$base/$d" 2>/dev/null || sudo mkdir -p "$base/$d"
        sudo chown -R scandy:scandy "$base/$d" 2>/dev/null || true
    done
}

# MongoDB-URI korrigieren falls nötig
fix_mongodb_uri() {
    log_step "Prüfe MongoDB-URI Konfiguration..."
    
    if [ ! -f ".env" ]; then
        log_warning "Keine .env-Datei gefunden"
        return
    fi
    
    # Aktueller Wert
    CURRENT_URI=$(grep "MONGODB_URI=" .env | cut -d'=' -f2-)
    INSTANCE_NAME=$(grep "INSTANCE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "scandy")
    
    # Prüfe ob es eine Docker-Installation ist und localhost verwendet
    if [ "$UPDATE_MODE" = "docker" ] && [[ "$CURRENT_URI" == *"localhost:"* ]]; then
        log_warning "Docker-Installation mit localhost MongoDB-URI erkannt - korrigiere..."
        
        # Extrahiere Passwort aus aktueller URI
        MONGO_PASSWORD=$(echo "$CURRENT_URI" | sed -n 's/.*admin:\([^@]*\)@.*/\1/p')
        
        if [ -n "$MONGO_PASSWORD" ]; then
            # Korrigiere URI für Docker
            NEW_URI="mongodb://admin:${MONGO_PASSWORD}@scandy-mongodb-${INSTANCE_NAME}:27017/scandy?authSource=admin"
            
            # Backup der .env
            cp .env .env.backup.mongodb-fix
            
            # Ersetze URI
            sed -i "s|MONGODB_URI=.*|MONGODB_URI=$NEW_URI|" .env
            
            log_success "MongoDB-URI korrigiert für Docker-Installation"
            log_info "Backup erstellt: .env.backup.mongodb-fix"
        else
            log_warning "Konnte Passwort nicht aus URI extrahieren"
        fi
    elif [ "$UPDATE_MODE" != "docker" ] && [[ "$CURRENT_URI" == *"scandy-mongodb-"* ]]; then
        log_warning "Native Installation mit Container MongoDB-URI erkannt - korrigiere..."
        
        # Extrahiere Passwort
        MONGO_PASSWORD=$(echo "$CURRENT_URI" | sed -n 's/.*admin:\([^@]*\)@.*/\1/p')
        MONGODB_PORT=$(grep "MONGODB_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "27017")
        
        if [ -n "$MONGO_PASSWORD" ]; then
            # Korrigiere URI für Native/LXC
            NEW_URI="mongodb://admin:${MONGO_PASSWORD}@localhost:${MONGODB_PORT}/scandy?authSource=admin"
            
            # Backup der .env
            cp .env .env.backup.mongodb-fix
            
            # Ersetze URI
            sed -i "s|MONGODB_URI=.*|MONGODB_URI=$NEW_URI|" .env
            
            log_success "MongoDB-URI korrigiert für Native/LXC-Installation"
            log_info "Backup erstellt: .env.backup.mongodb-fix"
        else
            log_warning "Konnte Passwort nicht aus URI extrahieren"
        fi
    else
        log_success "MongoDB-URI ist bereits korrekt"
    fi
}

# SSL-Setup Funktionen
setup_local_ssl() {
    log_step "Konfiguriere lokales SSL-Setup..."
    
    # Server-IP ermitteln
    SERVER_IP=$(hostname -I | awk '{print $1}')
    log_info "Server-IP: $SERVER_IP"
    
    # SSL-Verzeichnisse erstellen
    sudo mkdir -p /etc/ssl/scandy
    sudo mkdir -p /etc/nginx/sites-available
    sudo mkdir -p /etc/nginx/sites-enabled
    
    # Selbst-signiertes Zertifikat erstellen
    log_info "Erstelle selbst-signiertes SSL-Zertifikat..."
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/scandy/scandy.key \
        -out /etc/ssl/scandy/scandy.crt \
        -subj "/C=DE/ST=Germany/L=Local/O=Scandy/OU=IT/CN=$SERVER_IP" \
        -addext "subjectAltName=DNS:localhost,DNS:$SERVER_IP,IP:$SERVER_IP,IP:127.0.0.1"
    
    log_success "SSL-Zertifikat erstellt"
    
    # Nginx installieren (falls nicht vorhanden)
    if ! command -v nginx &> /dev/null; then
        log_info "Installiere Nginx..."
        if command -v apt &> /dev/null; then
            sudo apt update
            sudo apt install nginx -y
        elif command -v yum &> /dev/null; then
            sudo yum install nginx -y
        fi
        sudo systemctl enable nginx
        sudo systemctl start nginx
        log_success "Nginx installiert und gestartet"
    else
        log_success "Nginx bereits installiert"
    fi
    
    # Nginx-Konfiguration für lokales HTTPS
    log_info "Erstelle Nginx-Konfiguration für lokales HTTPS..."
    
    sudo tee /etc/nginx/sites-available/scandy-local > /dev/null <<EOF
# HTTP zu HTTPS Umleitung
server {
    listen 80;
    server_name $SERVER_IP localhost;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS Server mit selbst-signiertem Zertifikat
server {
    listen 443 ssl http2;
    server_name $SERVER_IP localhost;
    
    # SSL-Konfiguration
    ssl_certificate /etc/ssl/scandy/scandy.crt;
    ssl_certificate_key /etc/ssl/scandy/scandy.key;
    
    # SSL-Sicherheitseinstellungen
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    
    # Proxy-Einstellungen für Scandy
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # Timeout-Einstellungen
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer-Einstellungen
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Static Files (mit Cache)
    location /static/ {
        proxy_pass http://localhost:5000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Uploads (mit Sicherheitseinschränkungen)
    location /uploads/ {
        proxy_pass http://localhost:5000;
        # Verhindere Ausführung von Dateien
        location ~* \.(php|pl|py|jsp|asp|sh|cgi)$ {
            deny all;
        }
    }
    
    # Health Check (ohne Security Headers)
    location /health {
        proxy_pass http://localhost:5000;
        access_log off;
    }
    
    # Verstecke Server-Informationen
    server_tokens off;
    
    # Rate Limiting
    limit_req_zone \$binary_remote_addr zone=scandy:10m rate=10r/s;
    limit_req zone=scandy burst=20 nodelay;
    
    # Logging
    access_log /var/log/nginx/scandy_access.log;
    error_log /var/log/nginx/scandy_error.log;
}
EOF
    
    # Nginx-Konfiguration aktivieren
    sudo ln -sf /etc/nginx/sites-available/scandy-local /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx
    log_success "Nginx-Konfiguration aktiviert"
    
    # Firewall konfigurieren
    log_info "Konfiguriere Firewall..."
    if command -v ufw &> /dev/null; then
        sudo ufw allow 22/tcp    # SSH
        sudo ufw allow 80/tcp    # HTTP
        sudo ufw allow 443/tcp   # HTTPS
        sudo ufw --force enable
        log_success "UFW Firewall konfiguriert"
    elif command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --permanent --add-service=ssh
        sudo firewall-cmd --permanent --add-service=http
        sudo firewall-cmd --permanent --add-service=https
        sudo firewall-cmd --reload
        log_success "firewalld konfiguriert"
    else
        log_warning "Keine Firewall erkannt - manuelle Konfiguration empfohlen"
    fi
    
    log_success "Lokales SSL-Setup abgeschlossen!"
    log_info "Zugang: https://$SERVER_IP"
    log_warning "Browser-Warnung ist normal - Zertifikat importieren für bessere UX"
}

# Backup erstellen
create_backup() {
    if [ "$CREATE_BACKUP" = true ]; then
        log_step "Erstelle Backup..."
        
        BACKUP_DIR="backup_before_update_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Konfiguration sichern
        [ -f ".env" ] && cp .env "$BACKUP_DIR/"
        [ -f "docker-compose.yml" ] && cp docker-compose.yml "$BACKUP_DIR/"
        
        # Daten sichern (je nach Modus)
        case $UPDATE_MODE in
            docker)
                docker compose exec scandy-app-* bash -c "cd /app && python -c 'from app.utils.backup_manager import backup_manager; backup_manager.create_backup()'" || true
                ;;
            native|lxc)
                cd /opt/scandy && python3 -c "from app.utils.backup_manager import backup_manager; backup_manager.create_backup()" || true
                ;;
        esac
        
        # Logs sichern
        [ -d "logs" ] && cp -r logs "$BACKUP_DIR/"
        
        log_success "Backup erstellt: $BACKUP_DIR"
    fi
}

# Docker-Update
update_docker() {
    log_step "Docker-Update wird durchgeführt..."
    
    # Services stoppen
    log_info "Stoppe Container..."
    docker compose down
    
    # Images und Volumes komplett entfernen
    log_info "Entferne alte Images und Volumes..."
    docker compose down -v
    docker image rm scandy-local:dev-scandy 2>/dev/null || true
    
    # Images neu bauen mit Requirements-Rebuild
    log_info "Baue neue Images..."
    docker compose build --no-cache --build-arg REBUILD_REQUIREMENTS=true
    
    # Services starten
    log_info "Starte Container..."
    docker compose up -d
    
    # Container neu starten um gemountete Volumes zu aktualisieren
    log_info "Starte App-Container neu um Code-Updates zu laden..."
    docker compose restart scandy-app-$(grep "INSTANCE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "scandy")
    
    # Warte auf Services
    log_info "Warte auf Services..."
    for i in {1..30}; do
        if curl -f http://localhost:$(grep "WEB_PORT=" .env | cut -d'=' -f2)/health &>/dev/null; then
            log_success "Docker-Update abgeschlossen"
            return 0
        fi
        sleep 2
    done
    
    log_warning "Services brauchen länger zum Starten"
}

# Native Update
update_native() {
    log_step "Native Update wird durchgeführt..."
    
    # Service stoppen
    INSTANCE_NAME=$(grep "INSTANCE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "scandy")
    SERVICE_NAME=$(get_service_name "$INSTANCE_NAME")
    log_info "Stoppe Service $SERVICE_NAME..."
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    
    # Code aktualisieren
    log_info "Aktualisiere Code..."
    cd /opt/scandy
    ensure_git_safe_dir "/opt/scandy"
    git pull || log_warning "Git pull fehlgeschlagen"
    
    # Dependencies aktualisieren
    log_info "Aktualisiere Python-Pakete..."
    sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt

    # Laufzeitverzeichnisse & Berechtigungen
    ensure_runtime_dirs
    
    # Service starten
    log_info "Starte Service..."
    sudo systemctl start "$SERVICE_NAME"
    
    # Status prüfen
    sleep 5
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Native Update abgeschlossen"
    else
        log_error "Service konnte nicht gestartet werden"
        sudo systemctl status "$SERVICE_NAME"
    fi
}

# LXC Update
update_lxc() {
    log_step "LXC-Update wird durchgeführt..."
    
    # Prozess stoppen
    log_info "Stoppe Scandy-Prozess..."
    pkill -f "gunicorn.*scandy" || true
    
    # Code aktualisieren
    log_info "Aktualisiere Code..."
    cd /opt/scandy
    ensure_git_safe_dir "/opt/scandy"
    git pull || log_warning "Git pull fehlgeschlagen"
    
    # Stelle sicher, dass alle Dateien korrekt kopiert sind
    log_info "Stelle sicher, dass Code korrekt kopiert ist..."
    
    # Prüfe ob app-Verzeichnis existiert
    if [ ! -d "app" ]; then
        log_error "app-Verzeichnis nicht gefunden!"
        exit 1
    fi
    
    # Kopiere Code in den Container (falls nötig)
    if [ -d "/opt/scandy/app" ]; then
        log_info "Kopiere aktualisierten Code..."
        cp -r app/* /opt/scandy/app/ 2>/dev/null || {
            log_warning "Konnte Code nicht kopieren, verwende Git-Version"
        }
    fi
    
    # Dependencies aktualisieren
    log_info "Aktualisiere Python-Pakete..."
    sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt

    # Laufzeitverzeichnisse & Berechtigungen
    ensure_runtime_dirs
    
    # Service starten
    log_info "Starte Scandy..."
    sudo -u scandy ./start_scandy.sh &
    
    # Warte auf Service
    sleep 5
    WEB_PORT=$(grep "WEB_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "5000")
    if curl -f http://localhost:$WEB_PORT/health &>/dev/null; then
        log_success "LXC-Update abgeschlossen"
    else
        log_warning "Service braucht länger zum Starten"
    fi
}

# Rollback durchführen
perform_rollback() {
    log_step "Führe Rollback durch..."
    
    # Neuestes Backup finden
    LATEST_BACKUP=$(ls -t backup_before_update_* 2>/dev/null | head -1)
    
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "Kein Backup für Rollback gefunden!"
        exit 1
    fi
    
    log_info "Verwende Backup: $LATEST_BACKUP"
    
    # Bestätigung (außer bei --force)
    if [ "$FORCE_UPDATE" = false ]; then
        echo -e "${YELLOW}⚠️  Rollback wird die aktuelle Installation überschreiben!${NC}"
        read -p "Fortfahren? (j/N): " confirm
        if [[ ! $confirm =~ ^[Jj]$ ]]; then
            log_info "Rollback abgebrochen"
            exit 0
        fi
    fi
    
    # Konfiguration wiederherstellen
    [ -f "$LATEST_BACKUP/.env" ] && cp "$LATEST_BACKUP/.env" .
    [ -f "$LATEST_BACKUP/docker-compose.yml" ] && cp "$LATEST_BACKUP/docker-compose.yml" .
    
    # Services neu starten
    case $UPDATE_MODE in
        docker)
            docker compose down
            docker compose up -d
            ;;
        native)
            INSTANCE_NAME=$(grep "INSTANCE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "scandy")
            sudo systemctl restart scandy-$INSTANCE_NAME
            ;;
        lxc)
            pkill -f "gunicorn.*scandy" || true
            cd /opt/scandy && sudo -u scandy ./start_scandy.sh &
            ;;
    esac
    
    log_success "Rollback abgeschlossen"
}

# Hauptfunktion
main() {
    show_banner
    
    # Argumente parsen
    parse_arguments "$@"
    
    # SSL-Setup durchführen
    if [ "$ENABLE_SSL" = true ]; then
        setup_local_ssl
    fi

    # Rollback-Modus
    if [ "$ROLLBACK" = true ]; then
        detect_install_mode
        perform_rollback
        exit 0
    fi
    
    # Installationsmodus erkennen
    if [ -z "$UPDATE_MODE" ] || [ "$UPDATE_MODE" = "auto" ]; then
        detect_install_mode
    fi
    
    if [ "$UPDATE_MODE" = "unknown" ]; then
        log_error "Keine bekannte Scandy-Installation gefunden!"
        exit 1
    fi
    
    log_info "Update-Modus: $UPDATE_MODE"
    
    # Bestätigung (außer bei --force)
    if [ "$FORCE_UPDATE" = false ]; then
        echo -e "${YELLOW}⚠️  Update wird durchgeführt für: $UPDATE_MODE${NC}"
        read -p "Fortfahren? (j/N): " confirm
        if [[ ! $confirm =~ ^[Jj]$ ]]; then
            log_info "Update abgebrochen"
            exit 0
        fi
    fi
    
    # MongoDB-URI korrigieren falls nötig
    fix_mongodb_uri
    
    # Backup erstellen
    create_backup
    
    # Update durchführen
    case $UPDATE_MODE in
        docker)
            update_docker
            ;;
        native)
            update_native
            ;;
        lxc)
            update_lxc
            ;;
        *)
            log_error "Unbekannter Update-Modus: $UPDATE_MODE"
            exit 1
            ;;
    esac
    
    # Finale Info
    echo
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                      UPDATE ABGESCHLOSSEN                     ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${WHITE}✅ Scandy wurde erfolgreich aktualisiert${NC}"
    echo -e "${WHITE}📊 Update-Modus: $UPDATE_MODE${NC}"
    if [ "$CREATE_BACKUP" = true ]; then
        echo -e "${WHITE}💾 Backup erstellt: ${BACKUP_DIR:-"Siehe oben"}${NC}"
    fi
    echo
    echo -e "${WHITE}🔄 Bei Problemen: ./update_scandy_universal.sh --rollback${NC}"
    echo
}

# Skript ausführen
main "$@"