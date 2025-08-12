#!/usr/bin/env bash
set -euo pipefail

# Scandy Simple Updater - Aktualisiert bestehende Installation
# Funktioniert immer - auch bei Problemen

echo "🔄 Scandy Simple Updater - Starte Update..."

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

# Port-Auswahl
echo ""
echo "🌐 Port-Auswahl für Scandy:"
echo "1) Port 80 (Standard-HTTP, keine Port-Angabe in URL nötig)"
echo "2) Port 443 (Standard-HTTPS, keine Port-Angabe in URL nötig)"
echo "3) Port 5001 (Standard-Scandy-Port)"
echo "4) Benutzerdefinierter Port"
echo ""
read -p "Wähle Port (1-4): " PORT_CHOICE

case $PORT_CHOICE in
    1)
        WEB_PORT=80
        PORT_NAME="Standard-HTTP"
        ;;
    2)
        WEB_PORT=443
        PORT_NAME="Standard-HTTPS"
        ;;
    3)
        WEB_PORT=5001
        PORT_NAME="Standard-Scandy"
        ;;
    4)
        read -p "Gib benutzerdefinierten Port ein (z.B. 8080): " WEB_PORT
        PORT_NAME="Benutzerdefiniert"
        ;;
    *)
        WEB_PORT=80
        PORT_NAME="Standard-HTTP (Standardauswahl)"
        ;;
esac

# Prüfe ob Port verfügbar ist
if [ "$WEB_PORT" = "80" ] || [ "$WEB_PORT" = "443" ]; then
    if ss -H -ltn 2>/dev/null | grep -q ":$WEB_PORT "; then
        error "Port $WEB_PORT ist bereits belegt!"
        info "Verwende stattdessen Port 5001"
        WEB_PORT=5001
        PORT_NAME="Standard-Scandy (Port 80/443 belegt)"
    fi
fi

success "Verwende Port: $WEB_PORT ($PORT_NAME)"

# Prüfe ob Scandy installiert ist
if [ ! -d "/opt/scandy" ]; then
    error "Scandy ist nicht installiert. Verwende install_scandy_simple_new.sh"
    exit 1
fi

if [ ! -f "/etc/systemd/system/scandy.service" ]; then
    error "Scandy-Service nicht gefunden. Verwende install_scandy_simple_new.sh"
    exit 1
fi

success "Scandy-Installation gefunden - starte Update..."

# 1. Backup der aktuellen Installation
log "Erstelle Backup der aktuellen Installation..."
BACKUP_DIR="/opt/scandy.backup.$(date +%Y%m%d_%H%M%S)"
cp -r /opt/scandy "$BACKUP_DIR"
success "Backup erstellt: $BACKUP_DIR"

# 2. Services stoppen
log "Stoppe Scandy-Service..."
systemctl stop scandy 2>/dev/null || true
sleep 2

# 3. Code aktualisieren
log "Aktualisiere Scandy-Code..."
cd /opt/scandy

# Lösche alten Code (außer venv, .env, logs)
rm -rf app/ config/ *.py 2>/dev/null || true

# Kopiere neuen Code
if [ -d "/home/$(logname)/Scandy2" ]; then
    cp -r /home/$(logname)/Scandy2/* . 2>/dev/null || true
    success "Code von /home/$(logname)/Scandy2 aktualisiert"
elif [ -d "/home/woschj/Scandy2" ]; then
    cp -r /home/woschj/Scandy2/* . 2>/dev/null || true
    success "Code von /home/woschj/Scandy2 aktualisiert"
else
    info "Scandy-Code nicht gefunden - verwende aktuelles Verzeichnis"
    cp -r ./* /opt/scandy/ 2>/dev/null || true
fi

# Berechtigungen setzen
chown -R root:root /opt/scandy 2>/dev/null || true
chmod -R 755 /opt/scandy

# 4. .env-Datei aktualisieren
log "Aktualisiere .env-Datei..."
if [ -f ".env" ]; then
    # Aktualisiere WEB_PORT in .env
    if grep -q "WEB_PORT=" .env; then
        sed -i "s/WEB_PORT=.*/WEB_PORT=$WEB_PORT/" .env
        success "WEB_PORT in .env auf $WEB_PORT aktualisiert"
    else
        echo "WEB_PORT=$WEB_PORT" >> .env
        success "WEB_PORT=$WEB_PORT zu .env hinzugefügt"
    fi
else
    # Erstelle .env neu falls nicht vorhanden
            cat > .env << EOF
# Scandy - Einfache Konfiguration
WEB_PORT=$WEB_PORT
MONGODB_URI=mongodb://localhost:27017/scandy
MONGODB_DB=scandy
SECRET_KEY=scandy_secret_key_123
FLASK_ENV=production
SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
EOF
        success ".env-Datei erstellt mit WEB_PORT=$WEB_PORT"
fi

# 5. Python-Abhängigkeiten aktualisieren
log "Aktualisiere Python-Abhängigkeiten..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install --upgrade pip >/dev/null 2>&1
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --upgrade >/dev/null 2>&1
        success "Python-Abhängigkeiten aktualisiert"
    else
        info "requirements.txt nicht gefunden"
    fi
else
    error "Virtualenv nicht gefunden - erstelle neu..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip >/dev/null 2>&1
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt >/dev/null 2>&1
        success "Python-Abhängigkeiten installiert"
    fi
fi

# 5. App-Datei finden und Service aktualisieren
log "Finde App-Datei und aktualisiere Service..."
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

# 6. Systemd-Service aktualisieren
log "Aktualisiere Systemd-Service..."

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
Environment=PYTHONPATH=/opt/scandy
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
success "Systemd-Service aktualisiert"

# 7. Services starten
log "Starte Services neu..."
systemctl restart scandy

# 8. Warten auf App-Start
log "Warte auf App-Start..."
for i in {1..60}; do
    if ss -H -ltn 2>/dev/null | grep -q ":$WEB_PORT "; then
        success "Scandy läuft auf Port $WEB_PORT"
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
        
        log "Gunicorn-Konfiguration:"
        echo "APP_FILE: $APP_FILE"
        echo "MODULE_NAME: $MODULE_NAME"
        echo "EXEC_START: $EXEC_START"
        
        info "Prüfe Logs: journalctl -u scandy -f"
        
        # Versuche Rollback
        log "Versuche Rollback..."
        systemctl stop scandy 2>/dev/null || true
        rm -rf /opt/scandy
        mv "$BACKUP_DIR" /opt/scandy
        systemctl restart scandy
        log "Rollback abgeschlossen - ursprüngliche Version wiederhergestellt"
        
        exit 1
    fi
    sleep 2
done

# 9. Fertig!
echo ""
success "Update abgeschlossen!"
echo "🌐 Web-App: http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
echo "📊 MongoDB: mongodb://localhost:27017/scandy"
echo "📝 Logs: journalctl -u scandy -f"
echo "💾 Backup: $BACKUP_DIR"
echo ""
echo "Update erfolgreich! Die App läuft mit der neuesten Version. 🎯"
