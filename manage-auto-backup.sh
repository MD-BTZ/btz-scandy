#!/bin/bash

echo "🔧 Automatische Scandy Backups verwalten"
echo "========================================"

# Prüfe ob wir im richtigen Verzeichnis sind
if [[ ! -f "docker-compose.yml" ]]; then
    echo "❌ Keine Scandy-Installation gefunden!"
    echo "Führen Sie zuerst install.sh aus."
    exit 1
fi

echo "✅ Scandy-Installation gefunden"

echo ""
echo "📋 Verfügbare Aktionen:"
echo "1. Status der automatischen Backups anzeigen"
echo "2. Automatische Backups aktivieren/einrichten"
echo "3. Automatische Backups deaktivieren"
echo "4. Backup-Zeiten ändern"
echo "5. Backup-Logs anzeigen"
echo "6. Manuelles Backup erstellen"
echo "7. Backup-Verzeichnis öffnen"
echo "8. Beenden"
echo ""
read -p "Wählen Sie eine Aktion (1-8): " action

case $action in
    1)
        echo ""
        echo "📊 Status der automatischen Backups:"
        echo ""
        echo "Cron-Jobs:"
        if crontab -l 2>/dev/null | grep -q "Scandy Auto Backup"; then
            crontab -l | grep "Scandy Auto Backup"
        else
            echo "❌ Keine Cron-Jobs gefunden"
        fi
        
        # Prüfe Konfigurationsdatei
        if [[ -f "auto_backup_config.txt" ]]; then
            echo ""
            echo "📝 Konfiguration:"
            cat auto_backup_config.txt
        else
            echo ""
            echo "❌ Keine Konfigurationsdatei gefunden"
        fi
        
        # Prüfe Backup-Verzeichnis
        if [[ -d "backups/auto" ]]; then
            echo ""
            echo "📁 Backup-Verzeichnis: backups/auto"
            echo "Anzahl Backups: $(ls -1 backups/auto/auto_backup_*.tar.gz 2>/dev/null | wc -l)"
            echo "(Maximal 14 Backups - 7 Tage × 2x täglich)"
        else
            echo ""
            echo "❌ Backup-Verzeichnis nicht gefunden"
        fi
        
        # Prüfe Log-Datei
        if [[ -f "auto_backup.log" ]]; then
            echo ""
            echo "📋 Letzte Log-Einträge:"
            tail -5 auto_backup.log
        else
            echo ""
            echo "❌ Keine Log-Datei gefunden"
        fi
        ;;
    2)
        echo ""
        echo "🔄 Einrichtung automatischer Backups..."
        ./setup-auto-backup.sh
        ;;
    3)
        echo ""
        echo "⚠️  Automatische Backups deaktivieren..."
        echo ""
        read -p "Sind Sie sicher? (j/n): " confirm
        if [[ $confirm =~ ^[Jj]$ ]]; then
            echo "Lösche Cron-Jobs..."
            crontab -l 2>/dev/null | grep -v "Scandy Auto Backup" | crontab -
            echo "✅ Automatische Backups deaktiviert!"
            echo ""
            echo "💡 Hinweis: Bestehende Backups bleiben erhalten."
        fi
        ;;
    4)
        echo ""
        echo "⏰ Backup-Zeiten ändern..."
        echo ""
        echo "Aktuelle Cron-Jobs:"
        crontab -l 2>/dev/null | grep "Scandy Auto Backup"
        echo ""
        echo "Verfügbare Optionen:"
        echo "1. Morgens 06:00 und Abends 18:00"
        echo "2. Morgens 08:00 und Abends 20:00"
        echo "3. Benutzerdefiniert"
        echo ""
        read -p "Wählen Sie eine Option (1-3): " time_choice
        
        case $time_choice in
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
                echo "Ungültige Auswahl."
                exit 1
                ;;
        esac
        
        echo ""
        echo "🔄 Aktualisiere Cron-Jobs..."
        
        # Erstelle temporäre Cron-Datei
        TEMP_CRON=$(mktemp)
        
        # Hole bestehende Cron-Jobs
        crontab -l 2>/dev/null | grep -v "Scandy Auto Backup" > "$TEMP_CRON"
        
        # Füge neue Cron-Jobs hinzu
        SCRIPT_PATH="$(pwd)/auto-backup.sh"
        echo "# Scandy Auto Backup - Morgens $MORNING_TIME" >> "$TEMP_CRON"
        echo "$MORNING_CRON $SCRIPT_PATH >> $(pwd)/auto_backup.log 2>&1" >> "$TEMP_CRON"
        echo "# Scandy Auto Backup - Abends $EVENING_TIME" >> "$TEMP_CRON"
        echo "$EVENING_CRON $SCRIPT_PATH >> $(pwd)/auto_backup.log 2>&1" >> "$TEMP_CRON"
        
        # Installiere neue Cron-Jobs
        if crontab "$TEMP_CRON"; then
            echo "✅ Backup-Zeiten aktualisiert!"
            echo "- Morgens: $MORNING_TIME"
            echo "- Abends: $EVENING_TIME"
        else
            echo "❌ Fehler beim Aktualisieren der Cron-Jobs!"
        fi
        
        # Lösche temporäre Datei
        rm -f "$TEMP_CRON"
        ;;
    5)
        echo ""
        echo "📋 Backup-Logs anzeigen..."
        if [[ -f "auto_backup.log" ]]; then
            echo ""
            echo "Letzte 20 Log-Einträge:"
            echo "======================="
            tail -20 auto_backup.log
            echo ""
            read -p "Vollständige Log-Datei öffnen? (j/n): " open_log
            if [[ $open_log =~ ^[Jj]$ ]]; then
                if command -v nano >/dev/null 2>&1; then
                    nano auto_backup.log
                elif command -v vim >/dev/null 2>&1; then
                    vim auto_backup.log
                else
                    cat auto_backup.log
                fi
            fi
        else
            echo "❌ Keine Log-Datei gefunden!"
        fi
        ;;
    6)
        echo ""
        echo "📦 Manuelles Backup erstellen..."
        echo ""
        read -p "Soll ein manuelles Backup erstellt werden? (j/n): " confirm
        if [[ $confirm =~ ^[Jj]$ ]]; then
            echo "Führe manuelles Backup aus..."
            ./auto-backup.sh
        fi
        ;;
    7)
        echo ""
        echo "📁 Backup-Verzeichnis öffnen..."
        if [[ -d "backups/auto" ]]; then
            if command -v xdg-open >/dev/null 2>&1; then
                xdg-open "backups/auto"
            elif command -v open >/dev/null 2>&1; then
                open "backups/auto"
            else
                echo "Verzeichnis: $(pwd)/backups/auto"
                ls -la "backups/auto"
            fi
        else
            echo "❌ Backup-Verzeichnis nicht gefunden!"
        fi
        ;;
    8)
        echo "Beenden..."
        exit 0
        ;;
    *)
        echo "Ungültige Auswahl."
        ;;
esac

echo "" 