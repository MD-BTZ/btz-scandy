#!/bin/bash

# Live-Log-Überwachung für Scandy
# Überwacht Fehler und Backup-Aktivitäten in Echtzeit

echo "=== Scandy Live-Log-Überwachung ==="
echo "Drücken Sie Ctrl+C zum Beenden"
echo ""

# Funktion zum Anzeigen der aktuellen Zeit
show_time() {
    echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] ========================================="
}

# Live-Überwachung der Fehler-Logs
echo "🔍 Überwache Fehler-Logs..."
tail -f logs/errors.log | while read line; do
    if echo "$line" | grep -q -E "(ERROR|CRITICAL|FATAL)"; then
        show_time
        echo "❌ FEHLER: $line"
    elif echo "$line" | grep -q -E "(backup|Backup|RESTORE|restore)"; then
        show_time
        echo "💾 BACKUP: $line"
    fi
done &

# Live-Überwachung der Backup-Logs
echo "🔍 Überwache Backup-Logs..."
tail -f logs/auto_backup.log | while read line; do
    show_time
    echo "💾 BACKUP: $line"
done &

# Live-Überwachung der Benutzer-Aktionen
echo "🔍 Überwache Benutzer-Aktionen..."
tail -f logs/user_actions.log | while read line; do
    if echo "$line" | grep -q -E "(backup|Backup|upload|Upload|restore|Restore)"; then
        show_time
        echo "👤 USER: $line"
    fi
done &

# Warte auf Benutzer-Unterbrechung
echo "✅ Überwachung gestartet. Drücken Sie Ctrl+C zum Beenden."
wait 