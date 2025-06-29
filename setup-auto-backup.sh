#!/bin/bash

echo "🔄 Einrichtung automatischer Scandy Backups"
echo "==========================================="

# Prüfe ob wir im richtigen Verzeichnis sind
if [[ ! -f "docker-compose.yml" ]]; then
    echo "❌ Keine Scandy-Installation gefunden!"
    echo "Führen Sie zuerst install.sh aus."
    exit 1
fi

echo "✅ Scandy-Installation gefunden"

# Erstelle vollständigen Pfad zum auto-backup.sh
SCRIPT_PATH="$(pwd)/auto-backup.sh"
echo "📁 Script-Pfad: $SCRIPT_PATH"

# Mache Script ausführbar
chmod +x "$SCRIPT_PATH"

echo ""
echo "📋 Backup-Zeitplan konfigurieren:"
echo ""
echo "Verfügbare Optionen:"
echo "1. Morgens 06:00 und Abends 18:00 (empfohlen)"
echo "2. Morgens 08:00 und Abends 20:00"
echo "3. Benutzerdefiniert"
echo ""
read -p "Wählen Sie eine Option (1-3): " schedule_choice

case $schedule_choice in
    1)
        MORNING_TIME="06:00"
        EVENING_TIME="18:00"
        MORNING_CRON="0 6 * * *"
        EVENING_CRON="0 18 * * *"
        ;;
    2)
        MORNING_TIME="08:00"
        EVENING_TIME="20:00"
        MORNING_CRON="0 8 * * *"
        EVENING_CRON="0 20 * * *"
        ;;
    3)
        echo ""
        read -p "Morgens Backup-Zeit (HH:MM): " MORNING_TIME
        read -p "Abends Backup-Zeit (HH:MM): " EVENING_TIME
        
        # Konvertiere HH:MM zu Cron-Format
        MORNING_HOUR=$(echo $MORNING_TIME | cut -d: -f1)
        MORNING_MINUTE=$(echo $MORNING_TIME | cut -d: -f2)
        EVENING_HOUR=$(echo $EVENING_TIME | cut -d: -f1)
        EVENING_MINUTE=$(echo $EVENING_TIME | cut -d: -f2)
        
        MORNING_CRON="$MORNING_MINUTE $MORNING_HOUR * * *"
        EVENING_CRON="$EVENING_MINUTE $EVENING_HOUR * * *"
        ;;
    *)
        echo "Ungültige Auswahl. Verwende Standard-Zeiten."
        MORNING_TIME="06:00"
        EVENING_TIME="18:00"
        MORNING_CRON="0 6 * * *"
        EVENING_CRON="0 18 * * *"
        ;;
esac

echo ""
echo "⏰ Backup-Zeiten:"
echo "- Morgens: $MORNING_TIME"
echo "- Abends: $EVENING_TIME"

echo ""
echo "🔄 Erstelle Cron-Jobs..."

# Erstelle temporäre Cron-Datei
TEMP_CRON=$(mktemp)

# Hole bestehende Cron-Jobs
crontab -l 2>/dev/null | grep -v "Scandy Auto Backup" > "$TEMP_CRON"

# Füge neue Cron-Jobs hinzu
echo "# Scandy Auto Backup - Morgens $MORNING_TIME" >> "$TEMP_CRON"
echo "$MORNING_CRON $SCRIPT_PATH >> $(pwd)/auto_backup.log 2>&1" >> "$TEMP_CRON"
echo "# Scandy Auto Backup - Abends $EVENING_TIME" >> "$TEMP_CRON"
echo "$EVENING_CRON $SCRIPT_PATH >> $(pwd)/auto_backup.log 2>&1" >> "$TEMP_CRON"

# Installiere neue Cron-Jobs
if crontab "$TEMP_CRON"; then
    echo "✅ Cron-Jobs erfolgreich erstellt!"
else
    echo "❌ Fehler beim Erstellen der Cron-Jobs!"
    rm -f "$TEMP_CRON"
    exit 1
fi

# Lösche temporäre Datei
rm -f "$TEMP_CRON"

echo ""
echo "📋 Cron-Job-Status prüfen..."
crontab -l | grep "Scandy Auto Backup"

echo ""
echo "📁 Backup-Verzeichnis erstellen..."
mkdir -p "backups/auto"

echo ""
echo "📝 Erstelle Konfigurationsdatei..."
cat > auto_backup_config.txt << EOF
Automatische Backups konfiguriert am: $(date)
Projekt: $(pwd)
Script-Pfad: $SCRIPT_PATH
Morgens: $MORNING_TIME
Abends: $EVENING_TIME
Cron-Jobs:
- Morgens: $MORNING_CRON
- Abends: $EVENING_CRON
EOF

echo ""
echo "✅ Automatische Backups erfolgreich eingerichtet!"
echo ""
echo "📋 Zusammenfassung:"
echo "- Morgens Backup: $MORNING_TIME"
echo "- Abends Backup: $EVENING_TIME"
echo "- Backup-Verzeichnis: backups/auto"
echo "- Log-Datei: auto_backup.log"
echo "- Konfiguration: auto_backup_config.txt"
echo ""
echo "💡 Tipps:"
echo "- Backups werden automatisch alle 7 Tage bereinigt (14 Backups behalten)"
echo "- Prüfen Sie auto_backup.log für Backup-Status"
echo "- Bei Problemen: ./troubleshoot.sh ausführen"
echo "- Cron-Jobs anzeigen: crontab -l"
echo ""

# Teste das Backup-Script
echo "🧪 Teste Backup-Script..."
if "$SCRIPT_PATH" > /dev/null 2>&1; then
    echo "✅ Backup-Script funktioniert korrekt!"
else
    echo "⚠️  Backup-Script-Test fehlgeschlagen. Prüfen Sie die Logs."
fi

echo "" 