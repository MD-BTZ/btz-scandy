# Scandy - App-Struktur

Scandy ist eine Flask-basierte Webanwendung zur Verwaltung von Werkzeugen und Verbrauchsmaterialien. Die Anwendung wurde mit Flask entwickelt und verwendet MongoDB als Datenbank.

## Projektstruktur

```
scandy/
├── app/                    # Hauptanwendung
│   ├── __init__.py        # Flask-App Factory
│   ├── config/            # Konfigurationsdateien
│   │   ├── __init__.py
│   │   ├── config.py      # Hauptkonfiguration
│   │   ├── db_schema.json # Datenbankschema
│   │   └── version.py     # Versionsinformationen
│   ├── models/            # Datenbankmodelle
│   │   ├── __init__.py
│   │   ├── mongodb_database.py  # MongoDB-Verbindung
│   │   ├── mongodb_models.py    # MongoDB-Modelle
│   │   ├── tool.py        # Werkzeug-Modelle
│   │   └── user.py        # Benutzer-Modelle
│   ├── routes/            # API-Routen
│   │   ├── __init__.py
│   │   ├── admin.py       # Admin-Funktionen
│   │   ├── api.py         # API-Endpunkte
│   │   ├── auth.py        # Authentifizierung
│   │   ├── consumables.py # Verbrauchsmaterialien
│   │   ├── dashboard.py   # Dashboard
│   │   ├── history.py     # Historie
│   │   ├── index.py       # Hauptseite
│   │   ├── lending.py     # Ausleihen
│   │   ├── main.py        # Hauptrouten
│   │   ├── quick_scan.py  # QuickScan
│   │   ├── setup.py       # Setup
│   │   ├── tickets.py     # Tickets
│   │   ├── tools.py       # Werkzeuge
│   │   └── workers.py     # Mitarbeiter
│   ├── static/            # Statische Dateien
│   │   ├── css/           # Stylesheets
│   │   ├── js/            # JavaScript
│   │   ├── images/        # Bilder
│   │   ├── uploads/       # Hochgeladene Dateien
│   │   └── videos/        # Videos
│   ├── templates/         # HTML-Templates
│   │   ├── admin/         # Admin-Templates
│   │   ├── auth/          # Auth-Templates
│   │   ├── components/    # Komponenten
│   │   ├── consumables/   # Verbrauchsmaterialien
│   │   ├── dashboard/     # Dashboard
│   │   ├── errors/        # Fehlerseiten
│   │   ├── shared/        # Gemeinsame Templates
│   │   ├── tickets/       # Tickets
│   │   ├── tools/         # Werkzeuge
│   │   └── workers/       # Mitarbeiter
│   ├── utils/             # Hilfsfunktionen
│   │   ├── __init__.py
│   │   ├── auth_utils.py  # Auth-Hilfen
│   │   ├── backup_manager.py # Backup-Management
│   │   ├── context_processors.py # Context-Processor
│   │   ├── db_schema.py   # Datenbankschema
│   │   ├── decorators.py  # Decorators
│   │   ├── error_handler.py # Fehlerbehandlung
│   │   ├── filters.py     # Template-Filter
│   │   ├── logger.py      # Logging
│   │   └── update_manager.py # Update-Management
│   ├── constants.py       # Konstanten
│   ├── files.py           # Datei-Management
│   └── wsgi.py           # WSGI-Entry-Point
├── backups/               # Backup-Dateien
├── docs/                  # Dokumentation
├── logs/                  # Log-Dateien
├── migrations/            # Datenbank-Migrationen
├── requirements.txt       # Python-Abhängigkeiten
├── docker-compose.yml     # Docker-Konfiguration
├── Dockerfile            # Docker-Image
├── README.md             # Projekt-README
└── start.sh              # Start-Skript
```

## Datenbankarchitektur

Die Anwendung verwendet MongoDB als Datenbank. Die Datenbank ist in zwei Datenbanken aufgeteilt:

### Hauptdatenbank (scandy)
- **tools**: Werkzeuge mit Barcodes
- **consumables**: Verbrauchsmaterialien
- **workers**: Mitarbeiter
- **lendings**: Ausleihen
- **consumable_usages**: Materialverbrauch
- **departments**: Abteilungen
- **categories**: Kategorien
- **locations**: Standorte
- **users**: Benutzer
- **settings**: Systemeinstellungen

### Ticket-Datenbank (scandy_tickets)
- **tickets**: Tickets
- **auftrag_details**: Auftragsdetails
- **auftrag_material**: Auftragsmaterial

## MongoDB-Verbindung

```python
from app.models.mongodb_database import MongoDB

# MongoDB-Instanz erstellen
mongodb = MongoDB()

# Datenbankverbindung
db = mongodb.db

# Collection-Zugriff
tools = db.tools
consumables = db.consumables
workers = db.workers
```

## Hauptfunktionen

### 1. Werkzeugverwaltung
- Barcode-basierte Identifikation
- Kategorisierung und Standortverwaltung
- Status-Tracking (verfügbar, ausgeliehen, defekt)
- Wartungshistorie

### 2. Verbrauchsmaterialverwaltung
- Bestandsverwaltung
- Mindestbestand-Warnungen
- Verbrauchstracking
- Automatische Nachbestellung

### 3. Ausleihsystem
- Barcode-Scanning
- Mitarbeiterzuordnung
- Rückgabe-Tracking
- Überfälligkeitswarnungen

### 4. QuickScan
- Schnelle Ausleihe/Rückgabe
- Barcode-Scanner-Integration
- Touchscreen-optimiert

### 5. Admin-Dashboard
- Statistiken und Berichte
- Systemverwaltung
- Benutzerverwaltung
- Backup-Management

### 6. Ticket-System
- Auftragsverwaltung
- Materialzuordnung
- Status-Tracking
- Dokumentation

## Technologie-Stack

- **Backend**: Python 3, Flask
- **Datenbank**: MongoDB
- **Frontend**: HTML, Tailwind CSS, DaisyUI, JavaScript
- **Server**: Gunicorn (Produktion)
- **Container**: Docker
- **Deployment**: Docker Compose

## Sicherheit

- Flask-Login für Authentifizierung
- Rollenbasierte Zugriffskontrolle (Admin, Mitarbeiter)
- Session-Management
- CSRF-Schutz
- Input-Validierung

## Backup-System

- Automatische MongoDB-Backups
- JSON-Export für Portabilität
- Backup-Rotation
- Wiederherstellungsfunktionen

## Monitoring

- Logging-System
- Performance-Monitoring
- Fehlerbehandlung
- System-Status-Tracking