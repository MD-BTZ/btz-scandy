# Scandy Projektstruktur

## Hauptverzeichnis
- `app/` - Hauptanwendungsverzeichnis
- `venv/` - Virtuelle Python-Umgebung
- `migrations/` - Datenbank-Migrationen
- `docs/` - Dokumentation
- `backups/` - Backup-Verzeichnis
- `exports/` - Export-Verzeichnis
- `barcodes/` - Barcode-Verzeichnis

## Skripte und Konfiguration
- `install.bat` - Windows-Installationsskript
- `install.sh` - Linux-Installationsskript
- `start.bat` - Windows-Startskript
- `start.sh` - Linux-Startskript
- `requirements.txt` - Python-Abhängigkeiten
- `tailwind.config.js` - Tailwind CSS Konfiguration
- `docker-compose.yml` - Docker-Konfiguration
- `Dockerfile` - Docker-Build-Konfiguration

## App-Struktur (`app/`)
### Hauptmodule
- `__init__.py` - Flask-Anwendungsinitialisierung
- `wsgi.py` - WSGI-Einstiegspunkt
- `config.py` - Hauptkonfigurationsdatei
- `constants.py` - Konstantendefinitionen

### Verzeichnisse
- `templates/` - HTML-Templates
  - `components/` - Wiederverwendbare UI-Komponenten
  - `admin/` - Admin-Bereich Templates
  - `dashboard/` - Dashboard-Templates
  - `tools/` - Werkzeug-bezogene Templates
  - `workers/` - Mitarbeiter-bezogene Templates
  - `tickets/` - Ticket-bezogene Templates
  - `consumables/` - Verbrauchsmaterial-bezogene Templates

- `static/` - Statische Dateien
  - `css/` - Stylesheets
  - `js/` - JavaScript-Dateien
  - `images/` - Bilder
  - `tool_images/` - Werkzeugbilder
  - `audio/` - Audiodateien

- `routes/` - Flask-Routen
  - `admin.py` - Admin-Bereich Routen
  - `api.py` - API-Endpunkte
  - `auth.py` - Authentifizierungsrouten
  - `backup.py` - Backup-Routen
  - `consumables.py` - Verbrauchsmaterial-Routen
  - `dashboard.py` - Dashboard-Routen
  - `history.py` - Verlaufs-Routen
  - `index.py` - Hauptseiten-Routen
  - `lending.py` - Ausleih-Routen
  - `main.py` - Hauptrouten
  - `quick_scan.py` - Schnellscan-Routen
  - `tickets.py` - Ticket-Routen
  - `tools.py` - Werkzeug-Routen
  - `workers.py` - Mitarbeiter-Routen

- `models/` - Datenmodelle
  - `database.py` - Datenbank-Hauptklasse
  - `init_db.py` - Datenbank-Initialisierung
  - `user.py` - Benutzermodell
  - `worker.py` - Mitarbeitermodell
  - `tool.py` - Werkzeugmodell
  - `consumable.py` - Verbrauchsmaterialmodell
  - `ticket_db.py` - Ticket-Datenbankmodell
  - `settings.py` - Einstellungsmodell

- `utils/` - Hilfsfunktionen
  - `filters.py` - Template-Filter
  - `auth_utils.py` - Authentifizierungshilfen
  - `decorators.py` - Python-Dekoratoren
  - `context_processors.py` - Template-Kontext-Prozessoren
  - `db_schema.py` - Datenbankschema-Definitionen
  - `error_handler.py` - Fehlerbehandlung
  - `logger.py` - Logging-Funktionen
  - `system_structure.py` - Systemstruktur-Definitionen
  - `color_settings.py` - Farbeinstellungen

- `config/` - Konfigurationsdateien
  - `config.py` - Konfigurationsklassen
  - `version.py` - Versionsinformationen
  - `db_schema.json` - Datenbankschema in JSON

- `scripts/` - Hilfsskripte
  - `reset_color_settings.py` - Farbeinstellungen zurücksetzen
  - `setup_design_settings.py` - Design-Einstellungen einrichten

- `sql/` - SQL-Dateien
  - `design_settings.sql` - Design-Einstellungen SQL

## Datenbankverzeichnisse
- `app/database/` - Datenbankdateien
- `app/flask_session/` - Flask-Sessions
- `app/logs/` - Anwendungslogs
- `app/uploads/` - Hochgeladene Dateien

## Dokumentation
- `README.md` - Hauptdokumentation
- `LICENSE` - Lizenzinformationen
- `app_structure.md` - Detaillierte App-Struktur
- `PROJECT_STRUCTURE.md` - Diese Datei 