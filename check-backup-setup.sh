#!/bin/bash

echo "🔍 Prüfe automatische Backup-Einrichtung"
echo "========================================"

# Prüfe ob wir im richtigen Verzeichnis sind
if [[ ! -f "docker-compose.yml" ]]; then
    echo "❌ Keine Scandy-Installation gefunden!"
    echo "Führen Sie zuerst install.sh aus."
    exit 1
fi

echo "✅ Scandy-Installation gefunden"

# Prüfe ob automatische Backups bereits eingerichtet sind
if crontab -l 2>/dev/null | grep -q "Scandy Auto Backup"; then
    echo "✅ Automatische Backups sind eingerichtet!"
    echo ""
    echo "📋 Backup-Status:"
    crontab -l | grep "Scandy Auto Backup"
    echo ""
    echo "💡 Backup-Verwaltung: ./manage-auto-backup.sh"
else
    echo "❌ Automatische Backups nicht eingerichtet"
    echo ""
    echo "🔄 Möchten Sie automatische Backups jetzt einrichten?"
    echo "- Morgens 06:00 und Abends 18:00"
    echo "- 14 Backups werden automatisch behalten (7 Tage)"
    echo ""
    read -p "Automatische Backups einrichten? (j/n): " setup_backup
    if [[ $setup_backup =~ ^[Jj]$ ]]; then
        echo ""
        echo "🔄 Richte automatische Backups ein..."
        ./setup-auto-backup.sh
    else
        echo ""
        echo "💡 Sie können Backups später einrichten mit:"
        echo "   ./setup-auto-backup.sh"
    fi
fi

echo "" 