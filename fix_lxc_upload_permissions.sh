#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy LXC Upload-Berechtigungen Fix"
echo "========================================"
echo "Dieses Skript behebt Upload-Probleme im LXC-Container:"
echo "- ✅ Upload-Verzeichnis Berechtigungen"
echo "- ✅ Static Files Berechtigungen"
echo "- ✅ Flask-Session Berechtigungen"
echo "- ✅ Service-Berechtigungen"
echo "- ✅ Nginx-Konfiguration"
echo "========================================"
echo

# Prüfe ob wir als root laufen
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Dieses Script muss als root ausgeführt werden!${NC}"
    echo "Verwende: sudo ./fix_lxc_upload_permissions.sh"
    exit 1
fi

# 1. Upload-Verzeichnis Berechtigungen
echo -e "${BLUE}🔧 1. Korrigiere Upload-Verzeichnis Berechtigungen...${NC}"

# Prüfe verschiedene mögliche Upload-Pfade
UPLOAD_PATHS=(
    "/opt/scandy/app/uploads"
    "/opt/scandy/app/static/uploads"
    "/opt/scandy/data/uploads"
    "/opt/scandy/uploads"
    "/app/app/uploads"
    "/app/app/static/uploads"
    "/app/uploads"
    "/app/static/uploads"
)

for upload_path in "${UPLOAD_PATHS[@]}"; do
    if [ -d "$upload_path" ]; then
        echo -e "${BLUE}📁 Gefunden: $upload_path${NC}"
        
        # Setze Berechtigungen
        chmod -R 755 "$upload_path"
        chown -R scandy:scandy "$upload_path" 2>/dev/null || chown -R 1000:1000 "$upload_path" 2>/dev/null || true
        
        echo -e "${GREEN}✅ Berechtigungen gesetzt: $upload_path${NC}"
        ls -la "$upload_path" | head -3
        
        # Erstelle Unterverzeichnisse für verschiedene Entitätstypen
        mkdir -p "$upload_path/tickets"
        mkdir -p "$upload_path/jobs"
        mkdir -p "$upload_path/tools"
        mkdir -p "$upload_path/consumables"
        
        chmod -R 755 "$upload_path"
        chown -R scandy:scandy "$upload_path" 2>/dev/null || chown -R 1000:1000 "$upload_path" 2>/dev/null || true
        
        echo -e "${GREEN}✅ Unterverzeichnisse erstellt${NC}"
    fi
done

# 2. Static Files Berechtigungen
echo -e "${BLUE}🔧 2. Korrigiere Static Files Berechtigungen...${NC}"
STATIC_PATHS=(
    "/opt/scandy/app/static"
    "/app/app/static"
    "/app/static"
)

for static_path in "${STATIC_PATHS[@]}"; do
    if [ -d "$static_path" ]; then
        echo -e "${BLUE}📁 Gefunden: $static_path${NC}"
        
        chmod -R 755 "$static_path"
        chown -R scandy:scandy "$static_path" 2>/dev/null || chown -R 1000:1000 "$static_path" 2>/dev/null || true
        
        echo -e "${GREEN}✅ Static Files: 755${NC}"
        ls -la "$static_path" | head -3
    fi
done

# 3. Flask-Session Berechtigungen
echo -e "${BLUE}🔧 3. Korrigiere Flask-Session Berechtigungen...${NC}"
SESSION_PATHS=(
    "/opt/scandy/app/flask_session"
    "/app/app/flask_session"
    "/app/flask_session"
)

for session_path in "${SESSION_PATHS[@]}"; do
    if [ -d "$session_path" ]; then
        echo -e "${BLUE}📁 Gefunden: $session_path${NC}"
        
        chmod -R 755 "$session_path"
        chown -R scandy:scandy "$session_path" 2>/dev/null || chown -R 1000:1000 "$session_path" 2>/dev/null || true
        
        echo -e "${GREEN}✅ Flask-Session: 755${NC}"
    fi
done

# 4. Prüfe und korrigiere Service-Berechtigungen
echo -e "${BLUE}🔧 4. Prüfe Service-Berechtigungen...${NC}"

# Prüfe ob scandy Service läuft
if systemctl is-active --quiet scandy; then
    echo -e "${GREEN}✅ Scandy Service läuft${NC}"
    
    # Prüfe Service-User
    SERVICE_USER=$(systemctl show scandy --property=User --value 2>/dev/null || echo "scandy")
    echo -e "${BLUE}📋 Service-User: $SERVICE_USER${NC}"
    
    # Setze Berechtigungen basierend auf Service-User
    if [ "$SERVICE_USER" != "root" ]; then
        for upload_path in "${UPLOAD_PATHS[@]}"; do
            if [ -d "$upload_path" ]; then
                chown -R "$SERVICE_USER:$SERVICE_USER" "$upload_path" 2>/dev/null || true
                echo -e "${GREEN}✅ Upload-Berechtigungen für $SERVICE_USER gesetzt: $upload_path${NC}"
            fi
        done
    fi
else
    echo -e "${YELLOW}⚠️  Scandy Service läuft nicht${NC}"
fi

# 5. Prüfe Nginx-Konfiguration
echo -e "${BLUE}🔧 5. Prüfe Nginx-Konfiguration...${NC}"
if command -v nginx &> /dev/null; then
    echo -e "${BLUE}📋 Nginx-Konfiguration:${NC}"
    
    # Prüfe ob Nginx-Konfiguration Upload-Verzeichnisse korrekt referenziert
    if [ -f "/etc/nginx/sites-available/scandy" ]; then
        echo -e "${BLUE}📄 Scandy Nginx-Konfiguration gefunden${NC}"
        
        # Prüfe ob Upload-Location existiert
        if grep -q "location /uploads" /etc/nginx/sites-available/scandy; then
            echo -e "${GREEN}✅ Upload-Location in Nginx konfiguriert${NC}"
        else
            echo -e "${YELLOW}⚠️  Upload-Location fehlt in Nginx-Konfiguration${NC}"
            echo -e "${BLUE}💡 Füge folgende Zeilen zur Nginx-Konfiguration hinzu:${NC}"
            echo "    location /uploads {"
            echo "        alias /opt/scandy/app/uploads;"
            echo "        expires 1d;"
            echo "    }"
        fi
        
        # Teste Nginx-Konfiguration
        if nginx -t; then
            echo -e "${GREEN}✅ Nginx-Konfiguration ist gültig${NC}"
            systemctl reload nginx
            echo -e "${GREEN}✅ Nginx neu geladen${NC}"
        else
            echo -e "${RED}❌ Nginx-Konfiguration hat Fehler${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Scandy Nginx-Konfiguration nicht gefunden${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Nginx nicht installiert${NC}"
fi

# 6. Prüfe Docker-Container (falls verwendet)
echo -e "${BLUE}🔧 6. Prüfe Docker-Container...${NC}"
if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo -e "${BLUE}🐳 Docker verfügbar${NC}"
    
    # Prüfe ob Scandy-Container läuft
    if docker ps | grep -q scandy; then
        echo -e "${GREEN}✅ Scandy-Container läuft${NC}"
        
        # Korrigiere Berechtigungen im Container
        for container in $(docker ps --filter "name=scandy" --format "{{.Names}}"); do
            echo -e "${BLUE}🔧 Korrigiere Berechtigungen in Container: $container${NC}"
            
            # Korrigiere Upload-Berechtigungen im Container
            docker exec "$container" chmod -R 755 /app/app/uploads/ 2>/dev/null || true
            docker exec "$container" chmod -R 755 /app/app/static/uploads/ 2>/dev/null || true
            docker exec "$container" chmod -R 755 /app/uploads/ 2>/dev/null || true
            docker exec "$container" chmod -R 755 /app/static/uploads/ 2>/dev/null || true
            
            echo -e "${GREEN}✅ Container-Berechtigungen korrigiert: $container${NC}"
        done
    else
        echo -e "${YELLOW}⚠️  Scandy-Container läuft nicht${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker nicht verfügbar${NC}"
fi

# 7. Teste Upload-Funktionalität
echo -e "${BLUE}🔧 7. Teste Upload-Funktionalität...${NC}"

# Erstelle Test-Datei
TEST_FILE="/tmp/upload_test.txt"
echo "Upload-Test-Datei" > "$TEST_FILE"

# Teste verschiedene Upload-Pfade
for upload_path in "${UPLOAD_PATHS[@]}"; do
    if [ -d "$upload_path" ]; then
        echo -e "${BLUE}🧪 Teste Upload-Pfad: $upload_path${NC}"
        
        # Versuche Test-Datei zu kopieren
        if cp "$TEST_FILE" "$upload_path/test_upload.txt" 2>/dev/null; then
            echo -e "${GREEN}✅ Upload-Test erfolgreich: $upload_path${NC}"
            rm -f "$upload_path/test_upload.txt"
        else
            echo -e "${RED}❌ Upload-Test fehlgeschlagen: $upload_path${NC}"
        fi
    fi
done

# Entferne Test-Datei
rm -f "$TEST_FILE"

# 8. Debug-Informationen
echo -e "${BLUE}🔧 8. Debug-Informationen...${NC}"
echo -e "${BLUE}📁 Aktuelle Verzeichnisstruktur:${NC}"
find /opt/scandy -name "uploads" -type d 2>/dev/null | head -5
find /app -name "uploads" -type d 2>/dev/null | head -5

echo -e "${BLUE}👤 Aktuelle Benutzer:${NC}"
id scandy 2>/dev/null || echo "scandy Benutzer nicht gefunden"
id 1000 2>/dev/null || echo "UID 1000 nicht gefunden"

echo -e "${BLUE}📊 Speicherplatz:${NC}"
df -h /opt/scandy 2>/dev/null || df -h /app 2>/dev/null || echo "Speicherplatz-Info nicht verfügbar"

# 9. Abschluss
echo
echo -e "${GREEN}========================================"
echo -e "✅ Upload-Berechtigungen Fix abgeschlossen!"
echo -e "========================================"
echo
echo -e "${BLUE}📋 Nächste Schritte:${NC}"
echo -e "1. Starte Scandy-Service neu: systemctl restart scandy"
echo -e "2. Teste Upload-Funktionalität im Browser"
echo -e "3. Prüfe Logs bei Problemen: journalctl -u scandy -f"
echo -e "4. Prüfe Nginx-Logs: tail -f /var/log/nginx/error.log"
echo
echo -e "${YELLOW}💡 Falls Uploads immer noch nicht funktionieren:${NC}"
echo -e "   - Prüfe Firewall-Einstellungen"
echo -e "   - Prüfe SELinux-Status (falls aktiv)"
echo -e "   - Prüfe AppArmor-Profile"
echo -e "   - Prüfe Container-Netzwerk-Konfiguration"
echo 