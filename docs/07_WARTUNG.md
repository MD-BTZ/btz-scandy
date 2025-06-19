# Wartung und Backup

## Inhaltsverzeichnis

1. [Backup-System](#backup-system)
2. [Regelmäßige Wartung](#regelmäßige-wartung)
3. [Datenbank-Wartung](#datenbank-wartung)
4. [System-Updates](#system-updates)
5. [Überwachung](#überwachung)
6. [Notfallplan](#notfallplan)

## Backup-System

### Automatische Backups

#### Konfiguration
1. **Zeitplan**
   - Täglich um 02:00 Uhr
   - Wöchentlich am Sonntag
   - Monatlich am 1. Tag

2. **Speicherorte**
   - Lokales Backup: `/backups/`
   - Externes Backup: Konfigurierbar
   - Cloud-Backup: Optional

3. **Retention**
   - Tägliche Backups: 7 Tage
   - Wöchentliche Backups: 4 Wochen
   - Monatliche Backups: 12 Monate

#### Backup-Typen
1. **Vollständiges Backup**
   - Datenbanken
   - Uploads
   - Konfiguration
   - Logs

2. **Inkrementelles Backup**
   - Geänderte Dateien
   - Neue Datenbankeinträge
   - Aktualisierte Konfiguration

### Manuelle Backups

#### Durchführung
1. **Vorbereitung**
   ```bash
   # Backup-Skript starten
   python backup.py --type full
   ```

2. **Verifizierung**
   ```bash
   # Backup prüfen
   python backup.py --verify
   ```

3. **Export**
   ```bash
   # Backup exportieren
   python backup.py --export
   ```

#### Speicherung
1. **Lokale Speicherung**
   - Verschlüsselte Archivierung
   - Komprimierte Dateien
   - Metadaten-Dokumentation

2. **Externe Speicherung**
   - SFTP-Transfer
   - Cloud-Speicher
   - Physische Medien

## Regelmäßige Wartung

### Tägliche Aufgaben
1. **Log-Überprüfung**
   ```bash
   # Logs analysieren
   tail -f logs/app.log
   ```

2. **Speicherplatz**
   ```bash
   # Speicherplatz prüfen
   df -h
   ```

3. **Backup-Verifizierung**
   ```bash
   # Backup-Status prüfen
   python backup.py --status
   ```

### Wöchentliche Aufgaben
1. **Datenbank-Optimierung**
   ```bash
   # MongoDB-Optimierung
   mongo scandy --eval "db.runCommand('compact')"
   ```

2. **Log-Rotation**
   ```bash
   # Logs rotieren
   logrotate /etc/logrotate.d/scandy
   ```

3. **System-Überprüfung**
   ```bash
   # Systemstatus prüfen
   systemctl status scandy
   ```

### Monatliche Aufgaben
1. **Sicherheitsaudit**
   - Log-Analyse
   - Zugriffsprüfung
   - Update-Status

2. **Performance-Analyse**
   - Datenbank-Performance
   - Antwortzeiten
   - Ressourcennutzung

3. **Berichterstellung**
   - Nutzungsstatistiken
   - Fehleranalyse
   - Wartungsprotokoll

## Datenbank-Wartung

### Optimierung
1. **Indizes**
   ```bash
   # MongoDB-Indizes analysieren
   mongo scandy --eval "db.collection.getIndexes()"
   
   # MongoDB-Indizes neu aufbauen
   mongo scandy --eval "db.collection.reIndex()"
   ```

2. **Statistiken**
   ```bash
   # MongoDB-Statistiken aktualisieren
   mongo scandy --eval "db.runCommand('dbStats')"
   ```

3. **Integrität**
   ```bash
   # MongoDB-Integrität prüfen
   mongo scandy --eval "db.runCommand('dbStats')"
   ```

### Reparatur
1. **Fehlerbehebung**
   ```bash
   # MongoDB reparieren
   mongo scandy --eval "db.repairDatabase()"
   ```

2. **Wiederherstellung**
   ```bash
   # Backup einspielen
   python backup.py --restore
   ```

3. **Migration**
   ```bash
   # Schema aktualisieren
   python app/db_migration.py
   ```

### MongoDB-Wartung
```bash
# MongoDB-Status prüfen
sudo systemctl status mongod

# MongoDB-Optimierung
mongo scandy --eval "db.runCommand('compact')"

# MongoDB-Backup
mongodump --db scandy --out /backup/
```

## System-Updates

### Vorbereitung
1. **Backup**
   ```bash
   # Vollständiges Backup
   python backup.py --type full
   ```

2. **Testumgebung**
   - Staging-System
   - Test-Datenbank
   - Benutzer-Tests

3. **Zeitplan**
   - Wartungsfenster
   - Benutzerinformation
   - Rollback-Plan

### Durchführung
1. **Code-Update**
   ```bash
   # Repository aktualisieren
   git pull origin main
   ```

2. **Abhängigkeiten**
   ```bash
   # Pakete aktualisieren
   pip install -r requirements.txt --upgrade
   ```

3. **Datenbank**
   ```bash
   # Migration durchführen
   python app/db_migration.py
   ```

### Verifizierung
1. **Systemtest**
   - Funktionalität
   - Performance
   - Sicherheit

2. **Dokumentation**
   - Änderungen
   - Probleme
   - Lösungen

3. **Freigabe**
   - Benutzer informieren
   - Monitoring aktivieren
   - Support vorbereiten

## Überwachung

### System-Monitoring
1. **Ressourcen**
   - CPU-Auslastung
   - Speichernutzung
   - Festplattenplatz

2. **Performance**
   - Antwortzeiten
   - Datenbank-Performance
   - Netzwerk-Latenz

3. **Fehler**
   - Log-Analyse
   - Fehlerrate
   - Warnungen

### Benachrichtigungen
1. **Konfiguration**
   - E-Mail
   - SMS
   - Push-Benachrichtigungen

2. **Eskalation**
   - Prioritäten
   - Verantwortliche
   - Zeitpläne

## Notfallplan

### Vorbereitung
1. **Dokumentation**
   - Kontaktlisten
   - Verfahrensanweisungen
   - Zugangsdaten

2. **Tools**
   - Backup-System
   - Diagnose-Tools
   - Reparatur-Werkzeuge

3. **Ressourcen**
   - Ersatzhardware
   - Internetverbindung
   - Stromversorgung

### Durchführung
1. **Erkennung**
   - Monitoring-Alarme
   - Benutzer-Meldungen
   - System-Checks

2. **Reaktion**
   - Priorisierung
   - Team-Benachrichtigung
   - Maßnahmen-Plan

3. **Wiederherstellung**
   - Backup einspielen
   - System prüfen
   - Benutzer informieren

### Nachbereitung
1. **Analyse**
   - Ursachenforschung
   - Verbesserungsvorschläge
   - Dokumentation

2. **Prävention**
   - Maßnahmen umsetzen
   - Monitoring anpassen
   - Schulungen durchführen 