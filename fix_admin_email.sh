#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Fix: Admin-E-Mail-Problem${NC}"
echo "========================================"

# Prüfe ob wir im richtigen Verzeichnis sind
if [ ! -f "app/routes/admin.py" ]; then
    echo -e "${RED}❌ Bitte führen Sie dieses Skript im Scandy-Hauptverzeichnis aus!${NC}"
    exit 1
fi

echo -e "${YELLOW}🔍 Prüfe Admin-Benutzer und E-Mail-Konfiguration...${NC}"

# Finde alle Instance-Verzeichnisse
instances=()
if [ -f ".env" ]; then
    instances+=("Haupt-Instanz (.)")
fi

for dir in */; do
    if [ -f "$dir/docker-compose.yml" ]; then
        instances+=("$dir")
    fi
done

echo -e "${GREEN}✅ Gefundene Instanzen:${NC}"
for instance in "${instances[@]}"; do
    echo "  - $instance"
done

echo ""
echo -e "${BLUE}🔍 Prüfe Admin-Benutzer in allen Instanzen...${NC}"

# Prüfe Admin-Benutzer in allen Instanzen
for instance in "${instances[@]}"; do
    if [ "$instance" = "Haupt-Instanz (.)" ]; then
        echo -e "${YELLOW}📊 Haupt-Instanz Admin-Benutzer:${NC}"
        if docker ps | grep -q "scandy-mongodb-scandy"; then
            echo "  📋 Admin-Benutzer:"
            docker exec scandy-mongodb-scandy mongosh --eval "db.users.find({role: 'admin'}, {username: 1, email: 1, role: 1, is_active: 1}).pretty()" 2>/dev/null || echo "    Fehler beim Abfragen der Admin-Benutzer"
        else
            echo "  ❌ MongoDB Container läuft nicht"
        fi
    else
        instance_dir="${instance%/}"
        echo -e "${YELLOW}📊 $instance_dir Admin-Benutzer:${NC}"
        container_name="scandy-mongodb-$instance_dir"
        if docker ps | grep -q "$container_name"; then
            echo "  📋 Admin-Benutzer:"
            docker exec "$container_name" mongosh --eval "db.users.find({role: 'admin'}, {username: 1, email: 1, role: 1, is_active: 1}).pretty()" 2>/dev/null || echo "    Fehler beim Abfragen der Admin-Benutzer"
        else
            echo "  ❌ MongoDB Container läuft nicht"
        fi
    fi
done

echo ""
echo -e "${BLUE}🔧 Lösungsvorschläge:${NC}"
echo ""
echo -e "${YELLOW}1. Admin-E-Mail über Profil-Seite setzen:${NC}"
echo "   - Gehen Sie zu: http://localhost:5000/auth/profile"
echo "   - Geben Sie eine E-Mail-Adresse ein"
echo "   - Klicken Sie auf 'Speichern'"
echo ""
echo -e "${YELLOW}2. Admin-E-Mail über Admin-Benutzerverwaltung setzen:${NC}"
echo "   - Gehen Sie zu: http://localhost:5000/admin/manage_users"
echo "   - Klicken Sie auf den Admin-Benutzer zum Bearbeiten"
echo "   - Geben Sie eine E-Mail-Adresse ein"
echo "   - Klicken Sie auf 'Speichern'"
echo ""
echo -e "${YELLOW}3. E-Mail-Einstellungen konfigurieren:${NC}"
echo "   - Gehen Sie zu: http://localhost:5000/admin/email_settings"
echo "   - Konfigurieren Sie SMTP-Einstellungen"
echo "   - Testen Sie die E-Mail-Konfiguration"
echo ""
echo -e "${YELLOW}4. Manueller Fix über Datenbank:${NC}"
echo "   # Haupt-Instanz"
echo "   docker exec scandy-mongodb-scandy mongosh --eval \"db.users.updateOne({role: 'admin'}, {\$set: {email: 'admin@example.com'}})\""
echo ""
echo "   # Verwaltung-Instanz"
echo "   docker exec scandy-mongodb-verwaltung mongosh --eval \"db.users.updateOne({role: 'admin'}, {\$set: {email: 'admin@example.com'}})\""
echo ""
echo -e "${GREEN}✅ Fix-Skript abgeschlossen!${NC}"
echo ""
echo -e "${YELLOW}💡 Nächste Schritte:${NC}"
echo "1. Setzen Sie eine E-Mail-Adresse für den Admin-Benutzer"
echo "2. Konfigurieren Sie die E-Mail-Einstellungen"
echo "3. Testen Sie die E-Mail-Funktionalität" 