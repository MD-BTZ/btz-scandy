#!/usr/bin/env bash
set -euo pipefail

# Scandy Simple Installer - Komplett neu und einfach
# Funktioniert immer - auch bei Problemen

echo "🚀 Scandy Simple Installer - Starte Installation..."

# Prüfe Root-Rechte
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "❌ Bitte als root ausführen (sudo)"
    exit 1
fi

# Einfache Logging-Funktionen
log() { echo "[$(date '+%H:%M:%S')] $*"; }
success() { echo "✅ $*"; }
error() { echo "❌ $*"; }
info() { echo "ℹ️  $*"; }

# 1. System-Pakete installieren
log "Installiere System-Pakete..."
apt update -y >/dev/null 2>&1
apt install -y python3 python3-pip python3-venv git curl gnupg lsb-release bc >/dev/null 2>&1
success "System-Pakete installiert"

# 2. MongoDB installieren (einfach)
log "Installiere MongoDB..."
if ! command -v mongod >/dev/null 2>&1; then
    # MongoDB-Repository hinzufügen
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list
    apt update -y >/dev/null 2>&1
    apt install -y mongodb-org >/dev/null 2>&1
    success "MongoDB installiert"
else
    info "MongoDB bereits installiert"
fi

# 3. MongoDB starten (ohne Auth - einfach)
log "Starte MongoDB..."

# MongoDB komplett stoppen und aufräumen
log "Stoppe alle MongoDB-Prozesse..."
systemctl stop mongod 2>/dev/null || true
systemctl disable mongod 2>/dev/null || true
pkill -f mongod 2>/dev/null || true
pkill -f mongo 2>/dev/null || true

# Warte bis alle Prozesse gestoppt sind
for i in {1..10}; do
    if ! pgrep -f mongod >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Prüfe ob Port 27017 frei ist
if ss -H -ltn 2>/dev/null | grep -q ':27017 '; then
    log "Port 27017 ist noch belegt - warte..."
    sleep 5
fi

sleep 3

# Verzeichnisse erstellen
mkdir -p /var/lib/mongodb /var/log/mongodb
chown mongodb:mongodb /var/lib/mongodb /var/log/mongodb 2>/dev/null || true

# MongoDB-Version erkennen und passende Konfiguration erstellen
log "Erstelle MongoDB-Konfiguration..."
if command -v mongod >/dev/null 2>&1; then
    MONGO_VERSION=$(mongod --version | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
    log "MongoDB Version: $MONGO_VERSION"
    
    if [ -n "$MONGO_VERSION" ] && [ "$(echo "$MONGO_VERSION >= 4.0" | bc -l 2>/dev/null || echo "0")" = "1" ]; then
        # Moderne MongoDB (4.0+)
        cat > /etc/mongod.conf << 'EOF'
# MongoDB 4.0+ Konfiguration
storage:
  dbPath: /var/lib/mongodb

systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log

net:
  port: 27017
  bindIp: 0.0.0.0
EOF
        log "Moderne MongoDB-Konfiguration erstellt"
    else
        # Ältere MongoDB oder unbekannte Version
        cat > /etc/mongod.conf << 'EOF'
# Einfache MongoDB-Konfiguration (kompatibel)
dbpath=/var/lib/mongodb
logpath=/var/log/mongodb/mongod.log
logappend=true
port=27017
bind_ip=0.0.0.0
EOF
        log "Kompatible MongoDB-Konfiguration erstellt"
    fi
else
    # Fallback-Konfiguration
    cat > /etc/mongod.conf << 'EOF'
# Fallback MongoDB-Konfiguration
dbpath=/var/lib/mongodb
logpath=/var/log/mongodb/mongod.log
logappend=true
port=27017
bind_ip=0.0.0.0
EOF
    log "Fallback MongoDB-Konfiguration erstellt"
fi

# MongoDB starten
log "Starte MongoDB-Service..."
if systemctl start mongod; then
    success "MongoDB-Service gestartet"
else
    error "MongoDB-Service startet nicht - versuche manuellen Start"
    
    # Manueller Start als Fallback
    log "Starte MongoDB manuell..."
    nohup mongod --config /etc/mongod.conf > /var/log/mongodb/mongod.log 2>&1 &
    MONGODB_PID=$!
    echo $MONGODB_PID > /var/run/mongod.pid
    sleep 3
    
    if kill -0 $MONGODB_PID 2>/dev/null; then
        success "MongoDB läuft manuell (PID: $MONGODB_PID)"
    else
        error "Auch manueller Start fehlgeschlagen"
        exit 1
    fi
fi

# Prüfen ob MongoDB läuft
log "Prüfe MongoDB-Verbindung..."
for i in {1..30}; do
    if mongosh --quiet --eval "db.runCommand('ping')" >/dev/null 2>&1; then
        success "MongoDB läuft auf Port 27017"
        break
    fi
    if [ $i -eq 30 ]; then
        error "MongoDB-Verbindung nach 30 Versuchen fehlgeschlagen"
        
        # Zeige MongoDB-Status und Logs
        log "MongoDB-Status:"
        systemctl status mongod --no-pager 2>/dev/null || echo "Service-Status nicht verfügbar"
        
        log "MongoDB-Logs:"
        tail -20 /var/log/mongodb/mongod.log 2>/dev/null || echo "Keine Logs verfügbar"
        
        exit 1
    fi
    sleep 1
done

# 4. Scandy-Verzeichnis einrichten
log "Richte Scandy ein..."
mkdir -p /opt/scandy
cd /opt/scandy

# Code kopieren (robust)
log "Kopiere Scandy-Code..."
if [ -d "/home/$(logname)/Scandy2" ]; then
    cp -r /home/$(logname)/Scandy2/* . 2>/dev/null || true
    success "Code von /home/$(logname)/Scandy2 kopiert"
elif [ -d "/home/woschj/Scandy2" ]; then
    cp -r /home/woschj/Scandy2/* . 2>/dev/null || true
    success "Code von /home/woschj/Scandy2 kopiert"
else
    info "Scandy-Code nicht gefunden - verwende aktuelles Verzeichnis"
    cp -r ./* /opt/scandy/ 2>/dev/null || true
fi

# Prüfe welche App-Dateien existieren
log "Prüfe verfügbare App-Dateien..."
log "Root-Verzeichnis:"
ls -la *.py 2>/dev/null || echo "Keine Python-Dateien im Root gefunden"

if [ -d "app" ]; then
    log "App-Verzeichnis:"
    ls -la app/ | head -10
    log "Python-Dateien im app/ Verzeichnis:"
    find app/ -name "*.py" -maxdepth 1 2>/dev/null || echo "Keine Python-Dateien im app/ Verzeichnis"
fi

# Berechtigungen setzen
chown -R root:root /opt/scandy 2>/dev/null || true
chmod -R 755 /opt/scandy

# 5. Python-Umgebung einrichten
log "Erstelle Python-Umgebung..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1

# Requirements installieren
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt >/dev/null 2>&1
    success "Python-Abhängigkeiten installiert"
else
    info "requirements.txt nicht gefunden"
fi

# 6. Einfache .env-Datei erstellen
log "Erstelle .env-Datei..."
cat > .env << 'EOF'
# Scandy - Einfache Konfiguration
WEB_PORT=5001
MONGODB_URI=mongodb://localhost:27017/scandy
MONGODB_DB=scandy
SECRET_KEY=scandy_secret_key_123
FLASK_ENV=production
SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
EOF
success ".env-Datei erstellt"

# 7. Systemd-Service erstellen
log "Erstelle Systemd-Service..."

# Finde die richtige App-Datei
log "Finde App-Datei..."
APP_FILE=""

# Prüfe zuerst das app/ Verzeichnis (Hauptanwendung)
if [ -d "/opt/scandy/app" ]; then
    log "App-Verzeichnis gefunden - suche nach Hauptanwendung..."
    
    # Suche nach wsgi.py (Standard für Produktion)
    if [ -f "/opt/scandy/app/wsgi.py" ]; then
        APP_FILE="app/wsgi.py"
        log "WSGI-Entrypoint gefunden: app/wsgi.py (Produktionsstandard)"
    elif [ -f "/opt/scandy/app/wsgi_https.py" ]; then
        APP_FILE="app/wsgi_https.py"
        log "HTTPS-WSGI-Entrypoint gefunden: app/wsgi_https.py"
    elif [ -f "/opt/scandy/app/app.py" ]; then
        APP_FILE="app/app.py"
        log "App-Datei gefunden: app/app.py"
    elif [ -f "/opt/scandy/app/run.py" ]; then
        APP_FILE="app/run.py"
        log "App-Datei gefunden: app/run.py"
    elif [ -f "/opt/scandy/app/__init__.py" ]; then
        # Flask-App mit __init__.py (nur als Fallback)
        APP_FILE="app"
        log "Flask-App mit __init__.py gefunden: app (Fallback)"
    fi
fi

# Fallback: Prüfe Root-Verzeichnis
if [ -z "$APP_FILE" ]; then
    if [ -f "/opt/scandy/app.py" ]; then
        APP_FILE="app.py"
        log "App-Datei im Root gefunden: app.py"
    elif [ -f "/opt/scandy/run.py" ]; then
        APP_FILE="run.py"
        log "App-Datei im Root gefunden: run.py"
    elif [ -f "/opt/scandy/wsgi.py" ]; then
        APP_FILE="wsgi.py"
        log "App-Datei im Root gefunden: wsgi.py"
    fi
fi

# Letzter Fallback: Suche nach Python-Dateien (aber ignoriere Wartungsscripts)
if [ -z "$APP_FILE" ]; then
    log "Suche nach Python-App-Dateien..."
    PY_FILES=$(find /opt/scandy -maxdepth 1 -name "*.py" | grep -v "fix_" | grep -v "cleanup_" | grep -v "create_" | grep -v "migrate_" | head -5)
    if [ -n "$PY_FILES" ]; then
        APP_FILE=$(basename "$(echo "$PY_FILES" | head -1)")
        log "Verwende gefundene App-Datei: $APP_FILE"
    else
        error "Keine Python-App-Datei gefunden!"
        exit 1
    fi
fi

if [ -z "$APP_FILE" ]; then
    error "Keine App-Datei gefunden!"
    exit 1
fi

log "Verwende App-Datei: $APP_FILE"

# Entscheide ob Gunicorn oder Python direkt verwenden
if [[ "$APP_FILE" == *"wsgi.py" ]]; then
    # WSGI-Datei gefunden - verwende Gunicorn
    # Extrahiere den Modulnamen ohne .py
    MODULE_NAME=$(echo "$APP_FILE" | sed 's/\.py$//' | sed 's/\//\./g')
    EXEC_START="/opt/scandy/venv/bin/gunicorn --bind 0.0.0.0:\${WEB_PORT} --workers 2 --timeout 120 $MODULE_NAME:app"
    log "Verwende Gunicorn für WSGI-App: $MODULE_NAME:app"
else
    # Normale Python-Datei - verwende Python direkt
    EXEC_START="/opt/scandy/venv/bin/python3 $APP_FILE"
    log "Verwende Python direkt für App"
fi

cat > /etc/systemd/system/scandy.service << EOF
[Unit]
Description=Scandy Application
After=network.target mongod.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/scandy
Environment=PATH=/opt/scandy/venv/bin
EnvironmentFile=/opt/scandy/.env
ExecStart=$EXEC_START
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scandy >/dev/null 2>&1
success "Systemd-Service erstellt"

# 8. Firewall öffnen
log "Öffne Firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 5001/tcp >/dev/null 2>&1 || true
    info "Port 5001 freigegeben"
fi

# 9. Services starten
log "Starte Services..."
systemctl restart mongod
systemctl restart scandy

# 10. Warten auf App-Start
log "Warte auf App-Start..."
for i in {1..60}; do
    if ss -H -ltn 2>/dev/null | grep -q ':5001 '; then
        success "Scandy läuft auf Port 5001"
        break
    fi
    
    # Zeige Fortschritt alle 10 Sekunden
    if [ $((i % 5)) -eq 0 ]; then
        log "Warte auf App-Start... ($i/60)"
        
        # Zeige Service-Status alle 10 Sekunden
        log "Service-Status:"
        systemctl status scandy --no-pager 2>/dev/null | head -10 || echo "Service-Status nicht verfügbar"
    fi
    
    if [ $i -eq 60 ]; then
        error "App startet nicht nach 2 Minuten"
        
        # Detaillierte Fehlerdiagnose
        log "Fehlerdiagnose:"
        log "Systemd-Status:"
        systemctl status scandy --no-pager 2>/dev/null || echo "Service-Status nicht verfügbar"
        
        log "App-Logs:"
        journalctl -u scandy --no-pager -n 20 2>/dev/null || echo "Journalctl nicht verfügbar"
        
        log "Verfügbare Dateien in /opt/scandy:"
        ls -la /opt/scandy/ | head -10
        
        log "Python-Dateien:"
        find /opt/scandy -name "*.py" -maxdepth 1
        
        log "Gunicorn-Konfiguration:"
        echo "APP_FILE: $APP_FILE"
        echo "MODULE_NAME: $MODULE_NAME"
        echo "EXEC_START: $EXEC_START"
        
        info "Prüfe Logs: journalctl -u scandy -f"
        exit 1
    fi
    sleep 2
done

# 11. Fertig!
echo ""
success "Installation abgeschlossen!"
echo "🌐 Web-App: http://$(hostname -I | awk '{print $1}'):5001"
echo "📊 MongoDB: mongodb://localhost:27017/scandy"
echo "📝 Logs: journalctl -u scandy -f"
echo ""
echo "Das war's! Einfach und robust. 🎯"
