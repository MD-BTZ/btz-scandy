# Scandy Gesamtmanual

---

## 1. Verwendung (Bedienung & Administration)

### 1.1 Systemvoraussetzungen und Architekturüberblick
- Betriebssystem: Windows 10/11, macOS, Linux
- Docker Desktop (Windows/macOS) oder Docker Engine (Linux)
- Git (zum Klonen des Repositories)
- Empfohlene Hardware: 2 CPU-Kerne, 2 GB RAM, 2 GB freier Speicherplatz
- Architektur: Webanwendung (Flask), MongoDB als Datenbank, Docker-Containerisierung

### 1.2 Installation und Erstinbetriebnahme
- Repository mit `git clone` klonen
- Im Projektverzeichnis Installationsskript ausführen:
  - Windows: `install.bat`
  - Linux/macOS: `install.sh`
- `.env`-Datei wird automatisch erstellt, Werte anpassen (insbesondere Passwörter und SMTP)
- Nach erfolgreicher Installation ist die Web-App unter http://localhost:5000 erreichbar, Mongo Express unter http://localhost:8081
- Admin Account, Labelnamen und Ersteinrichtung der Kategorien erfolgt nach der Erstinstallation über Setup-Routine

### 1.3 Anmeldung, Benutzerrollen und Rechte
- Rollen: Admin, Mitarbeiter, Anwender, Teilnehmer
- Rechte und Zugriffsbereiche siehe `berechtigungen_uebersicht.md`
- Anmeldung über `/auth/login`, Passwort-Reset über `/admin/reset_password`
- Benutzerverwaltung über Admin-Oberfläche

### 1.4 Navigation und Aufbau der Weboberfläche
- Hauptnavigation: Dashboard, Werkzeuge, Verbrauchsgüter, Tickets, Mitarbeiter, Berichte, Admin
- Kontextabhängige Navigation je nach Rolle
- Such- und Filterfunktionen in Listenansichten
- Detailansichten für alle Objekte (Werkzeug, Verbrauchsgut, Ticket, Benutzer)

### 1.5 Werkzeuge
- Anlegen: Über Formular, Barcode kann vergeben werden
- Bearbeiten: Über Detailansicht, Felder editierbar
- Ausleihen: Manuell oder per QuickScan, Zuordnung zu Mitarbeiter
- Rückgabe: Über Rückgabe-Funktion, Status wird aktualisiert
- Status: Verfügbar, ausgeliehen, defekt, in Wartung
- Historie: Alle Ausleih- und Rückgabevorgänge werden protokolliert

### 1.6 Verbrauchsgüter
- Anlegen: Über Formular
- Bearbeiten: Über Detailansicht
- Verbrauch buchen: Über Verbrauchsformular, Bestandsführung automatisch
- Prognose: Verbrauchsprognose und Mindestbestand-Warnungen
- Bestandshistorie: Alle Buchungen werden protokolliert

### 1.7 Ausleihsystem
- Manuelle Ausleihe: Über Admin-Oberfläche, Werkzeug/Mitarbeiter auswählen
- QuickScan: Barcode-Scan, schneller Ablauf für Ausleihe/Rückgabe
- Rückgabe: Über Rückgabe-Funktion, Status und Historie werden aktualisiert
- Überfälligkeit: Überfällige Ausleihen werden angezeigt

### 1.8 Ticketsystem
- Ticketarten: Allgemein, Auftrag, Materialbedarf
- Anlegen: Über Formular, Zuweisung zu Mitarbeiter möglich
- Status: Offen, zugewiesen, in Bearbeitung, erledigt, geschlossen
- Kommunikation: Nachrichten und Notizen im Ticket
- Export: Tickets können als Datei exportiert werden
- Auftragsdetails: Separate Verwaltung von Auftragsmaterial und -details

### 1.9 Benutzerverwaltung
- Benutzer anlegen, bearbeiten, löschen
- Rollen zuweisen: Admin, Mitarbeiter, Anwender, Teilnehmer
- Passwort-Reset: Über Admin-Oberfläche oder per E-Mail
- Profilverwaltung: Eigene Profildaten ändern

### 1.10 Berichte und Dashboard
- Dashboard: Übersicht über aktuelle Ausleihen, offene Tickets, Verbrauch, Statistiken
- Berichte: Wochenberichte, Ausleihstatistiken, Verbrauchsstatistiken
- Exportfunktionen für Berichte

### 1.11 Backup und Wiederherstellung
- Automatische Backups im Verzeichnis `backups/`
- Manuelles Backup über Admin-Oberfläche oder per Docker/MongoDB-Tools
- Wiederherstellung: Backup-Datei auswählen und einspielen
- Backup-Upload: JSON-Backup-Dateien können hochgeladen und wiederhergestellt werden
- Backup-Status und Logs über Admin-Oberfläche einsehbar
- Automatische Sicherung der aktuellen Datenbank vor Wiederherstellung

### 1.12 E-Mail-Benachrichtigungen
- SMTP-Konfiguration über Weboberfläche oder `.env`
- Unterstützte Anbieter: Gmail, Office365, beliebige SMTP-Server
- Funktionen: Passwort-Reset, Benachrichtigungen, Backup-Reports
- Testfunktion für E-Mail-Versand
- Fehlerdiagnose über Logs

### 1.13 Fehlerbehebung und Support für Anwender
- Logs prüfen: `docker-compose logs -f`
- Sicherstellen, dass Docker läuft und Ports 5000/8081 frei sind
- E-Mail-Probleme: SMTP-Einstellungen und Logs prüfen
- Datenbankprobleme: MongoDB-Status prüfen (`docker exec -it scandy-mongodb mongosh`)
- Bei Problemen mit Backups: Speicherplatz und Dateiberechtigungen prüfen
- Bei nicht lösbaren Problemen: Backup wiederherstellen

---

## 2. Entwicklung & Betrieb

### 2.1 Projektstruktur und Komponenten im Detail
- Siehe `app_structure.md` für vollständige Übersicht
- Hauptkomponenten:
  - `app/`: Flask-Anwendung, Modelle, Routen, Templates, Static-Files, Utils
  - `mongo-init/`: Initialisierungsskripte für MongoDB
  - `backups/`, `logs/`, `data/`: Datenverzeichnisse
  - `docker-compose.yml`, `Dockerfile`: Container- und Build-Konfiguration
  - `install.bat`, `install.sh`, `update.bat`, `update.sh`: Installations- und Update-Skripte

### 2.2 Konfigurationsmanagement
- Alle Einstellungen über `.env`-Datei oder Umgebungsvariablen
- Wichtige Variablen:
  - `MONGODB_URI`: Verbindungsstring zur MongoDB
  - `SECRET_KEY`: Flask-Session-Key
  - `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`: SMTP-Konfiguration
  - Weitere Variablen siehe `env.example`

### 2.3 Datenbankmodell und Datenflüsse
- Hauptdatenbank: `scandy` (Werkzeuge, Verbrauchsgüter, Benutzer, Ausleihen, etc.)
- Ticket-Datenbank: `scandy_tickets` (Tickets, Auftragsdetails, Material)
- Datenbankmodelle in `app/models/`
- Datenflüsse: CRUD-Operationen über Flask-Routen, MongoDB als persistente Speicherung
- Migrationen: Manuell per Dump/Restore, keine automatisierten Migrationsskripte

### 2.4 API-Design und Routenübersicht
- REST-ähnliche API-Routen in `app/routes/`
- Übersicht aller Routen und Berechtigungen siehe `berechtigungen_uebersicht.md`
- Authentifizierung über Session, kein OAuth/JWT
- API-Endpoints für Werkzeuge, Verbrauchsgüter, Tickets, Benutzer, Admin-Funktionen

### 2.5 Authentifizierung, Autorisierung, Sessions
- Authentifizierung über Flask-Login
- Sessions serverseitig gespeichert (Flask-Session)
- Rollenbasierte Zugriffskontrolle über Decorators (`@admin_required`, `@mitarbeiter_required`, ...)
- Passwort-Hashing mit Werkzeug
- Passwort-Reset per E-Mail oder Admin

### 2.6 Frontend-Architektur
- Templates: Jinja2-Templates in `app/templates/`
- CSS: Tailwind CSS, eigene Styles in `app/static/css/`
- JavaScript: Eigene Skripte in `app/static/js/`
- Responsive Design, Touch-Optimierung für QuickScan
- Komponentenstruktur für wiederverwendbare UI-Elemente

### 2.7 Docker-Setup, Build, Deployment, Volumes, Healthchecks
- Docker-Container für App, MongoDB, Mongo Express
- Build über `Dockerfile`, Orchestrierung über `docker-compose.yml`
- Volumes für Datenpersistenz (`data/`, `backups/`, `logs/`)
- Healthchecks für MongoDB (Warten auf readiness im Install-Skript)
- Deployment lokal oder auf Server mit Docker

### 2.8 Update- und Upgrade-Prozess, Migration
- Update-Skripte: `update.bat` (Windows), `update.sh` (Linux/macOS)
- Manuelles Update: `docker-compose down`, `docker-compose up -d --build`
- Daten bleiben bei Update erhalten
- Migrationen: Manuell per Dump/Restore, keine automatisierten Migrationsskripte

### 2.9 Sicherheit: Best Practices, Logging, Monitoring, Recovery
- Authentifizierung und rollenbasierte Autorisierung
- CSRF-Schutz, Input-Validierung
- Logging in `logs/` und über Docker-Logs
- Monitoring über Healthchecks, Statusseiten, Logs
- Recovery: Backup/Restore, Rollback über Docker-Images und Backups

### 2.10 Erweiterung: Neue Features, Customizing, Tests
- Neue Routen/Funktionen in `app/routes/` hinzufügen
- Datenbankmodelle in `app/models/` erweitern
- Frontend-Anpassungen in `app/templates/` und `app/static/`
- Konfiguration über `.env` und Docker Compose anpassen
- Tests: Manuell, keine automatisierte Testabdeckung vorhanden

### 2.11 Troubleshooting: Logs, Fehleranalyse, Recovery
- Fehleranalyse über `docker-compose logs` und Anwendungslogs
- Datenbankstatus prüfen: `docker exec -it scandy-mongodb mongosh`
- Backup- und Restore-Probleme: Dateiberechtigungen und Speicherplatz prüfen
- Bei Problemen mit Containern: Neustart mit `docker-compose restart <service>`
- Bei nicht lösbaren Problemen: Backup wiederherstellen

### 2.12 Backup/Restore im Produktivbetrieb
- Regelmäßige Backups empfohlen (automatisch und manuell)
- Backups im Verzeichnis `backups/` sichern
- Restore über Admin-Oberfläche oder per MongoDB-Tools
- Vor Updates und Migrationen immer Backup anlegen

### 2.13 Hinweise zu Performance, Skalierung, Betrieb
- Für kleine bis mittlere Teams ausgelegt
- Skalierung über Docker Compose möglich (mehr RAM/CPU, separate Datenbank)
- Performance-Optimierung durch Indexe in MongoDB, Caching im Frontend
- Monitoring und Logging regelmäßig prüfen
- Bei hoher Last: Separate Datenbank-Instanz und Load Balancer möglich 