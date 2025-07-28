#!/bin/bash

# Backup-Fehler Diagnose-Skript
# Überwacht Serverlogs und identifiziert Backup-bezogene Probleme

echo "=== Scandy Backup-Fehler Diagnose ==="
echo "Datum: $(date)"
echo ""

# 1. Aktuelle Fehler in den Logs
echo "📋 AKTUELLE FEHLER IN DEN LOGS:"
echo "--------------------------------"
tail -20 logs/errors.log | grep -E "(backup|Backup|RESTORE|restore|upload|Upload)" || echo "Keine Backup-spezifischen Fehler gefunden"

echo ""
echo "📋 ALLE AKTUELLEN FEHLER:"
echo "-------------------------"
tail -10 logs/errors.log

echo ""
echo "📋 BACKUP-LOGS:"
echo "---------------"
tail -10 logs/auto_backup.log

echo ""
echo "📋 BENUTZER-AKTIONEN (letzte 5):"
echo "---------------------------------"
tail -5 logs/user_actions.log

echo ""
echo "🔍 BACKUP-DATEIEN PRÜFEN:"
echo "-------------------------"
ls -la backups/ | head -10

echo ""
echo "🔍 MONGODB-STATUS:"
echo "------------------"
if command -v mongosh &> /dev/null; then
    echo "MongoDB ist installiert"
    mongosh --eval "db.runCommand('ping')" --quiet || echo "MongoDB-Verbindung fehlgeschlagen"
else
    echo "MongoDB ist nicht installiert oder nicht im PATH"
fi

echo ""
echo "🔍 DISK-SPEICHER:"
echo "----------------"
df -h | grep -E "(/$|/home)"

echo ""
echo "🔍 PROZESS-STATUS:"
echo "------------------"
ps aux | grep -E "(python|flask|gunicorn)" | grep -v grep || echo "Keine Python-Prozesse gefunden"

echo ""
echo "=== DIAGNOSE ABGESCHLOSSEN ==="
echo ""
echo "💡 EMPFOHLENE AKTIONEN:"
echo "1. Prüfen Sie die MongoDB-Verbindung"
echo "2. Überprüfen Sie die Backup-Berechtigungen"
echo "3. Testen Sie ein manuelles Backup"
echo "4. Prüfen Sie die Disk-Speicherkapazität"
echo ""
echo "Für weitere Hilfe: tail -f logs/errors.log" 