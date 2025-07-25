#!/bin/bash
set -e

# Farben
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}==== Scandy LXC-Installationsskript für Linux Mint ====${NC}"

# Funktion für Logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# 1. System aktualisieren
log "Aktualisiere System..."
apt update && apt upgrade -y

# 2. Basis-Pakete installieren
log "Installiere Basis-Pakete..."
apt install -y python3 python3-pip python3-venv git nginx curl gnupg lsb-release wget software-properties-common

# 3. MongoDB installieren (Linux Mint optimiert)
log "Installiere MongoDB..."

# Erkenne Linux Mint Version
MINT_VERSION=$(lsb_release -rs)
log "Linux Mint Version erkannt: $MINT_VERSION"

# Bestimme den entsprechenden Ubuntu-Codename für MongoDB
case $MINT_VERSION in
    "22.1"|"22.2"|"22.3")
        UBUNTU_CODENAME="noble"
        ;;
    "21.3"|"21.2"|"21.1")
        UBUNTU_CODENAME="jammy"
        ;;
    "20.3"|"20.2"|"20.1")
        UBUNTU_CODENAME="focal"
        ;;
    "19.3"|"19.2"|"19.1")
        UBUNTU_CODENAME="bionic"
        ;;
    *)
        # Fallback für neuere Versionen
        UBUNTU_CODENAME="noble"
        log "${YELLOW}Warnung: Unbekannte Linux Mint Version, verwende noble als Fallback${NC}"
        ;;
esac

log "Verwende Ubuntu-Codename: $UBUNTU_CODENAME für MongoDB-Repository"

# MongoDB GPG-Key hinzufügen
log "Füge MongoDB GPG-Key hinzu..."

# Erstelle temporäres Verzeichnis mit korrekten Berechtigungen
TEMP_DIR=$(mktemp -d)
chmod 755 "$TEMP_DIR"

# Versuche Download mit verschiedenen Methoden
if curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o "$TEMP_DIR/server-7.0.asc"; then
    log "MongoDB GPG-Key erfolgreich heruntergeladen"
elif wget -qO "$TEMP_DIR/server-7.0.asc" https://pgp.mongodb.com/server-7.0.asc; then
    log "MongoDB GPG-Key erfolgreich heruntergeladen (wget)"
else
    log "${RED}Fehler: Konnte den MongoDB GPG-Key nicht herunterladen!${NC}"
    log "Versuche alternative Methode..."
    
    # Alternative: Direkt mit gpg importieren
    if curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg; then
        log "MongoDB GPG-Key erfolgreich importiert (direkt)"
    else
        log "${RED}Fehler: Alle Download-Methoden fehlgeschlagen!${NC}"
        log "Prüfe Internetverbindung und DNS-Einstellungen"
        exit 1
    fi
fi

# Nur ausführen, wenn die Datei existiert
if [ -f "$TEMP_DIR/server-7.0.asc" ]; then
    # GPG-Key mit sudo importieren
    if gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg "$TEMP_DIR/server-7.0.asc" 2>/dev/null; then
        log "MongoDB GPG-Key erfolgreich importiert"
    else
        log "${YELLOW}Warnung: GPG-Import fehlgeschlagen, versuche alternative Methode...${NC}"
        # Alternative: Direkt mit curl und gpg
        if curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg 2>/dev/null; then
            log "MongoDB GPG-Key erfolgreich importiert (alternative Methode)"
        else
            log "${RED}Fehler: GPG-Key konnte nicht importiert werden${NC}"
            log "Versuche manuelle Methode..."
            # Manuelle Methode
            rm -f /usr/share/keyrings/mongodb-server-7.0.gpg
            curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
        fi
    fi
    rm -rf "$TEMP_DIR"
fi

# MongoDB Repository hinzufügen
log "Füge MongoDB Repository hinzu..."
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $UBUNTU_CODENAME/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list

# System aktualisieren und MongoDB installieren
apt update
apt install -y mongodb-org

# 4. Benutzer erstellen (falls nicht vorhanden)
log "Erstelle Benutzer 'scandy'..."
if ! id "scandy" &>/dev/null; then
    useradd -m -s /bin/bash scandy
    log "Benutzer 'scandy' erstellt"
else
    log "Benutzer 'scandy' existiert bereits"
fi

# 5. Verzeichnis anlegen
log "Erstelle Verzeichnisse..."
mkdir -p /opt/scandy
chown scandy:scandy /opt/scandy

# 6. Code ins Zielverzeichnis kopieren
if [ "$PWD" != "/opt/scandy" ]; then
    log "Kopiere Code nach /opt/scandy..."
    cp -r . /opt/scandy/
    chown -R scandy:scandy /opt/scandy
fi

cd /opt/scandy

# 7. Python-Umgebung einrichten
log "Richte Python-Umgebung ein..."
sudo -u scandy python3 -m venv /opt/scandy/venv
sudo -u scandy /opt/scandy/venv/bin/pip install --upgrade pip
sudo -u scandy /opt/scandy/venv/bin/pip install -r /opt/scandy/requirements.txt

# 8. MongoDB einrichten und starten
log "Starte MongoDB..."
systemctl enable mongod
systemctl start mongod

# Warte auf MongoDB-Start
log "Warte auf MongoDB-Start..."
for i in {1..30}; do
    if systemctl is-active --quiet mongod; then
        log "MongoDB läuft"
        break
    fi
    if [ $i -eq 30 ]; then
        log "${RED}Fehler: MongoDB konnte nicht gestartet werden${NC}"
        systemctl status mongod
        exit 1
    fi
    sleep 2
done

# 9. MongoDB-Authentifizierung einrichten
log "Richte MongoDB-Authentifizierung ein..."
sleep 5  # Warte auf vollständigen MongoDB-Start

# Erstelle Admin-Benutzer
mongosh --eval "
use admin
db.createUser({
  user: 'admin',
  pwd: 'scandy123456',
  roles: [
    { role: 'userAdminAnyDatabase', db: 'admin' },
    { role: 'readWriteAnyDatabase', db: 'admin' },
    { role: 'dbAdminAnyDatabase', db: 'admin' }
  ]
})
" || log "${YELLOW}Warnung: MongoDB-Authentifizierung konnte nicht eingerichtet werden${NC}"

# 10. .env-Datei anlegen
log "Erstelle .env-Datei..."
cat > /opt/scandy/.env <<EOF
# MongoDB Konfiguration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=scandy123456
MONGO_INITDB_DATABASE=scandy
MONGODB_URI=mongodb://admin:scandy123456@localhost:27017/scandy?authSource=admin
MONGODB_DB=scandy

# Sicherheit
SECRET_KEY=$(openssl rand -hex 32)

# Flask-Konfiguration
FLASK_ENV=production
FLASK_DEBUG=False

# System-Namen
SYSTEM_NAME=Scandy
TICKET_SYSTEM_NAME=Aufgaben
TOOL_SYSTEM_NAME=Werkzeuge
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter

# Session-Konfiguration
SESSION_COOKIE_SECURE=False
REMEMBER_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=False
REMEMBER_COOKIE_HTTPONLY=False
EOF

chown scandy:scandy /opt/scandy/.env

# 11. Systemd-Service für Scandy anlegen
log "Erstelle Systemd-Service..."
cat > /etc/systemd/system/scandy.service <<EOF
[Unit]
Description=Scandy Flask App
After=network.target mongod.service
Requires=mongod.service

[Service]
User=scandy
Group=scandy
WorkingDirectory=/opt/scandy
Environment=PATH=/opt/scandy/venv/bin
EnvironmentFile=/opt/scandy/.env
ExecStart=/opt/scandy/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 120 app.wsgi:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scandy

# 12. Nginx als Reverse Proxy einrichten
log "Konfiguriere Nginx..."
cat > /etc/nginx/sites-available/scandy <<'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static {
        alias /opt/scandy/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /opt/scandy/app/uploads;
        expires 1d;
    }
}
EOF

ln -sf /etc/nginx/sites-available/scandy /etc/nginx/sites-enabled/scandy
rm -f /etc/nginx/sites-enabled/default

# 13. Berechtigungen korrigieren
log "Korrigiere Berechtigungen..."
if [ -d "/opt/scandy/app/static" ]; then
    chmod -R 755 /opt/scandy/app/static/
    chown -R scandy:scandy /opt/scandy/app/static/
fi

if [ -d "/opt/scandy/app/uploads" ]; then
    chmod -R 755 /opt/scandy/app/uploads/
    chown -R scandy:scandy /opt/scandy/app/uploads/
fi

if [ -d "/opt/scandy/app/flask_session" ]; then
    chmod -R 755 /opt/scandy/app/flask_session/
    chown -R scandy:scandy /opt/scandy/app/flask_session/
fi

# 14. Services starten
log "Starte Services..."
systemctl restart nginx
systemctl restart scandy

# 15. Firewall konfigurieren (falls ufw aktiv ist)
if command -v ufw &> /dev/null && ufw status | grep -q "Status: active"; then
    log "Konfiguriere Firewall..."
    ufw allow 80/tcp
    ufw allow 22/tcp
fi

# 16. Abschluss
IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}==== Installation abgeschlossen! ====${NC}"
echo -e "${GREEN}✅ Scandy läuft jetzt unter: http://$IP/${NC}"
echo -e "${GREEN}✅ MongoDB läuft auf localhost:27017${NC}"
echo -e "${GREEN}✅ Admin-Benutzer: admin / scandy123456${NC}"
echo -e "${YELLOW}⚠️  WICHTIG: Ändern Sie das Standard-Passwort in der .env-Datei!${NC}"

# 17. Status-Check
log "Führe Status-Check durch..."
echo -e "${BLUE}=== Service-Status ===${NC}"
systemctl status mongod --no-pager -l
echo ""
systemctl status scandy --no-pager -l
echo ""
systemctl status nginx --no-pager -l

echo -e "${GREEN}✅ Installation erfolgreich abgeschlossen!${NC}" 