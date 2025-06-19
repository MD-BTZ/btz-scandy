# Fehlerbehebung

## Inhaltsverzeichnis

1. [Häufige Probleme](#häufige-probleme)
2. [Datenbank-Probleme](#datenbank-probleme)
3. [Performance-Probleme](#performance-probleme)
4. [Sicherheitsprobleme](#sicherheitsprobleme)
5. [Backup-Probleme](#backup-probleme)
6. [Benutzer-Probleme](#benutzer-probleme)

## Häufige Probleme

### Anwendung startet nicht
1. **Überprüfen Sie die Logs**
   ```bash
   tail -f logs/app.log
   ```

2. **Port-Konflikte**
   ```bash
   # Verfügbare Ports prüfen
   netstat -tulpn | grep 5000
   ```

3. **Abhängigkeiten**
   ```bash
   # Pakete überprüfen
   pip list
   ```

### Barcode-Scanner funktioniert nicht
1. **Hardware prüfen**
   - USB-Verbindung
   - Treiber-Installation
   - Geräte-Erkennung

2. **Software-Konfiguration**
   ```bash
   # Scanner-Treiber prüfen
   lsusb
   ```

3. **Browser-Einstellungen**
   - Kamera-Berechtigungen
   - HTTPS erforderlich
   - Popup-Blocker

### Benutzer kann sich nicht anmelden
1. **Passwort zurücksetzen**
   ```bash
   # Admin-Tool verwenden
   python reset_password.py <username>
   ```

2. **Konto-Status prüfen**
   ```bash
   # MongoDB-Abfrage
   mongo scandy --eval "db.users.findOne({username: 'username'})"
   ```

3. **Session-Problem**
   - Browser-Cache leeren
   - Cookies löschen
   - Neustart

## Datenbank-Probleme

### MongoDB-Verbindungsfehler
```bash
# MongoDB-Status prüfen
sudo systemctl status mongod

# MongoDB starten
sudo systemctl start mongod

# MongoDB-Logs prüfen
sudo journalctl -u mongod -f
```

### MongoDB-Integritätsprüfung
```bash
# MongoDB-Datenbank prüfen
mongo scandy --eval "db.runCommand('dbStats')"

# Collections auflisten
mongo scandy --eval "db.getCollectionNames()"
```

### MongoDB-Performance
```bash
# MongoDB-Performance
mongo scandy --eval "db.runCommand('collStats', {scale: 1024})"
```

### MongoDB-Backup und Wiederherstellung
```bash
# Backup erstellen
mongodump --db scandy --out /backup/

# Wiederherstellung
mongorestore --db scandy /backup/scandy/
```

### Datenbank beschädigt
1. **Integrität prüfen**
   ```bash
   # MongoDB-Integritätsprüfung
   mongo scandy --eval "db.runCommand('dbStats')"
   ```

2. **Reparatur versuchen**
   ```bash
   # Backup einspielen
   python backup.py --restore --date YYYY-MM-DD
   ```

3. **Datenbank wiederherstellen**
   ```bash
   # Reparatur-Tool
   mongo scandy --eval "db.repairDatabase()"
   ```

### Performance-Probleme
1. **Indizes optimieren**
   ```sql
   -- Indizes analysieren
   ANALYZE;
   
   -- Indizes neu aufbauen
   REINDEX;
   ```

2. **VACUUM ausführen**
   ```sql
   -- Datenbank komprimieren
   VACUUM;
   ```

3. **Abfragen optimieren**
   ```sql
   -- Query-Plan analysieren
   EXPLAIN QUERY PLAN SELECT * FROM table;
   ```

## Performance-Probleme

### Langsame Antwortzeiten
1. **Server-Last prüfen**
   ```bash
   # System-Monitoring
   top
   htop
   ```

2. **Datenbank-Performance**
   ```bash
   # MongoDB-Performance
   mongo scandy --eval "db.runCommand('collStats', {scale: 1024})"
   ```

3. **Cache optimieren**
   ```