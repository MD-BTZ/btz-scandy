#!/bin/bash

#####################################################################
# Scandy Universal Installer
# Vereinheitlichtes Installationsskript für:
# - Docker Container (empfohlen)
# - LXC Container 
# - Native Linux Installation
#
# Automatische Erkennung der Umgebung und entsprechende Installation
#####################################################################

set -e  # Beende bei Fehlern

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# ASCII Art Banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    SCANDY UNIVERSAL INSTALLER                 ║"
    echo "║                         Version 1.0.0                        ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Logging-Funktionen
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Hilfe anzeigen
show_help() {
    echo
    echo -e "${WHITE}VERWENDUNG:${NC}"
    echo "  ./install_scandy_universal.sh [OPTIONEN]"
    echo
    echo -e "${WHITE}INSTALLATIONSMODI:${NC}"
    echo "  --docker          Docker-Installation erzwingen"
    echo "  --lxc            LXC-Container-Installation erzwingen"
    echo "  --native         Native Linux-Installation erzwingen"
    echo "  --auto           Automatische Erkennung (überspringt Menü)"
    echo "  [kein Parameter] Interaktives Menü (empfohlen)"
    echo
    echo -e "${WHITE}KONFIGURATION:${NC}"
    echo "  -n, --name NAME        Instance-Name (Standard: scandy)"
    echo "  -p, --port PORT        Web-App Port (Standard: 5000)"
    echo "  -m, --mongodb-port     MongoDB Port (Standard: 27017)"
    echo "  -e, --express-port     Mongo Express Port (Standard: 8081)"
    echo "  --domain DOMAIN        Domain für Nginx-Konfiguration"
    echo "  --ssl                  SSL/HTTPS aktivieren (mit Domain)"
    echo "  --local-ssl            Lokales SSL ohne Domain (selbst-signiert)"
    echo "  --https                HTTPS für lokale Entwicklung aktivieren"
    echo
    echo -e "${WHITE}SPEZIELLE OPTIONEN:${NC}"
    echo "  -u, --update          Nur Update durchführen"
    echo "  -f, --force           Bestehende Installation überschreiben"
    echo "  --backup              Backup vor Installation erstellen"
    echo "  --production          Produktions-Konfiguration verwenden"
    echo "  --dev                 Entwicklungs-Konfiguration verwenden"
    echo
    echo -e "${WHITE}VERSCHIEDENES:${NC}"
    echo "  -h, --help            Diese Hilfe anzeigen"
    echo "  --version             Version anzeigen"
    echo "  --check-system        System-Kompatibilität prüfen"
    echo
    echo -e "${WHITE}BEISPIELE:${NC}"
    echo "  # Automatische Installation"
    echo "  ./install_scandy_universal.sh --auto"
    echo
    echo "  # Docker-Installation mit Custom-Ports"
    echo "  ./install_scandy_universal.sh --docker -p 8080 -m 27018"
    echo
    echo "  # LXC-Installation für Produktionsumgebung"
    echo "  ./install_scandy_universal.sh --lxc --production --ssl --domain scandy.company.com"
    echo
    echo "  # Native Installation mit Backup"
    echo "  ./install_scandy_universal.sh --native --backup"
    echo
    echo "  # Update bestehende Installation"
    echo "  ./install_scandy_universal.sh --update"
    echo
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

# Variablen initialisieren
INSTALL_MODE=""
INSTANCE_NAME="scandy"
WEB_PORT=5000
MONGODB_PORT=27017
MONGO_EXPRESS_PORT=8081
DOMAIN=""
ENABLE_SSL=false
LOCAL_SSL=false
ENABLE_HTTPS=false
UPDATE_ONLY=false
FORCE_INSTALL=false
CREATE_BACKUP=false
PRODUCTION_MODE=false
DEV_MODE=false

# Argumente parsen
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --version)
                echo "Scandy Universal Installer v1.0.0"
                exit 0
                ;;
            --docker)
                INSTALL_MODE="docker"
                shift
                ;;
            --lxc)
                INSTALL_MODE="lxc"
                shift
                ;;
            --native)
                INSTALL_MODE="native"
                shift
                ;;
            --auto)
                INSTALL_MODE="auto"
                shift
                ;;
            -n|--name)
                INSTANCE_NAME="$2"
                shift 2
                ;;
            -p|--port)
                WEB_PORT="$2"
                shift 2
                ;;
            -m|--mongodb-port)
                MONGODB_PORT="$2"
                shift 2
                ;;
            -e|--express-port)
                MONGO_EXPRESS_PORT="$2"
                shift 2
                ;;
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --ssl)
                ENABLE_SSL=true
                shift
                ;;
            --local-ssl)
                LOCAL_SSL=true
                ENABLE_SSL=true
                shift
                ;;
            --https)
                ENABLE_HTTPS=true
                shift
                ;;
            -u|--update)
                UPDATE_ONLY=true
                shift
                ;;
            -f|--force)
                FORCE_INSTALL=true
                shift
                ;;
            --backup)
                CREATE_BACKUP=true
                shift
                ;;
            --production)
                PRODUCTION_MODE=true
                shift
                ;;
            --dev)
                DEV_MODE=true
                shift
                ;;
            --check-system)
                check_system_compatibility
                exit 0
                ;;
            *)
                log_error "Unbekannte Option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# System-Kompatibilität prüfen
check_system_compatibility() {
    log_step "Prüfe System-Kompatibilität..."
    
    # Betriebssystem erkennen
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_success "Linux-System erkannt"
        
        # Distribution ermitteln
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            log_info "Distribution: $NAME $VERSION"
        fi
        
        # Architektur prüfen
        ARCH=$(uname -m)
        log_info "Architektur: $ARCH"
        
        if [[ "$ARCH" != "x86_64" && "$ARCH" != "aarch64" ]]; then
            log_warning "Ungetestete Architektur: $ARCH"
        fi
        
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_success "macOS erkannt"
        
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        log_error "Windows wird nicht unterstützt!"
        log_info "Bitte verwenden Sie WSL2 oder eine Linux-VM"
        exit 1
    else
        log_warning "Unbekanntes Betriebssystem: $OSTYPE"
    fi
    
    # Docker prüfen
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null 2>&1; then
            log_success "Docker ist verfügbar und läuft"
            DOCKER_AVAILABLE=true
            DOCKER_CMD="docker"
        elif sudo docker info &> /dev/null 2>&1; then
            log_warning "Docker läuft, benötigt aber sudo-Rechte"
            DOCKER_AVAILABLE=true
            DOCKER_CMD="sudo docker"
        else
            log_warning "Docker ist installiert, läuft aber nicht"
            DOCKER_AVAILABLE=false
            DOCKER_CMD="docker"
        fi
    else
        log_warning "Docker ist nicht installiert"
        DOCKER_AVAILABLE=false
        DOCKER_CMD="docker"
    fi
    
    # LXC-Umgebung prüfen
    if [ -f /.dockerenv ]; then
        log_info "Läuft in Docker-Container"
        IN_DOCKER=true
    else
        IN_DOCKER=false
    fi
    
    if [ -n "${container}" ] && [ "${container}" = "lxc" ]; then
        log_info "Läuft in LXC-Container"
        IN_LXC=true
    else
        IN_LXC=false
    fi
    
    # Systemd prüfen
    if systemctl --version &> /dev/null; then
        log_success "Systemd ist verfügbar"
        SYSTEMD_AVAILABLE=true
    else
        log_warning "Systemd ist nicht verfügbar"
        SYSTEMD_AVAILABLE=false
    fi
    
    # Root-Rechte prüfen
    if [[ $EUID -eq 0 ]]; then
        log_info "Läuft mit Root-Rechten"
        HAS_ROOT=true
    else
        log_info "Läuft ohne Root-Rechte"
        HAS_ROOT=false
    fi
    
    # Speicherplatz prüfen
    AVAILABLE_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 5 ]; then
        log_warning "Wenig Speicherplatz verfügbar: ${AVAILABLE_SPACE}GB (empfohlen: 5GB+)"
    else
        log_success "Ausreichend Speicherplatz verfügbar: ${AVAILABLE_SPACE}GB"
    fi
}

# Alle bestehenden Installationen finden
detect_all_installations() {
    log_step "Prüfe auf bestehende Scandy-Installationen..."
    
    # Arrays für gefundene Installationen
    FOUND_INSTANCES=()
    FOUND_MODES=()
    FOUND_TYPES=()
    
    # Docker-Installationen prüfen (mehrere möglich)
    if [ -f "docker-compose.yml" ] && grep -q "scandy-app" docker-compose.yml; then
        # Aktuelle Instanz aus .env oder docker-compose.yml extrahieren
        if [ -f ".env" ]; then
            current_instance=$(grep "INSTANCE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "scandy")
        else
            current_instance="scandy"
        fi
        FOUND_INSTANCES+=("$current_instance")
        FOUND_MODES+=("Docker")
        FOUND_TYPES+=("docker")
        log_info "Docker-Installation gefunden: $current_instance"
    fi
    
    # Zusätzliche Docker-Instanzen über docker-compose Projekte finden
    if command -v docker &> /dev/null; then
        while IFS= read -r project; do
            if [[ "$project" == scandy* || "$project" == *scandy* ]]; then
                # Extrahiere Instance-Namen aus Projekt-Namen
                instance_name="${project#scandy}"
                instance_name="${instance_name#-}"
                instance_name="${instance_name:-scandy}"
                
                # Prüfe ob bereits gefunden
                already_found=false
                for found_instance in "${FOUND_INSTANCES[@]}"; do
                    if [ "$found_instance" = "$instance_name" ]; then
                        already_found=true
                        break
                    fi
                done
                
                if [ "$already_found" = false ]; then
                    FOUND_INSTANCES+=("$instance_name")
                    FOUND_MODES+=("Docker (Running)")
                    FOUND_TYPES+=("docker")
                    log_info "Laufende Docker-Installation gefunden: $instance_name"
                fi
            fi
        done < <($DOCKER_CMD ps --format "table {{.Names}}" 2>/dev/null | grep -E "scandy|app|mongodb" | sed 's/.*-\([^-]*\)$/\1/' | sort -u 2>/dev/null || true)
    fi
    
    # Native Installation prüfen (systemd Services)
    if systemctl list-units --type=service 2>/dev/null | grep -q "scandy"; then
        while IFS= read -r service; do
            # Extrahiere Instance-Namen aus Service-Namen
            if [[ "$service" == "scandy.service" ]]; then
                # Standard scandy.service (ohne Instance-Namen)
                instance_name="scandy"
            elif [[ "$service" == scandy-*.service ]]; then
                # Service mit Instance-Namen (scandy-INSTANCE.service)
                instance_name=$(echo "$service" | sed 's/scandy-\(.*\)\.service.*/\1/')
            else
                # Unbekanntes scandy-Service-Format, überspringen
                continue
            fi
            
            if [ -n "$instance_name" ]; then
                FOUND_INSTANCES+=("$instance_name")
                FOUND_MODES+=("Native (systemd)")
                FOUND_TYPES+=("native")
                log_info "Native Installation gefunden: $instance_name"
            fi
        done < <(systemctl list-units --type=service 2>/dev/null | grep "scandy" | awk '{print $1}')
    fi
    
    # LXC Installation prüfen
    if [ -f "/opt/scandy/start_scandy.sh" ] && [ -f "/opt/scandy/app/wsgi.py" ]; then
        # LXC hat normalerweise nur eine Instanz, aber prüfe .env für Namen
        if [ -f "/opt/scandy/.env" ]; then
            lxc_instance=$(grep "INSTANCE_NAME=" /opt/scandy/.env | cut -d'=' -f2 2>/dev/null || echo "scandy")
        else
            lxc_instance="scandy"
        fi
        FOUND_INSTANCES+=("$lxc_instance")
        FOUND_MODES+=("LXC")
        FOUND_TYPES+=("lxc")
        log_info "LXC Installation gefunden: $lxc_instance"
    fi
    
    # Legacy Docker-Installation (.env mit CONTAINER_NAME)
    if [ -f ".env" ] && grep -q "CONTAINER_NAME" .env; then
        legacy_instance=$(grep "CONTAINER_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "scandy")
        legacy_instance="${legacy_instance#scandy-app-}"
        FOUND_INSTANCES+=("$legacy_instance")
        FOUND_MODES+=("Docker (Legacy)")
        FOUND_TYPES+=("docker")
        log_info "Legacy Docker-Installation gefunden: $legacy_instance"
    fi
    
    # Ergebnis
    if [ ${#FOUND_INSTANCES[@]} -eq 0 ]; then
        log_success "Keine bestehende Installation gefunden"
        return 1
    else
        log_success "${#FOUND_INSTANCES[@]} Installation(en) gefunden"
        return 0
    fi
}

# Installationsauswahl für Multi-Instance
show_installation_selection() {
    echo
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                    BESTEHENDE INSTALLATIONEN                   ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${WHITE}Gefundene Installationen:${NC}"
    echo
    
    for i in "${!FOUND_INSTANCES[@]}"; do
        num=$((i + 1))
        echo -e "${CYAN}$num) ${FOUND_INSTANCES[i]}${NC} (${FOUND_MODES[i]})"
        
        # Zeige Status falls verfügbar
        case "${FOUND_TYPES[i]}" in
            docker)
                if command -v docker &> /dev/null; then
                    status=$($DOCKER_CMD ps --filter "name=${FOUND_INSTANCES[i]}" --format "table {{.Status}}" 2>/dev/null | tail -n +2 | head -1)
                    if [ -n "$status" ]; then
                        echo "   Status: $status"
                    fi
                fi
                ;;
            native)
                service_name=$(get_service_name "${FOUND_INSTANCES[i]}")
                status=$(systemctl is-active "$service_name" 2>/dev/null || echo "unknown")
                echo "   Status: $status"
                ;;
        esac
        echo
    done
    
    echo -e "${GREEN}$((${#FOUND_INSTANCES[@]} + 1))) Neue Installation erstellen${NC}"
    echo
    echo -e "${RED}$((${#FOUND_INSTANCES[@]} + 2))) Installation deinstallieren${NC}"
    echo "   🗑️  Ausgewählte Installation entfernen"
    echo
    echo -e "${WHITE}$((${#FOUND_INSTANCES[@]} + 3))) Abbrechen${NC}"
    echo
    
    while true; do
        read -p "Wählen Sie eine Option (1-$((${#FOUND_INSTANCES[@]} + 3))): " choice
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le $((${#FOUND_INSTANCES[@]} + 3)) ]; then
            if [ "$choice" -eq $((${#FOUND_INSTANCES[@]} + 1)) ]; then
                # Neue Installation
                log_info "Neue Installation wird erstellt"
                return 1
            elif [ "$choice" -eq $((${#FOUND_INSTANCES[@]} + 2)) ]; then
                # Deinstallation
                show_uninstall_selection
                exit 0
            elif [ "$choice" -eq $((${#FOUND_INSTANCES[@]} + 3)) ]; then
                # Abbrechen
                log_info "Installation abgebrochen"
                exit 0
            else
                # Bestehende Installation ausgewählt
                selected_index=$((choice - 1))
                EXISTING_INSTALLATION="${FOUND_TYPES[$selected_index]}"
                EXISTING_MODE="${FOUND_MODES[$selected_index]}"
                INSTANCE_NAME="${FOUND_INSTANCES[$selected_index]}"
                log_info "Ausgewählt: ${INSTANCE_NAME} (${EXISTING_MODE})"
                return 0
            fi
        else
            echo -e "${RED}❌ Ungültige Auswahl.${NC}"
            echo -e "${YELLOW}💡 Bitte wählen Sie eine Zahl zwischen 1 und $((${#FOUND_INSTANCES[@]} + 3)).${NC}"
            echo
            sleep 1
        fi
    done
}

# Deinstallations-Auswahl für Multi-Instance
show_uninstall_selection() {
    echo
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    INSTALLATION DEINSTALLIEREN                ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${WHITE}Wählen Sie die Installation zum Deinstallieren:${NC}"
    echo
    
    for i in "${!FOUND_INSTANCES[@]}"; do
        num=$((i + 1))
        echo -e "${RED}$num) ${FOUND_INSTANCES[i]}${NC} (${FOUND_MODES[i]})"
        
        # Zeige Status falls verfügbar
        case "${FOUND_TYPES[i]}" in
            docker)
                if command -v docker &> /dev/null; then
                    status=$($DOCKER_CMD ps --filter "name=${FOUND_INSTANCES[i]}" --format "table {{.Status}}" 2>/dev/null | tail -n +2 | head -1)
                    if [ -n "$status" ]; then
                        echo "   Status: $status"
                    fi
                fi
                ;;
            native)
                service_name=$(get_service_name "${FOUND_INSTANCES[i]}")
                status=$(systemctl is-active "$service_name" 2>/dev/null || echo "unknown")
                echo "   Status: $status"
                ;;
        esac
        echo
    done
    
    echo -e "${WHITE}$((${#FOUND_INSTANCES[@]} + 1))) Abbrechen${NC}"
    echo
    
    while true; do
        read -p "Wählen Sie eine Installation (1-$((${#FOUND_INSTANCES[@]} + 1))): " choice
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le $((${#FOUND_INSTANCES[@]} + 1)) ]; then
            if [ "$choice" -eq $((${#FOUND_INSTANCES[@]} + 1)) ]; then
                # Abbrechen
                log_info "Deinstallation abgebrochen"
                return 1
            else
                # Installation für Deinstallation ausgewählt
                selected_index=$((choice - 1))
                EXISTING_INSTALLATION="${FOUND_TYPES[$selected_index]}"
                EXISTING_MODE="${FOUND_MODES[$selected_index]}"
                INSTANCE_NAME="${FOUND_INSTANCES[$selected_index]}"
                log_info "Gewählt für Deinstallation: ${INSTANCE_NAME} (${EXISTING_MODE})"
                confirm_and_uninstall
                return 0
            fi
        else
            echo -e "${RED}❌ Ungültige Auswahl.${NC}"
            echo -e "${YELLOW}💡 Bitte wählen Sie eine Zahl zwischen 1 und $((${#FOUND_INSTANCES[@]} + 1)).${NC}"
            echo
            sleep 1
        fi
    done
}

# Service-Namen für systemd bestimmen
get_service_name() {
    local instance_name="$1"
    if [ "$instance_name" = "scandy" ]; then
        echo "scandy"
    else
        echo "scandy-$instance_name"
    fi
}

# Duplikate entfernen
remove_duplicates() {
    local unique_instances=()
    local unique_modes=()
    local unique_types=()
    
    for i in "${!FOUND_INSTANCES[@]}"; do
        local instance="${FOUND_INSTANCES[i]}"
        local mode="${FOUND_MODES[i]}"
        local type="${FOUND_TYPES[i]}"
        
        # Prüfe auf Duplikat
        local is_duplicate=false
        for j in "${!unique_instances[@]}"; do
            if [ "${unique_instances[j]}" = "$instance" ] && [ "${unique_types[j]}" = "$type" ]; then
                is_duplicate=true
                break
            fi
        done
        
        if [ "$is_duplicate" = false ]; then
            unique_instances+=("$instance")
            unique_modes+=("$mode")
            unique_types+=("$type")
        fi
    done
    
    FOUND_INSTANCES=("${unique_instances[@]}")
    FOUND_MODES=("${unique_modes[@]}")
    FOUND_TYPES=("${unique_types[@]}")
}

# Wrapper für Kompatibilität
detect_existing_installation() {
    if detect_all_installations; then
        # Duplikate entfernen
        remove_duplicates
        
        if [ ${#FOUND_INSTANCES[@]} -eq 1 ]; then
            # Nur eine Installation gefunden - direkt verwenden
            EXISTING_INSTALLATION="${FOUND_TYPES[0]}"
            EXISTING_MODE="${FOUND_MODES[0]}"
            INSTANCE_NAME="${FOUND_INSTANCES[0]}"
            log_info "Automatisch ausgewählt: ${INSTANCE_NAME} (${EXISTING_MODE})"
            return 0
        else
            # Mehrere Installationen - Benutzer wählen lassen
            show_installation_selection
            return $?
        fi
    else
        return 1
    fi
}

# Interaktives Installationsmenü
show_installation_menu() {
    echo
    echo -e "${WHITE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║                    INSTALLATIONSMODUS WÄHLEN                  ║${NC}"
    echo -e "${WHITE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    # Zeige verfügbare Optionen basierend auf System
    echo -e "${WHITE}Verfügbare Installationsoptionen:${NC}"
    echo
    
    # Option 1: Docker (falls verfügbar)
    if [ "$DOCKER_AVAILABLE" = true ]; then
        echo -e "${GREEN}1) Docker-Installation (empfohlen)${NC}"
        echo "   ✅ Isoliert und sicher"
        echo "   ✅ Einfaches Management"
        echo "   ✅ Automatische Updates"
        echo "   ✅ Mehrere Instanzen möglich"
        echo
    else
        echo -e "${RED}1) Docker-Installation (nicht verfügbar)${NC}"
        echo "   ❌ Docker ist nicht installiert oder läuft nicht"
        echo
    fi
    
    # Option 2: Native Installation
    if [ "$HAS_ROOT" = true ] && [ "$SYSTEMD_AVAILABLE" = true ]; then
        echo -e "${BLUE}2) Native Linux-Installation${NC}"
        echo "   ✅ Beste Performance"
        echo "   ✅ Direkter Systemzugriff"
        echo "   ✅ Für Produktionsumgebungen"
        echo "   ⚠️  Benötigt Root-Rechte"
        echo
    else
        echo -e "${YELLOW}2) Native Linux-Installation (eingeschränkt)${NC}"
        echo "   ⚠️  Benötigt Root-Rechte und systemd"
        echo
    fi
    
    # Option 3: LXC
    echo -e "${PURPLE}3) LXC-Container-Installation${NC}"
    echo "   ✅ Für Container-Umgebungen"
    echo "   ✅ Minimal-Setup"
    echo "   ⚠️  Vereinfachtes Management"
    echo
    
    # Option 4: Automatisch
    echo -e "${CYAN}4) Automatische Erkennung${NC}"
    echo "   🤖 System wählt beste Option"
    echo
    
    echo -e "${WHITE}5) Abbrechen${NC}"
    echo
}

# Update-Angebot für bestehende Installation
offer_update() {
    echo
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                 BESTEHENDE INSTALLATION GEFUNDEN              ║${NC}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${WHITE}Gefunden:${NC} $EXISTING_MODE Installation"
    echo
    echo -e "${WHITE}Optionen:${NC}"
    echo
    echo -e "${GREEN}1) Update durchführen (empfohlen)${NC}"
    echo "   ✅ Sichere Aktualisierung"
    echo "   ✅ Daten bleiben erhalten"
    echo "   ✅ Automatisches Backup"
    echo
    echo -e "${BLUE}2) Neuinstallation (überschreibt alles)${NC}"
    echo "   ⚠️  Alle Daten gehen verloren!"
    echo "   ⚠️  Komplett neue Installation"
    echo
    echo -e "${PURPLE}3) Erweiterte Optionen${NC}"
    echo "   🔧 Port-Änderungen"
    echo "   🔧 Instance-Name ändern"
    echo "   🔧 Installationsmodus wechseln"
    echo
    echo -e "${RED}4) Deinstallation${NC}"
    echo "   🗑️  Installation vollständig entfernen"
    echo "   ⚠️  Alle Daten gehen verloren!"
    echo
    echo -e "${WHITE}5) Abbrechen${NC}"
    echo
    
    while true; do
        read -p "Wählen Sie eine Option (1-5): " choice
        case $choice in
            1)
                log_info "Update wird durchgeführt..."
                UPDATE_ONLY=true
                INSTALL_MODE=$EXISTING_INSTALLATION
                return 0
                ;;
            2)
                echo -e "${RED}⚠️  WARNUNG: Alle Daten gehen verloren!${NC}"
                read -p "Sind Sie sicher? Tippen Sie 'JA' zum Bestätigen: " confirm
                if [ "$confirm" = "JA" ]; then
                    log_warning "Neuinstallation wird durchgeführt..."
                    FORCE_INSTALL=true
                    return 1  # Weiter zur Installationsauswahl
                else
                    log_info "Neuinstallation abgebrochen"
                    continue
                fi
                ;;
            3)
                log_info "Erweiterte Optionen..."
                show_advanced_options
                return 1  # Weiter zur Installationsauswahl
                ;;
            4)
                log_info "Deinstallation wird durchgeführt..."
                confirm_and_uninstall
                exit 0
                ;;
            5)
                log_info "Installation abgebrochen"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Ungültige Auswahl.${NC}"
                echo -e "${YELLOW}💡 Bitte wählen Sie eine Zahl zwischen 1 und 5.${NC}"
                echo
                sleep 1
                ;;
        esac
    done
}

# Deinstallations-Bestätigung und -Ausführung
confirm_and_uninstall() {
    echo
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                       ⚠️  DEINSTALLATION ⚠️                     ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${WHITE}Installation:${NC} ${EXISTING_MODE}"
    echo -e "${WHITE}Instance:${NC} ${INSTANCE_NAME}"
    echo
    echo -e "${RED}⚠️  WARNUNG: Diese Aktion wird ALLE Daten unwiderruflich löschen!${NC}"
    echo
    echo -e "${YELLOW}Was wird entfernt:${NC}"
    case $EXISTING_INSTALLATION in
        docker)
            echo "   🗑️  Docker Container und Images"
            echo "   🗑️  Docker Volumes (Datenbanken)"
            echo "   🗑️  docker-compose.yml und .env"
            echo "   🗑️  Alle Scandy-Daten"
            ;;
        native)
            echo "   🗑️  Systemd Services"
            echo "   🗑️  /opt/scandy Verzeichnis"
            echo "   🗑️  MongoDB Datenbanken"
            echo "   🗑️  Nginx Konfiguration"
            echo "   🗑️  Alle Scandy-Daten"
            ;;
        lxc)
            echo "   🗑️  /opt/scandy Verzeichnis"
            echo "   🗑️  Python Virtual Environment"
            echo "   🗑️  Alle Scandy-Daten"
            ;;
    esac
    echo
    echo -e "${GREEN}Optionen:${NC}"
    echo
    echo -e "${CYAN}1) Backup erstellen und dann deinstallieren${NC}"
    echo "   ✅ Sichere Deinstallation"
    echo "   ✅ Daten können später wiederhergestellt werden"
    echo
    echo -e "${RED}2) Sofort deinstallieren (OHNE Backup)${NC}"
    echo "   ⚠️  Alle Daten gehen unwiderruflich verloren!"
    echo
    echo -e "${WHITE}3) Abbrechen${NC}"
    echo
    
    while true; do
        read -p "Wählen Sie eine Option (1-3): " choice
        case $choice in
            1)
                log_info "Erstelle Backup vor Deinstallation..."
                if create_backup_before_uninstall; then
                    log_success "Backup erfolgreich erstellt"
                    confirm_final_uninstall
                else
                    log_error "Backup fehlgeschlagen - Deinstallation abgebrochen"
                    return 1
                fi
                break
                ;;
            2)
                confirm_final_uninstall
                break
                ;;
            3)
                log_info "Deinstallation abgebrochen"
                return 1
                ;;
            *)
                echo -e "${RED}❌ Ungültige Auswahl.${NC}"
                echo -e "${YELLOW}💡 Bitte wählen Sie eine Zahl zwischen 1 und 3.${NC}"
                echo
                sleep 1
                ;;
        esac
    done
}

# Finale Bestätigung für Deinstallation
confirm_final_uninstall() {
    echo
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                     FINALE BESTÄTIGUNG                        ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${RED}⚠️  LETZTE WARNUNG: Diese Aktion kann NICHT rückgängig gemacht werden!${NC}"
    echo
    echo -e "${WHITE}Um fortzufahren, tippen Sie exakt:${NC} ${RED}DEINSTALLIEREN${NC}"
    echo -e "${WHITE}Um abzubrechen, drücken Sie einfach Enter.${NC}"
    echo
    read -p "Eingabe: " final_confirm
    
    if [ "$final_confirm" = "DEINSTALLIEREN" ]; then
        log_warning "Deinstallation wird durchgeführt..."
        perform_uninstall
    else
        log_info "Deinstallation abgebrochen"
        return 1
    fi
}

# Backup vor Deinstallation erstellen
create_backup_before_uninstall() {
    local backup_name="scandy_backup_before_uninstall_$(date +%Y%m%d_%H%M%S)"
    
    case $EXISTING_INSTALLATION in
        docker)
            log_step "Erstelle Docker-Backup..."
            if command -v docker &> /dev/null; then
                # MongoDB Backup
                $DOCKER_CMD exec "scandy-mongodb-${INSTANCE_NAME}" mongodump --out /tmp/backup --quiet 2>/dev/null
                $DOCKER_CMD cp "scandy-mongodb-${INSTANCE_NAME}:/tmp/backup" "./${backup_name}_mongodb"
                
                # Dateien kopieren
                mkdir -p "${backup_name}_files"
                cp -r uploads/ "${backup_name}_files/" 2>/dev/null || true
                cp .env "${backup_name}_files/" 2>/dev/null || true
                cp docker-compose.yml "${backup_name}_files/" 2>/dev/null || true
                
                # ZIP erstellen
                zip -r "${backup_name}.zip" "${backup_name}_"* >/dev/null 2>&1
                rm -rf "${backup_name}_"*
                
                log_success "Backup erstellt: ${backup_name}.zip"
                return 0
            else
                log_error "Docker nicht verfügbar für Backup"
                return 1
            fi
            ;;
        native)
            log_step "Erstelle Native-Backup..."
            # MongoDB Backup
            mongodump --out "/tmp/${backup_name}_mongodb" --quiet 2>/dev/null || true
            
            # Dateien kopieren
            mkdir -p "${backup_name}_files"
            cp -r /opt/scandy/uploads/ "${backup_name}_files/" 2>/dev/null || true
            cp /opt/scandy/.env "${backup_name}_files/" 2>/dev/null || true
            cp -r "/tmp/${backup_name}_mongodb" "${backup_name}_files/" 2>/dev/null || true
            
            # ZIP erstellen
            zip -r "${backup_name}.zip" "${backup_name}_files" >/dev/null 2>&1
            rm -rf "${backup_name}_files" "/tmp/${backup_name}_mongodb"
            
            log_success "Backup erstellt: ${backup_name}.zip"
            return 0
            ;;
        lxc)
            log_step "Erstelle LXC-Backup..."
            # Einfaches Datei-Backup
            mkdir -p "${backup_name}_files"
            cp -r /opt/scandy/uploads/ "${backup_name}_files/" 2>/dev/null || true
            cp /opt/scandy/.env "${backup_name}_files/" 2>/dev/null || true
            
            # ZIP erstellen
            zip -r "${backup_name}.zip" "${backup_name}_files" >/dev/null 2>&1
            rm -rf "${backup_name}_files"
            
            log_success "Backup erstellt: ${backup_name}.zip"
            return 0
            ;;
    esac
}

# Deinstallation durchführen
perform_uninstall() {
    case $EXISTING_INSTALLATION in
        docker)
            uninstall_docker
            ;;
        native)
            uninstall_native
            ;;
        lxc)
            uninstall_lxc
            ;;
    esac
    
    log_success "Deinstallation von ${INSTANCE_NAME} (${EXISTING_MODE}) abgeschlossen!"
}

# Docker-Installation deinstallieren
uninstall_docker() {
    log_step "Entferne Docker-Installation..."
    
    # Container stoppen und entfernen
    if command -v docker &> /dev/null; then
        log_info "Stoppe und entferne Container..."
        $DOCKER_CMD compose down -v 2>/dev/null || true
        
        # Images entfernen
        log_info "Entferne Docker Images..."
        $DOCKER_CMD image rm "scandy2-scandy-app" 2>/dev/null || true
        $DOCKER_CMD image rm "mongo:7" 2>/dev/null || true
        $DOCKER_CMD image rm "mongo-express:latest" 2>/dev/null || true
        
        # Volumes entfernen
        log_info "Entferne Docker Volumes..."
        $DOCKER_CMD volume rm "scandy2_mongodb_data" 2>/dev/null || true
        $DOCKER_CMD volume rm "scandy2_uploads" 2>/dev/null || true
    fi
    
    # Dateien entfernen
    log_info "Entferne Konfigurationsdateien..."
    rm -f docker-compose.yml
    rm -f .env
    rm -f manage_scandy.sh
    rm -rf uploads/
    
    log_success "Docker-Installation entfernt"
}

# Native Installation deinstallieren
uninstall_native() {
    log_step "Entferne Native Installation..."
    
    # Service stoppen und deaktivieren
    service_name=$(get_service_name "$INSTANCE_NAME")
    log_info "Stoppe Service: $service_name"
    systemctl stop "$service_name" 2>/dev/null || true
    systemctl disable "$service_name" 2>/dev/null || true
    
    # Service-Datei entfernen
    log_info "Entferne Systemd Service..."
    rm -f "/etc/systemd/system/${service_name}.service"
    systemctl daemon-reload
    
    # MongoDB Datenbanken entfernen
    log_info "Entferne MongoDB Datenbanken..."
    if command -v mongosh &> /dev/null; then
        mongosh --eval "db.dropDatabase()" scandy 2>/dev/null || true
        mongosh --eval "db.dropDatabase()" scandy_tickets 2>/dev/null || true
    fi
    
    # Scandy-Verzeichnis entfernen
    log_info "Entferne /opt/scandy..."
    rm -rf /opt/scandy
    
    # Scandy-Benutzer entfernen
    log_info "Entferne scandy-Benutzer..."
    userdel scandy 2>/dev/null || true
    
    # Nginx-Konfiguration entfernen
    log_info "Entferne Nginx-Konfiguration..."
    rm -f "/etc/nginx/sites-available/scandy-${INSTANCE_NAME}"
    rm -f "/etc/nginx/sites-enabled/scandy-${INSTANCE_NAME}"
    systemctl reload nginx 2>/dev/null || true
    
    log_success "Native Installation entfernt"
}

# LXC Installation deinstallieren
uninstall_lxc() {
    log_step "Entferne LXC Installation..."
    
    # Prozesse stoppen
    log_info "Stoppe Scandy-Prozesse..."
    pkill -f "gunicorn.*scandy" 2>/dev/null || true
    
    # Verzeichnis entfernen
    log_info "Entferne /opt/scandy..."
    rm -rf /opt/scandy
    
    log_success "LXC Installation entfernt"
}

# Erweiterte Optionen
show_advanced_options() {
    echo
    echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                     ERWEITERTE OPTIONEN                       ║${NC}"
    echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    
    # Aktuelle Konfiguration anzeigen
    if [ -f ".env" ]; then
        echo -e "${WHITE}Aktuelle Konfiguration:${NC}"
        CURRENT_INSTANCE=$(grep "INSTANCE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "unbekannt")
        CURRENT_WEB_PORT=$(grep "WEB_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "unbekannt")
        CURRENT_MONGO_PORT=$(grep "MONGODB_PORT=" .env | cut -d'=' -f2 2>/dev/null || echo "unbekannt")
        
        echo "   Instance-Name: $CURRENT_INSTANCE"
        echo "   Web-Port: $CURRENT_WEB_PORT"
        echo "   MongoDB-Port: $CURRENT_MONGO_PORT"
        echo "   Installationsmodus: $EXISTING_MODE"
        echo
    fi
    
    echo -e "${WHITE}Möchten Sie:${NC}"
    echo
    echo "1) Instance-Name ändern"
    echo "2) Ports ändern"
    echo "3) Installationsmodus wechseln"
    echo "4) Zurück zum Hauptmenü"
    echo
    
    read -p "Wählen Sie eine Option (1-4): " adv_choice
    case $adv_choice in
        1)
            read -p "Neuer Instance-Name (aktuell: $CURRENT_INSTANCE): " new_name
            if [ -n "$new_name" ]; then
                INSTANCE_NAME="$new_name"
                log_info "Instance-Name geändert zu: $INSTANCE_NAME"
            fi
            ;;
        2)
            read -p "Neuer Web-Port (aktuell: $CURRENT_WEB_PORT): " new_web_port
            read -p "Neuer MongoDB-Port (aktuell: $CURRENT_MONGO_PORT): " new_mongo_port
            if [ -n "$new_web_port" ]; then
                WEB_PORT="$new_web_port"
            fi
            if [ -n "$new_mongo_port" ]; then
                MONGODB_PORT="$new_mongo_port"
            fi
            log_info "Ports aktualisiert"
            ;;
        3)
            log_info "Installationsmodus kann bei Neuinstallation gewählt werden"
            FORCE_INSTALL=true
            ;;
        4)
            return
            ;;
    esac
}

# Interaktive Installationsauswahl
interactive_installation_mode() {
    # Prüfe zuerst auf bestehende Installation
    if detect_existing_installation && [ "$FORCE_INSTALL" = false ]; then
        if offer_update; then
            # Update gewählt
            return 0
        fi
        # Neuinstallation oder erweiterte Optionen gewählt
    fi
    
    # Zeige Installationsmenü
    while true; do
        show_installation_menu
        
        read -p "Wählen Sie eine Option (1-5): " choice
        case $choice in
            1)
                if [ "$DOCKER_AVAILABLE" = true ]; then
                    INSTALL_MODE="docker"
                    log_success "Docker-Installation gewählt"
                    break
                else
                    echo -e "${RED}❌ Docker ist nicht verfügbar oder läuft nicht.${NC}"
                    echo -e "${YELLOW}💡 Alternativen: Wählen Sie Option 3 (LXC) oder 4 (Automatisch)${NC}"
                    echo
                    sleep 2
                fi
                ;;
            2)
                if [ "$HAS_ROOT" = true ] && [ "$SYSTEMD_AVAILABLE" = true ]; then
                    INSTALL_MODE="native"
                    log_success "Native Installation gewählt"
                    break
                else
                    echo -e "${RED}❌ Native Installation nicht möglich.${NC}"
                    echo -e "${YELLOW}💡 Grund: Root-Rechte oder systemd fehlen${NC}"
                    echo -e "${YELLOW}💡 Alternativen: Wählen Sie Option 1 (Docker) oder 3 (LXC)${NC}"
                    echo
                    sleep 2
                fi
                ;;
            3)
                INSTALL_MODE="lxc"
                log_success "LXC-Installation gewählt"
                break
                ;;
            4)
                log_info "Automatische Erkennung..."
                detect_best_install_mode_auto
                break
                ;;
            5)
                log_info "Installation abgebrochen"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Ungültige Auswahl.${NC}"
                echo -e "${YELLOW}💡 Bitte wählen Sie eine Zahl zwischen 1 und 5.${NC}"
                echo
                sleep 1
                ;;
        esac
    done
}

# Automatische Erkennung (alte Funktion, umbenannt)
detect_best_install_mode_auto() {
    log_step "Erkenne beste Installationsoption..."
    
    # Prüfe System-Zustand
    check_system_compatibility
    
    # Neue Installation: Beste Option wählen
    if [ "$DOCKER_AVAILABLE" = true ] && [ "$IN_LXC" = false ]; then
        log_success "Docker verfügbar → Docker-Installation empfohlen"
        INSTALL_MODE="docker"
    elif [ "$IN_LXC" = true ] || [ "$DOCKER_AVAILABLE" = false ]; then
        if [ "$HAS_ROOT" = true ] && [ "$SYSTEMD_AVAILABLE" = true ]; then
            log_info "LXC-Umgebung oder Docker nicht verfügbar → Native Installation"
            INSTALL_MODE="native"
        else
            log_warning "Eingeschränkte Umgebung erkannt → LXC-Modus"
            INSTALL_MODE="lxc"
        fi
    else
        log_info "Standard-Fallback → Docker-Installation"
        INSTALL_MODE="docker"
    fi
    
    log_success "Gewählter Installationsmodus: $INSTALL_MODE"
}

# Port-Verfügbarkeit prüfen
check_port_availability() {
    local port=$1
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        return 1  # Port ist belegt
    else
        return 0  # Port ist frei
    fi
}

# Automatische Port-Berechnung bei Konflikten
resolve_port_conflicts() {
    log_step "Prüfe Port-Verfügbarkeit..."
    
    # Web-Port prüfen
    if ! check_port_availability $WEB_PORT; then
        log_warning "Port $WEB_PORT ist belegt, suche alternative..."
        for ((i=5001; i<=5099; i++)); do
            if check_port_availability $i; then
                WEB_PORT=$i
                log_success "Alternativer Web-Port: $WEB_PORT"
                break
            fi
        done
    fi
    
    # MongoDB-Port prüfen
    if ! check_port_availability $MONGODB_PORT; then
        log_warning "Port $MONGODB_PORT ist belegt, suche alternative..."
        for ((i=27018; i<=27099; i++)); do
            if check_port_availability $i; then
                MONGODB_PORT=$i
                log_success "Alternativer MongoDB-Port: $MONGODB_PORT"
                break
            fi
        done
    fi
    
    # Mongo Express-Port prüfen
    if ! check_port_availability $MONGO_EXPRESS_PORT; then
        log_warning "Port $MONGO_EXPRESS_PORT ist belegt, suche alternative..."
        for ((i=8082; i<=8199; i++)); do
            if check_port_availability $i; then
                MONGO_EXPRESS_PORT=$i
                log_success "Alternativer Mongo Express-Port: $MONGO_EXPRESS_PORT"
                break
            fi
        done
    fi
}

# Backup erstellen
create_backup() {
    if [ "$CREATE_BACKUP" = true ]; then
        log_step "Erstelle Backup vor Installation..."
        
        BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Bestehende Konfiguration sichern
        [ -f ".env" ] && cp .env "$BACKUP_DIR/"
        [ -f "docker-compose.yml" ] && cp docker-compose.yml "$BACKUP_DIR/"
        [ -d "data" ] && cp -r data "$BACKUP_DIR/"
        [ -d "backups" ] && cp -r backups "$BACKUP_DIR/"
        
        log_success "Backup erstellt in: $BACKUP_DIR"
    fi
}

# .env Datei erstellen
create_env_file() {
    log_step "Erstelle .env-Konfiguration..."
    
    # Sichere Passwörter generieren
    MONGO_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
    
    # MongoDB-URI je nach Installationsmodus setzen
    if [ "$INSTALL_MODE" = "docker" ]; then
        # Docker: Verwende Container-Namen
        MONGODB_URI="mongodb://admin:${MONGO_PASSWORD}@scandy-mongodb-${INSTANCE_NAME}:27017/scandy?authSource=admin"
    else
        # Native/LXC: Verwende localhost
        MONGODB_URI="mongodb://admin:${MONGO_PASSWORD}@localhost:${MONGODB_PORT}/scandy?authSource=admin"
    fi
    
    cat > .env << EOF
# Scandy Universal Configuration
# Generated: $(date)

# Instance Configuration
INSTANCE_NAME=$INSTANCE_NAME
DEPARTMENT=$INSTANCE_NAME
CONTAINER_NAME=$INSTANCE_NAME

# Port Configuration
WEB_PORT=$WEB_PORT
MONGODB_PORT=$MONGODB_PORT
MONGO_EXPRESS_PORT=$MONGO_EXPRESS_PORT

# Database Configuration
MONGODB_URI=$MONGODB_URI
MONGODB_DB=scandy
MONGO_INITDB_ROOT_PASSWORD=$MONGO_PASSWORD
MONGO_INITDB_DATABASE=scandy

# Security
SECRET_KEY=$SECRET_KEY

# System Names
SYSTEM_NAME=Scandy - $INSTANCE_NAME
TICKET_SYSTEM_NAME=Ticket-System
TOOL_SYSTEM_NAME=Werkzeug-Verwaltung
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter-Verwaltung

# Features
ENABLE_TICKET_SYSTEM=true
ENABLE_JOB_BOARD=false
ENABLE_WEEKLY_REPORTS=true

# Production Settings
FLASK_ENV=$([ "$PRODUCTION_MODE" = true ] && echo "production" || echo "development")
SESSION_COOKIE_SECURE=$([ "$ENABLE_SSL" = true ] && echo "true" || echo "false")
REMEMBER_COOKIE_SECURE=$([ "$ENABLE_SSL" = true ] && echo "true" || echo "false")

# Domain Configuration
$([ -n "$DOMAIN" ] && echo "DOMAIN=$DOMAIN" || echo "# DOMAIN=")

# Email Configuration (anpassen nach Bedarf)
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-app-password
# MAIL_DEFAULT_SENDER=your-email@gmail.com
EOF

    log_success ".env-Datei erstellt"
}

# SSL-Zertifikate einrichten
setup_ssl_certificates() {
    log_step "Richte SSL-Zertifikate ein..."
    
    # SSL-Verzeichnis erstellen
    mkdir -p ssl
    
    # Selbst-signiertes Zertifikat erstellen
    if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
        log_info "Erstelle selbst-signiertes SSL-Zertifikat..."
        openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=DE/ST=NRW/L=Dortmund/O=Scandy/CN=localhost"
        log_success "SSL-Zertifikat erstellt"
    else
        log_info "SSL-Zertifikate bereits vorhanden"
    fi
}

# Docker-Installation
install_docker() {
    log_step "Starte Docker-Installation..."
    
    # Prüfe Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker ist nicht installiert!"
        log_info "Installiere Docker mit: curl -fsSL https://get.docker.com | sh"
        exit 1
    fi
    
    if ! $DOCKER_CMD info &> /dev/null; then
        log_error "Docker läuft nicht!"
        log_info "Starte Docker mit: sudo systemctl start docker"
        exit 1
    fi
    
    log_success "Docker ist verfügbar"
    
    # docker-compose.yml erstellen
    create_docker_compose
    
    # Container bauen und starten
    log_step "Baue und starte Container..."
    $DOCKER_CMD compose down || true
    $DOCKER_CMD compose build --no-cache
    $DOCKER_CMD compose up -d
    
    # Warte auf Services
    wait_for_docker_services
    
    log_success "Docker-Installation abgeschlossen!"
}

# docker-compose.yml erstellen
create_docker_compose() {
    log_step "Erstelle docker-compose.yml..."
    
    if [ "$ENABLE_HTTPS" = true ]; then
        log_info "HTTPS-Modus aktiviert - erstelle SSL-Zertifikate..."
        setup_ssl_certificates
    fi
    
    if [ "$ENABLE_HTTPS" = true ]; then
        create_https_docker_compose
    else
        create_http_docker_compose
    fi
}

# HTTP docker-compose.yml erstellen
create_http_docker_compose() {
    cat > docker-compose.yml << EOF
services:
  scandy-mongodb-${INSTANCE_NAME}:
    image: mongo:7
    container_name: scandy-mongodb-${INSTANCE_NAME}
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      MONGO_INITDB_DATABASE: \${MONGO_INITDB_DATABASE}
    ports:
      - "${MONGODB_PORT}:27017"
    volumes:
      - mongodb_data_${INSTANCE_NAME}:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - scandy-network-${INSTANCE_NAME}
    command: mongod --bind_ip_all
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 10s
      retries: 15
      start_period: 30s
    env_file:
      - .env

  scandy-mongo-express-${INSTANCE_NAME}:
    image: mongo-express:1.0.0
    container_name: scandy-mongo-express-${INSTANCE_NAME}
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      ME_CONFIG_MONGODB_URL: mongodb://admin:\${MONGO_INITDB_ROOT_PASSWORD}@scandy-mongodb-${INSTANCE_NAME}:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
    ports:
      - "${MONGO_EXPRESS_PORT}:8081"
    depends_on:
      scandy-mongodb-${INSTANCE_NAME}:
        condition: service_healthy
    networks:
      - scandy-network-${INSTANCE_NAME}
    env_file:
      - .env

  scandy-app-${INSTANCE_NAME}:
    build:
      context: .
      dockerfile: Dockerfile
    image: scandy-local:dev-${INSTANCE_NAME}
    container_name: scandy-app-${INSTANCE_NAME}
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=\${MONGODB_URI}
      - MONGODB_DB=\${MONGODB_DB}
      - FLASK_ENV=\${FLASK_ENV}
      - SECRET_KEY=\${SECRET_KEY}
      - SYSTEM_NAME=\${SYSTEM_NAME}
      - TICKET_SYSTEM_NAME=\${TICKET_SYSTEM_NAME}
      - TOOL_SYSTEM_NAME=\${TOOL_SYSTEM_NAME}
      - CONSUMABLE_SYSTEM_NAME=\${CONSUMABLE_SYSTEM_NAME}
      - CONTAINER_NAME=\${CONTAINER_NAME}
      - TZ=Europe/Berlin
      - SESSION_COOKIE_SECURE=\${SESSION_COOKIE_SECURE}
      - REMEMBER_COOKIE_SECURE=\${REMEMBER_COOKIE_SECURE}
    ports:
      - "${WEB_PORT}:5000"
    volumes:
      - ./app:/app/app
      - app_uploads_${INSTANCE_NAME}:/app/app/uploads
      - app_backups_${INSTANCE_NAME}:/app/app/backups
      - app_logs_${INSTANCE_NAME}:/app/app/logs
      - app_sessions_${INSTANCE_NAME}:/app/app/flask_session
    depends_on:
      scandy-mongodb-${INSTANCE_NAME}:
        condition: service_healthy
    networks:
      - scandy-network-${INSTANCE_NAME}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    env_file:
      - .env

volumes:
  mongodb_data_${INSTANCE_NAME}:
    driver: local
  app_uploads_${INSTANCE_NAME}:
    driver: local
  app_backups_${INSTANCE_NAME}:
    driver: local
  app_logs_${INSTANCE_NAME}:
    driver: local
  app_sessions_${INSTANCE_NAME}:
    driver: local

networks:
  scandy-network-${INSTANCE_NAME}:
    driver: bridge
EOF
    
    log_success "HTTP docker-compose.yml erstellt"
}

# HTTPS docker-compose.yml erstellen
create_https_docker_compose() {
    cat > docker-compose.yml << EOF
services:
  scandy-mongodb-${INSTANCE_NAME}:
    image: mongo:7
    container_name: scandy-mongodb-${INSTANCE_NAME}
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      MONGO_INITDB_DATABASE: \${MONGO_INITDB_DATABASE}
    ports:
      - "${MONGODB_PORT}:27017"
    volumes:
      - mongodb_data_${INSTANCE_NAME}:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - scandy-network-${INSTANCE_NAME}
    command: mongod --bind_ip_all
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 10s
      retries: 15
      start_period: 30s
    env_file:
      - .env

  scandy-mongo-express-${INSTANCE_NAME}:
    image: mongo-express:1.0.0
    container_name: scandy-mongo-express-${INSTANCE_NAME}
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      ME_CONFIG_MONGODB_URL: mongodb://admin:\${MONGO_INITDB_ROOT_PASSWORD}@scandy-mongodb-${INSTANCE_NAME}:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
    ports:
      - "${MONGO_EXPRESS_PORT}:8081"
    depends_on:
      scandy-mongodb-${INSTANCE_NAME}:
        condition: service_healthy
    networks:
      - scandy-network-${INSTANCE_NAME}
    env_file:
      - .env

  scandy-app-${INSTANCE_NAME}:
    build:
      context: .
      dockerfile: Dockerfile.https
    image: scandy-local:dev-${INSTANCE_NAME}
    container_name: scandy-app-${INSTANCE_NAME}
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=\${MONGODB_URI}
      - MONGODB_DB=\${MONGODB_DB}
      - FLASK_ENV=\${FLASK_ENV}
      - SECRET_KEY=\${SECRET_KEY}
      - SYSTEM_NAME=\${SYSTEM_NAME}
      - TICKET_SYSTEM_NAME=\${TICKET_SYSTEM_NAME}
      - TOOL_SYSTEM_NAME=\${TOOL_SYSTEM_NAME}
      - CONSUMABLE_SYSTEM_NAME=\${CONSUMABLE_SYSTEM_NAME}
      - CONTAINER_NAME=\${CONTAINER_NAME}
      - TZ=Europe/Berlin
      - SESSION_COOKIE_SECURE=True
      - REMEMBER_COOKIE_SECURE=True
      - FORCE_HTTPS=True
      - SSL_CERT_PATH=/app/ssl/cert.pem
      - SSL_KEY_PATH=/app/ssl/key.pem
    ports:
      - "${WEB_PORT}:5000"
    volumes:
      - ./app:/app/app
      - app_uploads_${INSTANCE_NAME}:/app/app/uploads
      - app_backups_${INSTANCE_NAME}:/app/app/backups
      - app_logs_${INSTANCE_NAME}:/app/app/logs
      - app_sessions_${INSTANCE_NAME}:/app/app/flask_session
      - ./ssl:/app/ssl
    depends_on:
      scandy-mongodb-${INSTANCE_NAME}:
        condition: service_healthy
    networks:
      - scandy-network-${INSTANCE_NAME}
    healthcheck:
      test: ["CMD", "curl", "-k", "-f", "https://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    env_file:
      - .env

volumes:
  mongodb_data_${INSTANCE_NAME}:
    driver: local
  app_uploads_${INSTANCE_NAME}:
    driver: local
  app_backups_${INSTANCE_NAME}:
    driver: local
  app_logs_${INSTANCE_NAME}:
    driver: local
  app_sessions_${INSTANCE_NAME}:
    driver: local

networks:
  scandy-network-${INSTANCE_NAME}:
    driver: bridge
EOF
    
    log_success "HTTPS docker-compose.yml erstellt"
}

# Warte auf Docker-Services
wait_for_docker_services() {
    log_step "Warte auf Services..."
    
    # Warte auf MongoDB
    log_info "Warte auf MongoDB..."
    for i in {1..30}; do
        if $DOCKER_CMD exec scandy-mongodb-${INSTANCE_NAME} mongosh --eval "db.adminCommand('ping')" &>/dev/null; then
            log_success "MongoDB ist bereit"
            break
        fi
        sleep 2
    done
    
    # Warte auf Web-App
    log_info "Warte auf Web-App..."
    for i in {1..30}; do
        if curl -f http://localhost:${WEB_PORT}/health &>/dev/null; then
            log_success "Web-App ist bereit"
            break
        fi
        sleep 2
    done
}

# Native Linux-Installation
install_native() {
    log_step "Starte native Linux-Installation..."
    
    # Root-Rechte prüfen
    if [[ $EUID -ne 0 ]] && [ "$FORCE_INSTALL" = false ]; then
        log_error "Native Installation benötigt Root-Rechte!"
        log_info "Führen Sie das Skript mit 'sudo' aus oder verwenden Sie --force"
        exit 1
    fi
    
    # System-Pakete installieren
    install_system_packages
    
    # MongoDB installieren
    install_mongodb_native
    
    # Python-Umgebung einrichten
    setup_python_environment
    
    # SSL-Setup für lokale Installation
    if [ "$LOCAL_SSL" = true ]; then
        setup_local_ssl
    fi
    
    # Nginx konfigurieren
    configure_nginx
    
    # Systemd-Services erstellen
    create_systemd_services
    
    # Services starten
    start_native_services
    
    log_success "Native Installation abgeschlossen!"
}

# System-Pakete installieren
install_system_packages() {
    log_step "Installiere System-Pakete..."
    
    # Package Manager erkennen
    if command -v apt &> /dev/null; then
        PKG_MANAGER="apt"
        UPDATE_CMD="apt update"
        INSTALL_CMD="apt install -y"
    elif command -v yum &> /dev/null; then
        PKG_MANAGER="yum"
        UPDATE_CMD="yum update -y"
        INSTALL_CMD="yum install -y"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
        UPDATE_CMD="dnf update -y"
        INSTALL_CMD="dnf install -y"
    else
        log_error "Unbekannter Package Manager!"
        exit 1
    fi
    
    log_info "Verwende Package Manager: $PKG_MANAGER"
    
    # System aktualisieren
    $UPDATE_CMD
    
    # Basis-Pakete installieren
    $INSTALL_CMD python3 python3-pip python3-venv git nginx curl gnupg lsb-release openssl
    
    log_success "System-Pakete installiert"
}

# MongoDB native installieren
install_mongodb_native() {
    log_step "Installiere MongoDB..."
    
    # Prüfe ob bereits installiert
    if command -v mongod &> /dev/null; then
        log_info "MongoDB ist bereits installiert"
        return
    fi
    
    if [ "$PKG_MANAGER" = "apt" ]; then
        # Ubuntu/Debian
        curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
        echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list
        apt update
        apt install -y mongodb-org
    else
        # RedHat/CentOS/Fedora
        cat > /etc/yum.repos.d/mongodb-org-7.0.repo << EOF
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://pgp.mongodb.com/server-7.0.asc
EOF
        $INSTALL_CMD mongodb-org
    fi
    
    # MongoDB konfigurieren
    systemctl enable mongod
    systemctl start mongod
    
    log_success "MongoDB installiert und gestartet"
}

# Python-Umgebung einrichten
setup_python_environment() {
    log_step "Richte Python-Umgebung ein..."
    
    # Benutzer erstellen (falls nicht vorhanden)
    if ! id "scandy" &>/dev/null; then
        useradd -r -s /bin/bash -d /opt/scandy scandy
        log_info "Benutzer 'scandy' erstellt"
    else
        log_info "Benutzer 'scandy' existiert bereits"
    fi
    
    # Verzeichnisse erstellen
    mkdir -p /opt/scandy
    chown scandy:scandy /opt/scandy
    
    # Code kopieren (aber bestehende venv ausschließen)
    if [ "$PWD" != "/opt/scandy" ]; then
        log_info "Kopiere Code nach /opt/scandy..."
        
        # Verwende rsync falls verfügbar, sonst cp
        if command -v rsync &> /dev/null; then
            rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' . /opt/scandy/
        else
            # Fallback: cp mit manueller Ausnahme-Behandlung
            cp -r . /opt/scandy/
            # Entferne problematische Verzeichnisse
            rm -rf /opt/scandy/venv /opt/scandy/__pycache__
            find /opt/scandy -name "*.pyc" -delete 2>/dev/null || true
        fi
        
        chown -R scandy:scandy /opt/scandy
    fi
    
    cd /opt/scandy
    
    # Bestehende venv prüfen und löschen falls nötig
    if [ -d "venv" ]; then
        log_warning "Bestehende venv gefunden, entferne sie..."
        rm -rf venv
    fi
    
    # Virtual Environment erstellen
    log_info "Erstelle neue Python Virtual Environment..."
    sudo -u scandy python3 -m venv venv
    
    # pip upgrade (mit besserem Error-Handling)
    log_info "Aktualisiere pip..."
    if ! sudo -u scandy venv/bin/pip install --upgrade pip --no-warn-script-location; then
        log_warning "pip-Upgrade fehlgeschlagen, verwende bestehende Version"
    fi
    
    # Requirements installieren
    log_info "Installiere Python-Abhängigkeiten..."
    sudo -u scandy venv/bin/pip install -r requirements.txt --no-warn-script-location
    
    log_success "Python-Umgebung eingerichtet"
}

# Nginx konfigurieren
configure_nginx() {
    if [ -n "$DOMAIN" ]; then
        log_step "Konfiguriere Nginx für Domain: $DOMAIN"
        
        cat > /etc/nginx/sites-available/scandy-${INSTANCE_NAME} << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        proxy_pass http://localhost:${WEB_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
        
        ln -sf /etc/nginx/sites-available/scandy-${INSTANCE_NAME} /etc/nginx/sites-enabled/
        
        # SSL konfigurieren
        if [ "$ENABLE_SSL" = true ]; then
            if command -v certbot &> /dev/null; then
                log_step "Konfiguriere SSL mit Let's Encrypt..."
                certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
            else
                log_warning "Certbot nicht installiert - SSL manuell konfigurieren"
            fi
        fi
        
        systemctl reload nginx
        log_success "Nginx konfiguriert"
    fi
}

# Systemd-Services erstellen
create_systemd_services() {
    log_step "Erstelle Systemd-Services..."
    
    # Service-Namen bestimmen
    service_name=$(get_service_name "$INSTANCE_NAME")
    
    # Scandy Service
    cat > /etc/systemd/system/${service_name}.service << EOF
[Unit]
Description=Scandy Application - ${INSTANCE_NAME}
After=network.target mongod.service

[Service]
Type=exec
User=scandy
Group=scandy
WorkingDirectory=/opt/scandy
Environment=PATH=/opt/scandy/venv/bin
ExecStart=/opt/scandy/venv/bin/gunicorn --bind 0.0.0.0:${WEB_PORT} --workers 4 app.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    service_name=$(get_service_name "$INSTANCE_NAME")
    systemctl enable "$service_name"
    
    log_success "Systemd-Services erstellt"
}

# Native Services starten
start_native_services() {
    log_step "Starte Services..."
    
    systemctl start mongod
    service_name=$(get_service_name "$INSTANCE_NAME")
    systemctl start "$service_name"
    systemctl start nginx
    
    # Warte auf Services
    for i in {1..30}; do
        if curl -f http://localhost:${WEB_PORT}/health &>/dev/null; then
            log_success "Alle Services sind bereit"
            break
        fi
        sleep 2
    done
}

# LXC-Installation
install_lxc() {
    log_step "Starte LXC-Installation..."
    
    # LXC-spezifische Installation (vereinfachte native Installation)
    install_system_packages
    install_mongodb_native
    setup_python_environment
    
    # Einfache Service-Konfiguration (ohne systemd)
    cat > /opt/scandy/start_scandy.sh << 'EOF'
#!/bin/bash
cd /opt/scandy
source venv/bin/activate
export FLASK_ENV=production
python -m gunicorn --bind 0.0.0.0:5000 --workers 2 app.wsgi:application
EOF
    
    chmod +x /opt/scandy/start_scandy.sh
    chown scandy:scandy /opt/scandy/start_scandy.sh
    
    log_success "LXC-Installation abgeschlossen!"
}

# Update-Funktion
update_installation() {
    log_step "Führe Update durch..."
    
    # Backup erstellen
    if [ "$CREATE_BACKUP" = true ]; then
        create_backup
    fi
    
    case $INSTALL_MODE in
        docker)
            log_info "Docker-Update..."
            $DOCKER_CMD compose down
            
            # Images entfernen aber Volumes behalten
            log_info "Entferne alte Images..."
            $DOCKER_CMD image rm scandy-local:dev-scandy 2>/dev/null || true
            
            # Requirements explizit neu installieren
            log_info "Baue Images komplett neu..."
            $DOCKER_CMD compose build --no-cache --build-arg REBUILD_REQUIREMENTS=true
            
            # Container starten
            $DOCKER_CMD compose up -d
            wait_for_docker_services
            ;;
        native)
            log_info "Native Update..."
            
            # Verzeichnisse
            TARGET_DIR="/opt/scandy"
            
            # Prüfe das aktuelle Verzeichnis zuerst
            CURRENT_DIR="$(pwd)"
            if [ -d "$CURRENT_DIR/app" ] && (echo "$CURRENT_DIR" | grep -qi "scandy"); then
                SOURCE_DIR="$CURRENT_DIR"
                log_info "Verwende aktuelles Verzeichnis als Quelle: $SOURCE_DIR"
            else
                # Fallback auf Standard-Verzeichnisse
                if [ -d "/scandy2" ] && [ -d "/scandy2/app" ]; then
                    SOURCE_DIR="/scandy2"
                elif [ -d "/Scandy" ] && [ -d "/Scandy/app" ]; then
                    SOURCE_DIR="/Scandy"
                elif [ -d "/scandy" ] && [ -d "/scandy/app" ]; then
                    SOURCE_DIR="/scandy"
                elif [ -d "/home/scandy/Scandy2" ] && [ -d "/home/scandy/Scandy2/app" ]; then
                    SOURCE_DIR="/home/scandy/Scandy2"
                elif [ -d "/root/Scandy2" ] && [ -d "/root/Scandy2/app" ]; then
                    SOURCE_DIR="/root/Scandy2"
                else
                    log_error "Quellverzeichnis nicht gefunden!"
                    echo "Verfügbare Verzeichnisse:"
                    find / -name "*scandy*" -type d 2>/dev/null | head -5
                    echo "Aktuelles Verzeichnis: $CURRENT_DIR"
                    echo "Prüfe, ob app-Verzeichnis existiert:"
                    ls -la "$CURRENT_DIR/app" 2>/dev/null || echo "app-Verzeichnis nicht gefunden"
                    exit 1
                fi
            fi
            
            log_info "Verwende Quellverzeichnis: $SOURCE_DIR"
            
            # Git Pull (falls im Quellverzeichnis)
            cd "$SOURCE_DIR"
            log_info "Aktualisiere Code von Git..."
            git pull origin main || git pull origin master || git pull origin IT-VW || {
                log_warning "Git pull fehlgeschlagen, verwende aktuellen Code"
            }
            
            # Backup erstellen
            if [ -d "$TARGET_DIR/app" ]; then
                log_info "Erstelle Backup..."
                BACKUP_DIR="$TARGET_DIR/app.backup.$(date +%Y%m%d_%H%M%S)"
                cp -r "$TARGET_DIR/app" "$BACKUP_DIR" 2>/dev/null || {
                    log_warning "Konnte Backup nicht erstellen"
                }
                log_info "Backup: $BACKUP_DIR"
            fi
            
            # Code kopieren
            log_info "Kopiere Code..."
            
            # Zuerst das Zielverzeichnis leeren (außer Backup-Verzeichnis)
            if [ -d "$TARGET_DIR/app" ]; then
                log_info "Leere Zielverzeichnis..."
                find "$TARGET_DIR/app" -mindepth 1 -not -path "$TARGET_DIR/app/backups*" -delete 2>/dev/null || {
                    log_warning "Konnte Zielverzeichnis nicht vollständig leeren"
                }
            fi
            
            # Code kopieren mit mehreren Fallback-Methoden
            log_info "Kopiere Dateien..."
            SUCCESS=false
            
            # Methode 1: rsync (falls verfügbar)
            if command -v rsync >/dev/null 2>&1; then
                if rsync -av --exclude='backups' "$SOURCE_DIR/app/" "$TARGET_DIR/app/" 2>/dev/null; then
                    log_success "Code mit rsync kopiert!"
                    SUCCESS=true
                fi
            fi
            
            # Methode 2: Standard cp (falls rsync fehlschlägt oder nicht verfügbar)
            if [ "$SUCCESS" = false ]; then
                if cp -r "$SOURCE_DIR/app"/* "$TARGET_DIR/app/" 2>/dev/null; then
                    log_success "Code mit cp kopiert!"
                    SUCCESS=true
                fi
            fi
            
            # Methode 3: Datei für Datei kopieren (als letzter Ausweg)
            if [ "$SUCCESS" = false ]; then
                log_info "Versuche alternative Kopiermethode..."
                for file in "$SOURCE_DIR/app"/*; do
                    if [ -f "$file" ]; then
                        cp "$file" "$TARGET_DIR/app/" 2>/dev/null || log_warning "Konnte $file nicht kopieren"
                    elif [ -d "$file" ] && [ "$(basename "$file")" != "backups" ]; then
                        cp -r "$file" "$TARGET_DIR/app/" 2>/dev/null || log_warning "Konnte Verzeichnis $(basename "$file") nicht kopieren"
                    fi
                done
                log_success "Code kopiert (mit Warnungen)"
                SUCCESS=true
            fi
            
            if [ "$SUCCESS" = false ]; then
                log_error "Alle Kopiermethoden fehlgeschlagen!"
                exit 1
            fi
            
            # Berechtigungen setzen
            log_info "Setze Berechtigungen..."
            chown -R scandy:scandy "$TARGET_DIR/app" 2>/dev/null || {
                log_warning "Konnte Berechtigungen nicht setzen"
            }
            
            # Dependencies aktualisieren
            if [ -d "$TARGET_DIR/venv" ] && [ -f "$TARGET_DIR/requirements.txt" ]; then
                log_info "Aktualisiere Python-Pakete..."
                sudo -u scandy "$TARGET_DIR/venv/bin/pip" install --upgrade -r "$TARGET_DIR/requirements.txt" 2>/dev/null || {
                    log_warning "Konnte Dependencies nicht aktualisieren"
                }
            fi
            
            # Service neu starten
            service_name=$(get_service_name "$INSTANCE_NAME")
            log_info "Starte Service neu: $service_name"
            systemctl restart "$service_name"
            ;;
        lxc)
            log_info "LXC-Update..."
            
            # Verzeichnisse
            TARGET_DIR="/opt/scandy"
            
            # Prüfe das aktuelle Verzeichnis zuerst
            CURRENT_DIR="$(pwd)"
            if [ -d "$CURRENT_DIR/app" ] && (echo "$CURRENT_DIR" | grep -qi "scandy"); then
                SOURCE_DIR="$CURRENT_DIR"
                log_info "Verwende aktuelles Verzeichnis als Quelle: $SOURCE_DIR"
            else
                # Fallback auf Standard-Verzeichnisse
                if [ -d "/scandy2" ] && [ -d "/scandy2/app" ]; then
                    SOURCE_DIR="/scandy2"
                elif [ -d "/Scandy" ] && [ -d "/Scandy/app" ]; then
                    SOURCE_DIR="/Scandy"
                elif [ -d "/scandy" ] && [ -d "/scandy/app" ]; then
                    SOURCE_DIR="/scandy"
                elif [ -d "/home/scandy/Scandy2" ] && [ -d "/home/scandy/Scandy2/app" ]; then
                    SOURCE_DIR="/home/scandy/Scandy2"
                elif [ -d "/root/Scandy2" ] && [ -d "/root/Scandy2/app" ]; then
                    SOURCE_DIR="/root/Scandy2"
                else
                    log_error "Quellverzeichnis nicht gefunden!"
                    echo "Verfügbare Verzeichnisse:"
                    find / -name "*scandy*" -type d 2>/dev/null | head -5
                    echo "Aktuelles Verzeichnis: $CURRENT_DIR"
                    echo "Prüfe, ob app-Verzeichnis existiert:"
                    ls -la "$CURRENT_DIR/app" 2>/dev/null || echo "app-Verzeichnis nicht gefunden"
                    exit 1
                fi
            fi
            
            log_info "Verwende Quellverzeichnis: $SOURCE_DIR"
            
            # Git Pull (falls im Quellverzeichnis)
            cd "$SOURCE_DIR"
            log_info "Aktualisiere Code von Git..."
            git pull origin main || git pull origin master || git pull origin IT-VW || {
                log_warning "Git pull fehlgeschlagen, verwende aktuellen Code"
            }
            
            # Backup erstellen
            if [ -d "$TARGET_DIR/app" ]; then
                log_info "Erstelle Backup..."
                BACKUP_DIR="$TARGET_DIR/app.backup.$(date +%Y%m%d_%H%M%S)"
                cp -r "$TARGET_DIR/app" "$BACKUP_DIR" 2>/dev/null || {
                    log_warning "Konnte Backup nicht erstellen"
                }
                log_info "Backup: $BACKUP_DIR"
            fi
            
            # Code kopieren
            log_info "Kopiere Code..."
            
            # Zuerst das Zielverzeichnis leeren (außer Backup-Verzeichnis)
            if [ -d "$TARGET_DIR/app" ]; then
                log_info "Leere Zielverzeichnis..."
                find "$TARGET_DIR/app" -mindepth 1 -not -path "$TARGET_DIR/app/backups*" -delete 2>/dev/null || {
                    log_warning "Konnte Zielverzeichnis nicht vollständig leeren"
                }
            fi
            
            # Code kopieren mit mehreren Fallback-Methoden
            log_info "Kopiere Dateien..."
            SUCCESS=false
            
            # Methode 1: rsync (falls verfügbar)
            if command -v rsync >/dev/null 2>&1; then
                if rsync -av --exclude='backups' "$SOURCE_DIR/app/" "$TARGET_DIR/app/" 2>/dev/null; then
                    log_success "Code mit rsync kopiert!"
                    SUCCESS=true
                fi
            fi
            
            # Methode 2: Standard cp (falls rsync fehlschlägt oder nicht verfügbar)
            if [ "$SUCCESS" = false ]; then
                if cp -r "$SOURCE_DIR/app"/* "$TARGET_DIR/app/" 2>/dev/null; then
                    log_success "Code mit cp kopiert!"
                    SUCCESS=true
                fi
            fi
            
            # Methode 3: Datei für Datei kopieren (als letzter Ausweg)
            if [ "$SUCCESS" = false ]; then
                log_info "Versuche alternative Kopiermethode..."
                for file in "$SOURCE_DIR/app"/*; do
                    if [ -f "$file" ]; then
                        cp "$file" "$TARGET_DIR/app/" 2>/dev/null || log_warning "Konnte $file nicht kopieren"
                    elif [ -d "$file" ] && [ "$(basename "$file")" != "backups" ]; then
                        cp -r "$file" "$TARGET_DIR/app/" 2>/dev/null || log_warning "Konnte Verzeichnis $(basename "$file") nicht kopieren"
                    fi
                done
                log_success "Code kopiert (mit Warnungen)"
                SUCCESS=true
            fi
            
            if [ "$SUCCESS" = false ]; then
                log_error "Alle Kopiermethoden fehlgeschlagen!"
                exit 1
            fi
            
            # Berechtigungen setzen
            log_info "Setze Berechtigungen..."
            chown -R scandy:scandy "$TARGET_DIR/app" 2>/dev/null || {
                log_warning "Konnte Berechtigungen nicht setzen"
            }
            
            # Dependencies aktualisieren (optional)
            if [ -d "$TARGET_DIR/venv" ] && [ -f "$TARGET_DIR/requirements.txt" ]; then
                log_info "Aktualisiere Python-Pakete..."
                sudo -u scandy "$TARGET_DIR/venv/bin/pip" install --upgrade -r "$TARGET_DIR/requirements.txt" 2>/dev/null || {
                    log_warning "Konnte Dependencies nicht aktualisieren"
                }
            fi
            
            # Service neu starten
            log_info "Starte Scandy-Service neu..."
            systemctl restart scandy 2>/dev/null || {
                log_warning "systemctl restart scandy fehlgeschlagen"
                log_info "Versuche alternative Start-Methoden..."
                
                # Fallback: Docker Compose
                if [ -f "$TARGET_DIR/docker-compose.yml" ]; then
                    log_info "Versuche Docker Compose..."
                    cd "$TARGET_DIR"
                    docker compose restart 2>/dev/null || docker compose up -d 2>/dev/null || {
                        log_error "Docker Compose fehlgeschlagen"
                    }
                else
                    log_error "Keine Start-Methode gefunden!"
                fi
            }
            
            # Status prüfen
            log_info "Prüfe Service-Status..."
            sleep 3
            if systemctl is-active --quiet scandy; then
                log_success "Service läuft!"
            else
                log_warning "Service-Status unklar"
                systemctl status scandy --no-pager -l
            fi
            ;;
    esac
    
    log_success "Update abgeschlossen!"
}

# Management-Skript erstellen
create_management_script() {
    log_step "Erstelle Management-Skript..."
    
    cat > manage_scandy.sh << EOF
#!/bin/bash

# Scandy $INSTANCE_NAME Management Script
# Generated by Universal Installer

INSTALL_MODE="$INSTALL_MODE"
INSTANCE_NAME="$INSTANCE_NAME"
WEB_PORT="$WEB_PORT"
DOCKER_CMD="$DOCKER_CMD"

# Service-Namen für systemd bestimmen
get_service_name() {
    local instance_name="\$1"
    if [ "\$instance_name" = "scandy" ]; then
        echo "scandy"
    else
        echo "scandy-\$instance_name"
    fi
}

show_help() {
    echo "========================================"
    echo "Scandy \$INSTANCE_NAME Management"
    echo "Installation: \$INSTALL_MODE"
    echo "========================================"
    echo
    echo "Befehle:"
    echo "  start     - Scandy starten"
    echo "  stop      - Scandy stoppen"
    echo "  restart   - Scandy neustarten"
    echo "  status    - Status anzeigen"
    echo "  logs      - Logs anzeigen"
    echo "  update    - Update durchführen"
    echo "  backup    - Backup erstellen"
    echo "  shell     - Shell öffnen"
    echo "  info      - Informationen anzeigen"
    echo "  help      - Diese Hilfe"
}

case "\$1" in
    start)
        case \$INSTALL_MODE in
            docker)
                \$DOCKER_CMD compose up -d
                ;;
            native)
                service_name=\$(get_service_name "\$INSTANCE_NAME")
                sudo systemctl start "\$service_name"
                ;;
            lxc)
                systemctl restart scandy 2>/dev/null || {
                    cd /opt/scandy && sudo -u scandy ./start_scandy.sh &
                }
                ;;
        esac
        echo "Scandy \$INSTANCE_NAME gestartet"
        ;;
    stop)
        case \$INSTALL_MODE in
            docker)
                \$DOCKER_CMD compose down
                ;;
            native)
                service_name=\$(get_service_name "\$INSTANCE_NAME")
                sudo systemctl stop "\$service_name"
                ;;
            lxc)
                pkill -f "gunicorn.*scandy"
                ;;
        esac
        echo "Scandy \$INSTANCE_NAME gestoppt"
        ;;
    restart)
        \$0 stop
        sleep 2
        \$0 start
        ;;
    status)
        case \$INSTALL_MODE in
            docker)
                \$DOCKER_CMD compose ps
                ;;
            native)
                service_name=\$(get_service_name "\$INSTANCE_NAME")
                systemctl status "\$service_name"
                ;;
            lxc)
                ps aux | grep gunicorn | grep scandy
                ;;
        esac
        ;;
    logs)
        case \$INSTALL_MODE in
            docker)
                \$DOCKER_CMD compose logs -f
                ;;
            native)
                service_name=\$(get_service_name "\$INSTANCE_NAME")
                journalctl -u "\$service_name" -f
                ;;
            lxc)
                tail -f /opt/scandy/logs/scandy.log
                ;;
        esac
        ;;
    update)
        case \$INSTALL_MODE in
            docker)
                ./install_scandy_universal.sh --update
                ;;
            native)
                ./install_scandy_universal.sh --update
                ;;
            lxc)
                # LXC-spezifisches Update
                TARGET_DIR="/opt/scandy"
                
                # Prüfe das aktuelle Verzeichnis zuerst
                CURRENT_DIR="\$(pwd)"
                if [ -d "\$CURRENT_DIR/app" ] && (echo "\$CURRENT_DIR" | grep -qi "scandy"); then
                    SOURCE_DIR="\$CURRENT_DIR"
                    echo "Verwende aktuelles Verzeichnis als Quelle: \$SOURCE_DIR"
                else
                    # Fallback auf Standard-Verzeichnisse
                    if [ -d "/scandy2" ] && [ -d "/scandy2/app" ]; then
                        SOURCE_DIR="/scandy2"
                    elif [ -d "/Scandy" ] && [ -d "/Scandy/app" ]; then
                        SOURCE_DIR="/Scandy"
                    elif [ -d "/scandy" ] && [ -d "/scandy/app" ]; then
                        SOURCE_DIR="/scandy"
                    elif [ -d "/home/scandy/Scandy2" ] && [ -d "/home/scandy/Scandy2/app" ]; then
                        SOURCE_DIR="/home/scandy/Scandy2"
                    elif [ -d "/root/Scandy2" ] && [ -d "/root/Scandy2/app" ]; then
                        SOURCE_DIR="/root/Scandy2"
                    else
                        echo "Quellverzeichnis nicht gefunden!"
                        find / -name "*scandy*" -type d 2>/dev/null | head -5
                        echo "Aktuelles Verzeichnis: \$CURRENT_DIR"
                        echo "Prüfe, ob app-Verzeichnis existiert:"
                        ls -la "\$CURRENT_DIR/app" 2>/dev/null || echo "app-Verzeichnis nicht gefunden"
                        exit 1
                    fi
                fi
                
                echo "LXC Update gestartet..."
                echo "Quellverzeichnis: \$SOURCE_DIR"
                
                # Git Pull
                cd "\$SOURCE_DIR"
                git pull origin main || git pull origin master || git pull origin IT-VW || {
                    echo "Git pull fehlgeschlagen"
                }
                
                # Backup
                if [ -d "\$TARGET_DIR/app" ]; then
                    BACKUP_DIR="\$TARGET_DIR/app.backup.\$(date +%Y%m%d_%H%M%S)"
                    cp -r "\$TARGET_DIR/app" "\$BACKUP_DIR" 2>/dev/null
                    echo "Backup: \$BACKUP_DIR"
                fi
                
                # Code kopieren
                if cp -r "\$SOURCE_DIR/app"/* "\$TARGET_DIR/app/" 2>/dev/null; then
                    echo "Code kopiert!"
                else
                    echo "Fehler beim Kopieren!"
                    exit 1
                fi
                
                # Berechtigungen
                chown -R scandy:scandy "\$TARGET_DIR/app" 2>/dev/null
                
                # Service neu starten
                systemctl restart scandy 2>/dev/null || {
                    echo "systemctl fehlgeschlagen, versuche alternative Methoden..."
                    if [ -f "\$TARGET_DIR/docker-compose.yml" ]; then
                        cd "\$TARGET_DIR"
                        docker compose restart 2>/dev/null || docker compose up -d 2>/dev/null
                    fi
                }
                
                echo "LXC Update abgeschlossen!"
                ;;
        esac
        ;;
    info)
        echo "========================================"
        echo "Scandy \$INSTANCE_NAME Informationen"
        echo "========================================"
        echo "Installation: \$INSTALL_MODE"
        echo "Web-App: http://localhost:\$WEB_PORT"
        echo "Instance: \$INSTANCE_NAME"
        echo "========================================"
        ;;
    *)
        show_help
        ;;
esac
EOF
    
    chmod +x manage_scandy.sh
    log_success "Management-Skript erstellt: ./manage_scandy.sh"
}

# Finale Informationen anzeigen
show_final_info() {
    echo
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    INSTALLATION ABGESCHLOSSEN                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${WHITE}🌐 ZUGANG:${NC}"
    echo "   Web-App:        http://localhost:${WEB_PORT}"
    if [ "$INSTALL_MODE" = "docker" ]; then
        echo "   Mongo Express:  http://localhost:${MONGO_EXPRESS_PORT}"
    fi
    if [ -n "$DOMAIN" ]; then
        echo "   Domain:         http$([ "$ENABLE_SSL" = true ] && echo "s")://${DOMAIN}"
    fi
    echo
    echo -e "${WHITE}🚀 ERSTEINRICHTUNG:${NC}"
    echo "   👤 Setup-Assistent erstellt ersten Admin-Benutzer"
    echo "   🔒 Sicheres Passwort (min. 8 Zeichen) erforderlich"
    echo "   🌐 Vollständige System-Konfiguration"
    echo
    echo -e "${WHITE}⚙️  VERWALTUNG:${NC}"
    echo "   Management:     ./manage_scandy.sh"
    echo "   Modus:          $INSTALL_MODE"
    echo "   Instance:       $INSTANCE_NAME"
    echo
    echo -e "${WHITE}📝 NÄCHSTE SCHRITTE:${NC}"
    echo "   1. Web-App aufrufen: http://localhost:${WEB_PORT}"
    echo "   2. Setup-Assistent durchlaufen:"
    echo "      • Admin-Benutzer erstellen (eigener Benutzername/Passwort)"
    echo "      • System-Labels konfigurieren"
    echo "      • Optionale Einstellungen anpassen"
    echo "   3. E-Mail-Konfiguration in .env anpassen (optional)"
    echo "   4. SSL-Zertifikat einrichten (falls Domain konfiguriert)"
    echo
    echo -e "${GREEN}✅ SETUP: Beim ersten Aufruf führt Sie der Setup-Assistent durch die Konfiguration!${NC}"
    echo
}

# Hauptfunktion
main() {
    # Banner anzeigen
    show_banner
    
    # Argumente parsen
    parse_arguments "$@"
    
    # System-Kompatibilität prüfen (für interaktive Auswahl benötigt)
    check_system_compatibility
    
    # Installationsmodus bestimmen
    if [ -z "$INSTALL_MODE" ] || [ "$INSTALL_MODE" = "auto" ]; then
        # Interaktive Auswahl verwenden
        interactive_installation_mode
    fi
    
    log_info "Installationsmodus: $INSTALL_MODE"
    log_info "Instance: $INSTANCE_NAME"
    log_info "Ports: Web=$WEB_PORT, MongoDB=$MONGODB_PORT, MongoExpress=$MONGO_EXPRESS_PORT"
    
    # Update-Modus
    if [ "$UPDATE_ONLY" = true ]; then
        update_installation
        show_final_info
        exit 0
    fi
    
    # Port-Konflikte lösen
    resolve_port_conflicts
    
    # Backup erstellen
    create_backup
    
    # .env-Datei erstellen
    create_env_file
    
    # Verzeichnisse erstellen
    mkdir -p data logs backups
    
    # Installation nach Modus
    case $INSTALL_MODE in
        docker)
            install_docker
            ;;
        native)
            install_native
            ;;
        lxc)
            install_lxc
            ;;
        *)
            log_error "Unbekannter Installationsmodus: $INSTALL_MODE"
            exit 1
            ;;
    esac
    
    # Management-Skript erstellen
    create_management_script
    
    # Finale Informationen
    show_final_info
}

# Skript ausführen
main "$@"