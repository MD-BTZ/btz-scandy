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
   ```sql
   -- SQLite-Abfrage
   SELECT * FROM users WHERE username = 'username';
   ```

3. **Session-Problem**
   - Browser-Cache leeren
   - Cookies löschen
   - Neustart

## Datenbank-Probleme

### Datenbank beschädigt
1. **Integrität prüfen**
   ```sql
   -- SQLite-Integritätsprüfung
   PRAGMA integrity_check;
   ```

2. **Reparatur versuchen**
   ```bash
   # Backup einspielen
   python backup.py --restore --date YYYY-MM-DD
   ```

3. **Datenbank wiederherstellen**
   ```bash
   # Reparatur-Tool
   sqlite3 inventory.db ".recover"
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
   # SQLite-Performance
   sqlite3 inventory.db "PRAGMA cache_size = -2000;"
   ```

3. **Cache optimieren**
   ```python
   # Flask-Cache konfigurieren
   CACHE_TYPE = 'simple'
   CACHE_DEFAULT_TIMEOUT = 300
   ```

### Hohe CPU-Auslastung
1. **Prozesse analysieren**
   ```bash
   # Prozess-Überwachung
   ps aux | grep python
   ```

2. **Logs überprüfen**
   ```bash
   # Fehler-Logs
   grep -i error logs/app.log
   ```

3. **Optimierung**
   - Gunicorn-Worker anpassen
   - Caching aktivieren
   - Datenbank-Indizes prüfen

## Sicherheitsprobleme

### Unerlaubte Zugriffe
1. **Logs analysieren**
   ```bash
   # Zugriffs-Logs
   grep -i "failed login" logs/app.log
   ```

2. **IP-Sperrung**
   ```bash
   # Firewall-Regel
   iptables -A INPUT -s IP_ADDRESS -j DROP
   ```

3. **Passwort-Reset**
   ```bash
   # Alle Benutzer zurücksetzen
   python reset_all_passwords.py
   ```

### Datenverlust
1. **Backup prüfen**
   ```bash
   # Backup-Status
   python backup.py --status
   ```

2. **Wiederherstellung**
   ```bash
   # Letztes Backup
   python backup.py --restore --latest
   ```

3. **Forensik**
   - Log-Analyse
   - Zugriffsprotokolle
   - Änderungshistorie

## Backup-Probleme

### Backup fehlgeschlagen
1. **Fehler-Logs prüfen**
   ```bash
   # Backup-Logs
   cat logs/backup.log
   ```

2. **Speicherplatz prüfen**
   ```bash
   # Festplattenplatz
   df -h /backups
   ```

3. **Manuelles Backup**
   ```bash
   # Sofort-Backup
   python backup.py --type full --force
   ```

### Wiederherstellung fehlgeschlagen
1. **Backup-Integrität**
   ```bash
   # Backup prüfen
   python backup.py --verify
   ```

2. **Datenbank-Status**
   ```sql
   -- SQLite-Status
   .databases
   .tables
   ```

3. **Alternative Wiederherstellung**
   ```bash
   # Schrittweise Wiederherstellung
   python backup.py --restore --step-by-step
   ```

## Benutzer-Probleme

### Zugriffsprobleme
1. **Berechtigungen prüfen**
   ```sql
   -- Benutzerrechte
   SELECT * FROM user_permissions WHERE username = 'username';
   ```

2. **Session-Status**
   ```bash
   # Aktive Sessions
   python list_sessions.py
   ```

3. **Konto-Status**
   ```bash
   # Benutzer-Status
   python user_status.py username
   ```

### Funktionsprobleme
1. **Browser-Konsole**
   - JavaScript-Fehler
   - Netzwerk-Probleme
   - CORS-Fehler

2. **Server-Logs**
   ```bash
   # Anwendungs-Logs
   tail -f logs/app.log
   ```

3. **Datenbank-Abfragen**
   ```sql
   -- Transaktionen prüfen
   SELECT * FROM sqlite_master WHERE type='table';
   ```

## Eskalationspfad

### Level 1 Support
1. **Grundlegende Fehlerbehebung**
   - Dokumentation konsultieren
   - Standard-Prozeduren
   - Benutzer-Support

2. **Tools**
   - Log-Analyse
   - Basis-Diagnose
   - Backup/Reset

### Level 2 Support
1. **Technische Analyse**
   - Performance-Optimierung
   - Datenbank-Reparatur
   - System-Konfiguration

2. **Tools**
   - Debug-Modus
   - Profiling
   - Datenbank-Tools

### Level 3 Support
1. **Entwickler-Support**
   - Code-Analyse
   - Hotfix-Entwicklung
   - System-Architektur

2. **Tools**
   - Entwicklungsumgebung
   - Test-Systeme
   - Monitoring-Tools 