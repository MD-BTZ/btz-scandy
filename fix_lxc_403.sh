#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy LXC 403 Forbidden Fix"
echo "========================================"
echo "Dieses Skript behebt 403 Forbidden Fehler im LXC-Container:"
echo "- ✅ Static Files Berechtigungen"
echo "- ✅ Upload-Verzeichnis Berechtigungen"
echo "- ✅ Flask-Session Berechtigungen"
echo "- ✅ Nginx-Konfiguration prüfen"
echo "- ✅ Service-Berechtigungen"
echo "========================================"
echo

# Prüfe ob wir als root laufen
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Dieses Script muss als root ausgeführt werden!${NC}"
    echo "Verwende: sudo ./fix_lxc_403.sh"
    exit 1
fi

# 1. Static Files Berechtigungen
echo -e "${BLUE}🔧 1. Korrigiere Static Files Berechtigungen...${NC}"
if [ -d "/opt/scandy/app/static" ]; then
    chmod -R 755 /opt/scandy/app/static/
    chown -R scandy:scandy /opt/scandy/app/static/
    echo -e "${GREEN}✅ Static Files: 755 (scandy:scandy)${NC}"
    ls -la /opt/scandy/app/static/ | head -5
else
    echo -e "${RED}❌ /opt/scandy/app/static Verzeichnis nicht gefunden${NC}"
fi

# 2. Upload-Verzeichnis Berechtigungen
echo -e "${BLUE}🔧 2. Korrigiere Upload-Verzeichnis Berechtigungen...${NC}"
if [ -d "/opt/scandy/app/uploads" ]; then
    chmod -R 755 /opt/scandy/app/uploads/
    chown -R scandy:scandy /opt/scandy/app/uploads/
    echo -e "${GREEN}✅ Upload-Verzeichnis: 755 (scandy:scandy)${NC}"
    ls -la /opt/scandy/app/uploads/ | head -5
else
    echo -e "${YELLOW}⚠️  /opt/scandy/app/uploads Verzeichnis nicht gefunden${NC}"
fi

# 3. Flask-Session Berechtigungen
echo -e "${BLUE}🔧 3. Korrigiere Flask-Session Berechtigungen...${NC}"
if [ -d "/opt/scandy/app/flask_session" ]; then
    chmod -R 755 /opt/scandy/app/flask_session/
    chown -R scandy:scandy /opt/scandy/app/flask_session/
    echo -e "${GREEN}✅ Flask-Session: 755 (scandy:scandy)${NC}"
else
    echo -e "${YELLOW}⚠️  /opt/scandy/app/flask_session Verzeichnis nicht gefunden${NC}"
fi

# 4. App-Verzeichnis Berechtigungen
echo -e "${BLUE}🔧 4. Korrigiere App-Verzeichnis Berechtigungen...${NC}"
if [ -d "/opt/scandy/app" ]; then
    chmod -R 755 /opt/scandy/app/
    chown -R scandy:scandy /opt/scandy/app/
    echo -e "${GREEN}✅ App-Verzeichnis: 755 (scandy:scandy)${NC}"
else
    echo -e "${RED}❌ /opt/scandy/app Verzeichnis nicht gefunden${NC}"
fi

# 5. Nginx-Konfiguration prüfen
echo -e "${BLUE}🔧 5. Prüfe Nginx-Konfiguration...${NC}"
if [ -f "/etc/nginx/sites-enabled/scandy" ]; then
    echo -e "${GREEN}✅ Nginx-Site aktiviert${NC}"
    echo "Nginx-Konfiguration:"
    cat /etc/nginx/sites-enabled/scandy
else
    echo -e "${RED}❌ Nginx-Site nicht gefunden${NC}"
fi

# 6. Nginx-Berechtigungen prüfen
echo -e "${BLUE}🔧 6. Prüfe Nginx-Berechtigungen...${NC}"
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx läuft${NC}"
    # Prüfe ob nginx auf Static Files zugreifen kann
    if [ -d "/opt/scandy/app/static" ]; then
        nginx_user=$(ps aux | grep nginx | grep -v grep | head -1 | awk '{print $1}')
        echo "Nginx läuft als: $nginx_user"
        echo "Static Files gehören: $(ls -ld /opt/scandy/app/static | awk '{print $3":"$4}')"
    fi
else
    echo -e "${RED}❌ Nginx läuft nicht!${NC}"
fi

# 7. Service-Status prüfen
echo -e "${BLUE}🔧 7. Prüfe Service-Status...${NC}"
if systemctl is-active --quiet scandy; then
    echo -e "${GREEN}✅ Scandy-Service läuft${NC}"
else
    echo -e "${RED}❌ Scandy-Service läuft nicht!${NC}"
    echo "Letzte Logs:"
    journalctl -u scandy --no-pager -n 5
fi

# 8. Teste Static Files über HTTP
echo -e "${BLUE}🔧 8. Teste Static Files über HTTP...${NC}"
if command -v curl &> /dev/null; then
    echo -e "${BLUE}🌐 Teste Static Files...${NC}"
    
    # Teste verschiedene Static Files
    static_files=(
        "http://localhost/static/css/main.css"
        "http://localhost/static/js/main.js"
        "http://localhost/static/images/scandy-logo.png"
    )
    
    for file in "${static_files[@]}"; do
        if curl -s -I "$file" | grep -q "200 OK"; then
            echo -e "${GREEN}✅ $file - OK${NC}"
        elif curl -s -I "$file" | grep -q "403 Forbidden"; then
            echo -e "${RED}❌ $file - 403 Forbidden${NC}"
        else
            echo -e "${YELLOW}⚠️  $file - Nicht erreichbar${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  curl nicht verfügbar - kann Static Files nicht testen${NC}"
fi

# 9. Debug-Informationen
echo -e "${BLUE}🔧 9. Debug-Informationen...${NC}"
echo -e "${BLUE}📁 Aktuelle Verzeichnisstruktur:${NC}"
ls -la /opt/scandy/app/static/ 2>/dev/null || echo "app/static/ nicht gefunden"
echo
echo -e "${BLUE}🐧 Service-Status:${NC}"
systemctl status scandy --no-pager -l
echo
echo -e "${BLUE}🌐 Nginx-Status:${NC}"
systemctl status nginx --no-pager -l
echo
echo -e "${BLUE}📋 App-Logs (letzte 5 Zeilen):${NC}"
journalctl -u scandy --no-pager -n 5

# 10. Sofortige Lösungsvorschläge
echo
echo "========================================"
echo -e "${GREEN}✅ 403 Forbidden Fix abgeschlossen!${NC}"
echo "========================================"
echo
echo -e "${BLUE}🔧 Sofortige Lösungsvorschläge:${NC}"
echo "1. Falls 403-Probleme bestehen:"
echo "   sudo systemctl restart nginx"
echo "   sudo systemctl restart scandy"
echo
echo "2. Browser-Cache leeren (Ctrl+F5)"
echo
echo "3. Falls weiterhin Probleme:"
echo "   sudo nginx -t"
echo "   sudo journalctl -u nginx -f"
echo "   sudo journalctl -u scandy -f"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Service neu starten: sudo systemctl restart scandy"
echo "- Nginx neu starten: sudo systemctl restart nginx"
echo "- App-Logs: sudo journalctl -u scandy -f"
echo "- Nginx-Logs: sudo journalctl -u nginx -f"
echo "- Berechtigungen prüfen: ls -la /opt/scandy/app/static/"
echo
echo "========================================"
read -p "Drücke Enter zum Beenden..." 