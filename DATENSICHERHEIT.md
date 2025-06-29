# 🔒 Datensicherheit in Scandy

## Übersicht

Scandy implementiert umfassende Datensicherheitsmaßnahmen, um Ihre Daten bei Installationen und Updates zu schützen.

## ⚠️ Wichtige Sicherheitshinweise

### Bei Neuinstallation

**Automatische Erkennung:**
- Das System erkennt automatisch bestehende Installationen
- Sie erhalten eine detaillierte Warnung mit allen gefundenen Daten
- Keine versehentliche Datenüberschreibung möglich

**Sicherheitsoptionen:**
1. **Installation abbrechen** (empfohlen)
   - Bestehende Daten bleiben unverändert
   - Keine Risiken für Ihre Daten

2. **Backup erstellen und neu installieren**
   - Automatisches Backup aller Daten
   - Sichere Neuinstallation mit Backup-Schutz

3. **Bestehende Daten überschreiben** (nur für Experten!)
   - Doppelte Bestätigung erforderlich
   - Nur für bewusste Datenlöschung

### Datenpersistenz

**MongoDB-Daten:**
- Werden in Docker-Volumes gespeichert
- Bleiben bei Container-Updates erhalten
- Automatische Persistenz ohne manuelle Konfiguration

**Upload-Dateien:**
- Werden in lokalen Verzeichnissen gespeichert
- Unabhängig von Container-Lebenszyklus
- Direkter Zugriff auf Dateisystem

**Backup-Dateien:**
- Automatische Erstellung vor kritischen Operationen
- Zeitstempel-basierte Namensgebung
- Komprimierte Archive für effiziente Speicherung

## 📦 Backup-System

### Automatische Backups

**Trigger:**
- Vor jedem sicheren Update
- Bei Neuinstallation mit Backup-Option
- Manuell über Backup-Scripts

**Backup-Inhalt:**
```
scandy_backup_YYYYMMDD_HHMMSS.zip
├── mongodb_backup.archive    # Komplette Datenbank
├── uploads/                  # Hochgeladene Dateien
├── backups/                  # Bestehende Backups
├── logs/                     # Log-Dateien
├── static/                   # Statische Dateien
└── backup_info.txt          # Backup-Metadaten
```

### Manuelle Backups

**Windows:**
```batch
backup.bat
```

**Linux/macOS:**
```bash
./backup.sh
```

**Features:**
- MongoDB-Dump mit Authentifizierung
- Datei-Kompression (ZIP/TAR)
- Größenanzeige
- Detaillierte Backup-Informationen

## 🔄 Update-Sicherheit

### Sichere Updates

**Automatische Sicherheitsmaßnahmen:**
1. **Backup vor Update**
   - Automatische Erstellung vor jedem Update
   - Rollback-Möglichkeit bei Problemen

2. **Container-spezifische Updates**
   - Nur App-Container wird aktualisiert
   - Datenbank-Container bleibt unverändert
   - Minimale Ausfallzeiten

3. **Health-Checks**
   - Automatische Überprüfung nach Updates
   - Benachrichtigung bei Problemen

### Update-Optionen

**Sicheres Update (empfohlen):**
```bash
# Windows
safe-update.bat

# Linux/macOS
./safe-update.sh
```
- Backup + Update
- Nur App-Container
- Maximale Sicherheit

**Schnelles Update:**
- Nur App-Container
- Kein Backup (nur bei geringen Änderungen)
- Minimale Ausfallzeit

**Vollständiges Update:**
- Alle Container
- Nur für größere Updates
- Doppelte Bestätigung erforderlich

## 🛡️ Schutzmechanismen

### Installation-Schutz

**Erkennung bestehender Installationen:**
- Automatische Suche nach `*_project` Verzeichnissen
- Prüfung auf `docker-compose.yml`
- Erkennung von Datenverzeichnissen

**Sicherheitsabfragen:**
- Detaillierte Auflistung gefundener Daten
- Klare Optionen mit Erklärungen
- Doppelte Bestätigung bei gefährlichen Operationen

### Datenbank-Schutz

**MongoDB-Sicherheit:**
- Authentifizierung erforderlich
- Backup mit Credentials
- Volume-Persistenz

**Container-Sicherheit:**
- Health-Checks für alle Services
- Automatische Neustarts bei Fehlern
- Log-Rotation für Speichereffizienz

## 📋 Best Practices

### Vor Updates

1. **Backup erstellen**
   ```bash
   # Windows
   backup.bat
   
   # Linux/macOS
   ./backup.sh
   ```

2. **System-Status prüfen**
   ```bash
   docker-compose ps
   ```

3. **Speicherplatz prüfen**
   - Mindestens 2GB freier Speicher
   - Backup-Speicherplatz berücksichtigen

### Nach Updates

1. **Anwendung testen**
   - http://localhost:5000 aufrufen
   - Funktionen testen

2. **Logs prüfen**
   ```bash
   docker-compose logs
   ```

3. **Backup-Integrität prüfen**
   - Backup-Datei-Größe prüfen
   - Backup-Info lesen

### Regelmäßige Wartung

1. **Wöchentliche Backups**
   - Automatische Backups planen
   - Backup-Integrität testen

2. **Log-Rotation**
   - Alte Logs archivieren
   - Speicherplatz überwachen

3. **System-Updates**
   - Regelmäßige Updates durchführen
   - Immer sicheres Update verwenden

## 🚨 Notfall-Wiederherstellung

### Backup-Wiederherstellung

**ZIP-Backup (Windows):**
1. Backup-Datei extrahieren
2. MongoDB-Restore durchführen
3. Dateien in entsprechende Verzeichnisse kopieren

**TAR-Backup (Linux/macOS):**
1. Backup-Datei entpacken
2. MongoDB-Restore durchführen
3. Dateien in entsprechende Verzeichnisse kopieren

### MongoDB-Restore

```bash
# Aus Backup-Archiv
docker-compose exec -T scandy-mongodb mongorestore --username admin --password scandy123 --authenticationDatabase admin --archive < mongodb_backup.archive
```

### Vollständige Wiederherstellung

1. **Neue Installation**
   - Install-Script ausführen
   - Installation abbrechen wenn Daten gefunden

2. **Backup wiederherstellen**
   - MongoDB-Restore
   - Dateien kopieren

3. **System testen**
   - Anwendung aufrufen
   - Daten-Integrität prüfen

## 📞 Support bei Datenproblemen

### Häufige Probleme

**Backup fehlgeschlagen:**
- Docker-Status prüfen
- Speicherplatz prüfen
- Manuelles Backup versuchen

**Update-Probleme:**
- Logs prüfen: `docker-compose logs`
- Troubleshooting-Script ausführen
- Backup zurückspielen

**Datenverlust:**
- Sofort alle Operationen stoppen
- Backup-Integrität prüfen
- Professionelle Hilfe suchen

### Kontakt

Bei Datenproblemen:
1. **Sofort Backup erstellen** (falls möglich)
2. **Logs sammeln**: `docker-compose logs > problem.log`
3. **Problem dokumentieren** mit Screenshots
4. **Issue erstellen** mit allen Details

## 🔐 Sicherheitsempfehlungen

### Produktionsumgebung

1. **Regelmäßige Backups**
   - Tägliche automatische Backups
   - Externe Backup-Speicherung

2. **Monitoring**
   - Container-Status überwachen
   - Speicherplatz überwachen

3. **Updates**
   - Nur sicheres Update verwenden
   - Updates in Testumgebung prüfen

### Entwicklungsumgebung

1. **Test-Backups**
   - Backup-Funktionalität testen
   - Wiederherstellung üben

2. **Sichere Updates**
   - Immer Backup vor Update
   - Rollback-Plan haben

3. **Dokumentation**
   - Änderungen dokumentieren
   - Backup-Strategien dokumentieren 