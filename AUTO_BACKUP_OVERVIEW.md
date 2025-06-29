# 🤖 Automatisches Backup-System für Scandy

## Übersicht

Das automatische Backup-System sichert Ihre Scandy-Datenbank **2x täglich** ohne manuelles Eingreifen. Es verwendet den Windows Task Scheduler (Windows) oder Cron (Linux/macOS) für zuverlässige, zeitgesteuerte Backups.

## ⚡ Schnellstart

### Windows
```batch
# Als Administrator ausführen
setup-auto-backup.bat
```

### Linux/macOS
```bash
# Im Projektverzeichnis ausführen
./setup-auto-backup.sh
```

## 📋 Features

### 🔄 Automatische Ausführung
- **2x täglich** (morgens und abends)
- **Zeitgesteuert** (06:00/18:00 oder 08:00/20:00 oder benutzerdefiniert)
- **Hintergrund-Ausführung** ohne Benutzerinteraktion

### 🛡️ Datensicherheit
- **MongoDB-Dump** mit Authentifizierung
- **Upload-Dateien** Backup
- **Statische Dateien** Backup
- **Komprimierte Archive** (ZIP/TAR)

### 🧹 Automatische Bereinigung
- **14 Backups** werden automatisch behalten (7 Tage × 2x täglich)
- **Alte Backups** werden automatisch gelöscht
- **Speicherplatz-Optimierung**

### 📊 Monitoring
- **Detaillierte Logs** in `auto_backup.log`
- **Backup-Status** überwachen
- **Fehler-Benachrichtigungen**

## 🕐 Backup-Zeiten

### Standard-Zeiten
1. **Morgens 06:00 und Abends 18:00** (Standard)
2. **Morgens 08:00 und Abends 20:00**
3. **Benutzerdefiniert** (frei wählbar)

### Warum 2x täglich?
- **Minimaler Datenverlust** bei Problemen
- **Geringe Systemlast** außerhalb der Arbeitszeiten
- **Flexibilität** für verschiedene Arbeitszeiten
- **7 Tage Rückblick** mit 14 Backups

## 📁 Backup-Struktur

```
backups/auto/
├── auto_backup_20241201_060000.zip    # Morgens Backup (06:00)
├── auto_backup_20241201_180000.zip    # Abends Backup (18:00)
├── auto_backup_20241202_060000.zip    # Nächster Tag
└── ... (14 Backups insgesamt)
```

### Backup-Inhalt
```
auto_backup_YYYYMMDD_HHMMSS.zip
├── mongodb_backup.archive    # Komplette Datenbank
├── uploads/                  # Hochgeladene Dateien
├── static/                   # Statische Dateien
└── backup_info.txt          # Backup-Metadaten
```

## 🔧 Verwaltung

### Windows
```batch
# Backup-Status anzeigen
manage-auto-backup.bat

# Manuelles Backup erstellen
auto-backup.bat
```

### Linux/macOS
```bash
# Backup-Status anzeigen
./manage-auto-backup.sh

# Manuelles Backup erstellen
./auto-backup.sh
```

### Verwaltungsoptionen
1. **Status anzeigen** - Aktuelle Backup-Konfiguration (14 Backups max.)
2. **Backups aktivieren** - Automatische Backups einrichten
3. **Backups deaktivieren** - Automatische Backups stoppen
4. **Zeiten ändern** - Backup-Zeiten anpassen (Standard: 06:00/18:00)
5. **Logs anzeigen** - Backup-Historie prüfen
6. **Manuelles Backup** - Sofortiges Backup erstellen
7. **Verzeichnis öffnen** - Backup-Dateien anzeigen

## 📊 Monitoring & Logs

### Log-Datei: `auto_backup.log`
```
Backup erfolgreich: 01.12.2024 06:00:00 - backups/auto/auto_backup_20241201_060000.zip
Backup erfolgreich: 01.12.2024 18:00:00 - backups/auto/auto_backup_20241201_180000.zip
Backup fehlgeschlagen: 02.12.2024 06:00:00 - Docker nicht verfügbar
```

### Status prüfen
```bash
# Windows
schtasks /query /tn "Scandy Auto Backup Morning"
schtasks /query /tn "Scandy Auto Backup Evening"

# Linux/macOS
crontab -l | grep "Scandy Auto Backup"
```

## 🚨 Fehlerbehebung

### Häufige Probleme

**Backup fehlgeschlagen:**
- Docker läuft nicht
- Container gestoppt
- Speicherplatz voll
- Berechtigungsprobleme

**Lösungen:**
1. **Docker starten**
2. **Container prüfen**: `docker-compose ps`
3. **Speicherplatz prüfen**
4. **Logs analysieren**: `auto_backup.log`

### Troubleshooting
```bash
# Windows
troubleshoot.bat

# Linux/macOS
./troubleshoot.sh
```

## 🔄 Wiederherstellung

### Aus automatischem Backup
```bash
# Backup extrahieren
# Windows: ZIP-Datei entpacken
# Linux/macOS: tar -xzf auto_backup_*.tar.gz

# MongoDB wiederherstellen
docker-compose exec -T scandy-mongodb mongorestore --username admin --password scandy123 --authenticationDatabase admin --archive < mongodb_backup.archive

# Dateien kopieren
# Uploads und statische Dateien in entsprechende Verzeichnisse kopieren
```

## 📈 Best Practices

### Produktionsumgebung
1. **Regelmäßige Tests** der Backup-Wiederherstellung
2. **Externe Backup-Speicherung** (Cloud, NAS)
3. **Monitoring** der Backup-Logs
4. **Backup-Integrität** prüfen (14 Backups überwachen)

### Entwicklungsumgebung
1. **Test-Backups** durchführen
2. **Wiederherstellung** üben
3. **Backup-Zeiten** an Arbeitszeiten anpassen
4. **Speicherplatz** für 14 Backups planen

## 🔐 Sicherheitsaspekte

### Datenschutz
- **Lokale Speicherung** (keine Cloud-Übertragung)
- **Verschlüsselte Archive** möglich
- **Berechtigungsbasierte** Ausführung

### Zugriffsschutz
- **System-Benutzer** für Windows Tasks
- **Cron-Berechtigungen** für Linux/macOS
- **Docker-Container** Isolation

## 📞 Support

### Bei Problemen
1. **Logs prüfen**: `auto_backup.log`
2. **Status prüfen**: `manage-auto-backup.bat/sh`
3. **Manuelles Backup** testen
4. **Troubleshooting-Script** ausführen

### Kontakt
- **Issue erstellen** mit Logs
- **Backup-Konfiguration** dokumentieren
- **Fehler-Zeitstempel** angeben

## 🎯 Vorteile

### Automatisierung
- **Keine manuellen Backups** erforderlich
- **Zuverlässige Ausführung** zu festen Zeiten
- **Minimaler Wartungsaufwand**

### Datensicherheit
- **Regelmäßige Backups** ohne Vergessen
- **Automatische Bereinigung** alter Backups (14 Backups max.)
- **Vollständige Datenbank** + Dateien
- **7 Tage Rückblick** bei Problemen

### Flexibilität
- **Anpassbare Zeiten** nach Bedarf (Standard: 06:00/18:00)
- **Einfache Verwaltung** über Scripts
- **Plattform-unabhängig** (Windows/Linux/macOS) 