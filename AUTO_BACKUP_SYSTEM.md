# Automatisches Backup-System für Scandy

## Übersicht

Das automatische Backup-System für Scandy führt regelmäßige Backups der Datenbank durch, um Datenverluste zu vermeiden und eine einfache Wiederherstellung zu ermöglichen.

## Funktionen

### Automatische Backups
- **2 Backups pro Tag** zu festen Zeiten:
  - 06:00 Uhr (Morgens)
  - 18:00 Uhr (Abends)
- **Automatische Aufbewahrung**: Die letzten 10 Backups werden behalten
- **Automatische Bereinigung**: Alte Backups werden automatisch gelöscht

### Backup-Inhalt
Das System sichert alle wichtigen Datenbank-Collections:
- Werkzeuge (`tools`)
- Verbrauchsmaterialien (`consumables`)
- Mitarbeiter (`workers`)
- Ausleihen (`lendings`)
- Verbrauchsmaterial-Verwendung (`consumable_usages`)
- Einstellungen (`settings`)
- Tickets (`tickets`)
- Ticket-Nachrichten (`ticket_messages`)
- Ticket-Notizen (`ticket_notes`)

### Manuelle Backups
- Admins können jederzeit manuelle Backups erstellen
- Backup-Download und -Wiederherstellung
- Backup-Verwaltung über Admin-Interface

## Installation und Konfiguration

### 1. System-Start
Das automatische Backup-System startet automatisch beim Start der Scandy-Anwendung.

### 2. Admin-Interface
- **Zugriff**: `/admin/auto-backup`
- **Berechtigung**: Nur Administratoren
- **Funktionen**:
  - Status des Backup-Systems anzeigen
  - System starten/stoppen
  - Backup-Logs einsehen
  - Konfiguration anzeigen

### 3. Dashboard-Integration
Das Admin-Dashboard zeigt:
- Aktuellen Status des Backup-Systems
- Nächste geplante Backup-Zeit
- Schnellzugriff auf Backup-Verwaltung
- Übersicht der letzten Backups

## Technische Details

### Dateien
- **Backup-Manager**: `app/utils/backup_manager.py`
- **Auto-Backup-Scheduler**: `app/utils/auto_backup.py`
- **Admin-Routen**: `app/routes/admin.py`
- **Admin-Template**: `app/templates/admin/auto_backup.html`

### Logs
- **Log-Datei**: `logs/auto_backup.log`
- **Inhalt**: Backup-Ereignisse, Fehler, Status-Änderungen
- **Format**: `[YYYY-MM-DD HH:MM:SS] Nachricht`

### E-Mail-Benachrichtigungen
- Automatische E-Mail-Benachrichtigungen bei erfolgreichen Backups
- Empfänger: Admin-E-Mail-Adresse aus der Datenbank
- Benachrichtigung enthält Backup-Datei als Anhang

## Verwendung

### Backup-Status prüfen
1. Admin-Dashboard öffnen
2. "Automatisches Backup-System" Karte prüfen
3. Status sollte "Aktiv" anzeigen

### Manuelles Backup erstellen
1. Admin-Dashboard öffnen
2. "Backup erstellen" Button klicken
3. Backup wird sofort erstellt

### Backup herunterladen
1. Admin-Dashboard → "Alle Backups anzeigen"
2. Gewünschtes Backup auswählen
3. Download-Button klicken

### Backup wiederherstellen
1. Admin-Dashboard → "Alle Backups anzeigen"
2. Gewünschtes Backup auswählen
3. Wiederherstellen-Button klicken
4. Bestätigung geben

### Auto-Backup verwalten
1. `/admin/auto-backup` aufrufen
2. Status prüfen
3. System starten/stoppen
4. Logs einsehen

## Fehlerbehebung

### Backup-System läuft nicht
1. Prüfen Sie die Logs in `logs/auto_backup.log`
2. Stellen Sie sicher, dass die App läuft
3. Prüfen Sie die Datenbankverbindung

### Backups werden nicht erstellt
1. Prüfen Sie die Berechtigungen für das Backup-Verzeichnis
2. Stellen Sie sicher, dass genügend Speicherplatz vorhanden ist
3. Prüfen Sie die MongoDB-Verbindung

### E-Mail-Benachrichtigungen funktionieren nicht
1. Prüfen Sie die E-Mail-Konfiguration
2. Stellen Sie sicher, dass eine Admin-E-Mail-Adresse gesetzt ist
3. Prüfen Sie die SMTP-Einstellungen

## Sicherheitshinweise

### Backup-Dateien
- Backup-Dateien enthalten alle Datenbankdaten
- Sichern Sie Backup-Dateien an einem separaten Ort
- Verwenden Sie sichere Übertragungsmethoden

### Zugriffskontrolle
- Nur Administratoren können Backups verwalten
- Backup-Dateien sind nur über Admin-Interface zugänglich
- Logs enthalten keine sensiblen Daten

### Wiederherstellung
- Vor jeder Wiederherstellung wird automatisch ein Backup erstellt
- Testen Sie Wiederherstellungen in einer Testumgebung
- Dokumentieren Sie Wiederherstellungsprozesse

## Monitoring

### Automatische Überwachung
- Das System loggt alle Aktivitäten
- Fehler werden automatisch protokolliert
- Status wird im Admin-Dashboard angezeigt

### Manuelle Überwachung
- Regelmäßige Prüfung der Backup-Logs
- Kontrolle der Backup-Dateien
- Überwachung des Speicherplatzes

## Erweiterte Konfiguration

### Backup-Zeiten ändern
Die Backup-Zeiten können in `app/utils/auto_backup.py` angepasst werden:

```python
self.backup_times = [
    dt_time(6, 0),   # 06:00 Uhr
    dt_time(18, 0)   # 18:00 Uhr
]
```

### Backup-Aufbewahrung anpassen
Die Anzahl der zu behaltenden Backups kann in `app/utils/backup_manager.py` geändert werden:

```python
def _cleanup_old_backups(self, keep=10):
```

### E-Mail-Benachrichtigungen deaktivieren
E-Mail-Benachrichtigungen können in `app/utils/auto_backup.py` deaktiviert werden, indem die `_send_backup_notification` Methode angepasst wird.

## Support

Bei Problemen mit dem automatischen Backup-System:
1. Prüfen Sie die Logs in `logs/auto_backup.log`
2. Kontrollieren Sie die Datenbankverbindung
3. Stellen Sie sicher, dass alle Abhängigkeiten installiert sind
4. Prüfen Sie die Berechtigungen für Verzeichnisse und Dateien 