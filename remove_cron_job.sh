#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================"
echo "Scandy Cron-Job Entfernung"
echo "========================================"
echo "Dieses Skript entfernt den Cron-Job für die"
echo "automatische Bereinigung abgelaufener Accounts."
echo "========================================"
echo "${NC}"

# Prüfe ob wir als root laufen
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Dieses Script muss als root ausgeführt werden!${NC}"
    echo "Verwende: sudo ./remove_cron_job.sh"
    exit 1
fi

echo -e "${YELLOW}⚠️  WARNUNG: Der Cron-Job für die automatische Bereinigung wird entfernt!${NC}"
echo "   Abgelaufene Accounts und Jobs werden nicht mehr automatisch gelöscht."
echo "   Sie müssen die Bereinigung manuell über die Admin-Oberfläche durchführen."
echo

read -p "Möchten Sie fortfahren? (j/N): " confirm
if [[ ! $confirm =~ ^[Jj]$ ]]; then
    echo "Entfernung abgebrochen."
    exit 0
fi

echo -e "${BLUE}🔍 Suche nach Cron-Job...${NC}"

# Entferne Cron-Job
if crontab -l 2>/dev/null | grep -q "cleanup_expired.sh"; then
    echo -e "${BLUE}🗑️  Entferne Cron-Job...${NC}"
    crontab -l 2>/dev/null | grep -v "cleanup_expired.sh" | crontab -
    echo -e "${GREEN}✅ Cron-Job erfolgreich entfernt${NC}"
else
    echo -e "${YELLOW}⚠️  Kein Cron-Job für Cleanup gefunden${NC}"
fi

# Entferne Cleanup-Skript (optional)
echo -e "${BLUE}🗑️  Entferne Cleanup-Skript...${NC}"
if [ -f "/opt/scandy/cleanup_expired.sh" ]; then
    rm /opt/scandy/cleanup_expired.sh
    echo -e "${GREEN}✅ Cleanup-Skript entfernt${NC}"
else
    echo -e "${YELLOW}⚠️  Cleanup-Skript nicht gefunden${NC}"
fi

# Entferne Cleanup-Python-Skript (optional)
if [ -f "/opt/scandy/cleanup_expired.py" ]; then
    echo -e "${BLUE}🗑️  Entferne Cleanup-Python-Skript...${NC}"
    rm /opt/scandy/cleanup_expired.py
    echo -e "${GREEN}✅ Cleanup-Python-Skript entfernt${NC}"
else
    echo -e "${YELLOW}⚠️  Cleanup-Python-Skript nicht gefunden${NC}"
fi

echo
echo "========================================"
echo -e "${GREEN}✅ CRON-JOB ENTFERNUNG ABGESCHLOSSEN!${NC}"
echo "========================================"
echo
echo -e "${GREEN}🎉 Der Cron-Job für die automatische Bereinigung wurde entfernt!${NC}"
echo
echo -e "${BLUE}📋 Was wurde entfernt:${NC}"
echo "- Cron-Job für tägliche Bereinigung"
echo "- Cleanup-Skript (cleanup_expired.sh)"
echo "- Cleanup-Python-Skript (cleanup_expired.py)"
echo
echo -e "${YELLOW}⚠️  WICHTIG:${NC}"
echo "- Abgelaufene Accounts und Jobs werden nicht mehr automatisch gelöscht"
echo "- Sie können die Bereinigung manuell über die Admin-Oberfläche durchführen"

echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Cron-Jobs anzeigen: crontab -l"
echo "- Scandy-Status: systemctl status scandy"
echo "- Scandy-Logs: journalctl -u scandy -f"
echo
echo "========================================" 