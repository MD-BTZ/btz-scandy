# Scandy - Werkzeug- und Materialverwaltung

Scandy ist eine Webanwendung zur Verwaltung von Werkzeugen, Verbrauchsmaterialien und deren Ausleihe/Nutzung durch Mitarbeiter.

## Inhaltsverzeichnis

- [Projektübersicht](#projektübersicht)
- [Features](#features)
- [Technologie-Stack](#technologie-stack)
- [Setup & Installation](#setup--installation)
- [Projektstruktur (Detailliert)](#projektstruktur-detailliert)
- [Datenbank](#datenbank)
- [Konfiguration](#konfiguration)
- [Backend (Flask)](#backend-flask)
- [Frontend](#frontend)
- [Deployment](#deployment)

## Projektübersicht

Die Anwendung ermöglicht es, einen Inventarbestand von Werkzeugen und Verbrauchsmaterialien zu pflegen, Ausleihvorgänge zu verfolgen und die Materialentnahme zu protokollieren. Eine QuickScan-Funktion mittels Barcodes erleichtert die Prozesse. Es gibt eine Benutzerverwaltung mit Admin-Rolle.

## Features

- Verwaltung von Werkzeugen (inkl. Status, Kategorie, Standort)
- Verwaltung von Verbrauchsmaterialien (inkl. Bestand, Mindestbestand)
- Verwaltung von Mitarbeitern (inkl. Abteilung)
- Ausleihen und Rückgeben von Werkzeugen
- Protokollierung der Materialentnahme
- QuickScan-Funktion via Barcode-Eingabe
- Anzeige der Historie für Werkzeuge, Material und Mitarbeiter
- Ticket-System für Meldungen
- Benutzer-Authentifizierung (Login/Logout)
- Admin-Bereich für erweiterte Verwaltung

## Technologie-Stack

- **Backend:** Python 3, Flask
- **Datenbank:** SQLite
- **Frontend:** HTML, Tailwind CSS, DaisyUI, JavaScript (mit Jinja2 Templating)
- **Server:** Gunicorn (für Produktion empfohlen)

## Setup & Installation

1.  **Repository klonen:** `git clone <repository_url>`
2.  **Virtuelle Umgebung erstellen:** `python -m venv venv`
3.  **Umgebung aktivieren:**
    *   Windows: `.\venv\Scripts\activate`
    *   Linux/macOS: `source venv/bin/activate`
4.  **Abhängigkeiten installieren:** `pip install -r requirements.txt`
5.  **Datenbank initialisieren/prüfen:**
    *   Die Hauptdatenbank (`app/database/inventory.db`) und die Benutzerdatenbank (`app/database/users.db`) sollten im Repository enthalten sein oder beim ersten Start initialisiert werden.
    *   Das Skript `app/db_migration.py` enthält Datenbankschema-Änderungen. Führen Sie es bei Bedarf aus, um das Schema zu aktualisieren: `python app/db_migration.py`
    *   **WICHTIG:** Die mitgelieferte `inventory.db` enthält Demodaten. Für einen Produktiveinsatz sollten die Daten gelöscht und neu eingegeben werden.
6.  **(Optional) Ersten Admin-Benutzer anlegen:** Falls die Benutzerdatenbank leer ist, verwenden Sie das (ggf. aus `_potentially_unused` wiederhergestellte) Skript `create_admin.py` (Details zur Nutzung siehe Skript).
7.  **Entwicklungsserver starten:** `flask run` (oder `python run.py`)

Die Anwendung ist standardmäßig unter `http://127.0.0.1:5000` erreichbar.

## Projektstruktur (Detailliert)

```
scandy/
├── _potentially_unused/  # Isolierte, wahrscheinlich ungenutzte Dateien (kann gelöscht werden)
├── app/                  # Hauptverzeichnis der Flask-Anwendung
│   ├── database/         # Enthält SQLite-DBs (inventory.db, users.db)
│   ├── models/           # Datenbankschicht
│   │   ├── database.py   # Zentrale Klasse für DB-Abfragen (meist rohes SQL)
│   │   ├── tool.py       # (Optional) Modellklasse für Werkzeuge
│   │   ├── worker.py     # (Optional) Modellklasse für Mitarbeiter
│   │   ├── consumable.py # (Optional) Modellklasse für Verbrauchsmaterial
│   │   ├── user.py       # Modellklasse für Benutzer (verwendet von Flask-Login)
│   │   └── ...           # Weitere Modelle (settings.py etc.)
│   ├── routes/           # Flask Blueprints (Controller)
│   │   ├── tools.py      # Routen für /tools (index, detail, edit, add)
│   │   ├── workers.py    # Routen für /workers
│   │   ├── consumables.py# Routen für /consumables
│   │   ├── auth.py       # Routen für /auth (login, logout)
│   │   └── ...           # Weitere Blueprints (admin, main, api, etc.)
│   ├── static/           # Statische Frontend-Assets
│   │   ├── css/          # CSS-Dateien (main.css, quickscan.css)
│   │   ├── js/           # JavaScript-Dateien (quickscan.js, etc.)
│   │   └── images/       # Bilder
│   ├── templates/        # Jinja2 HTML-Templates (Views)
│   │   ├── base.html     # Basis-Layout
│   │   ├── tools/        # Templates für Werkzeuge (index.html, details.html)
│   │   ├── workers/      # Templates für Mitarbeiter
│   │   ├── consumables/  # Templates für Verbrauchsmaterial
│   │   ├── components/   # Wiederverwendbare Template-Snippets (z.B. für Modals)
│   │   └── shared/       # Geteilte Templates (z.B. list_base.html)
│   ├── utils/            # Hilfsmodule
│   │   ├── decorators.py # Enthält @login_required, @admin_required
│   │   ├── auth_utils.py # Hilfsfunktionen für Auth (needs_setup)
│   │   └── ...           # Weitere Utilities (Filter, Logger etc.)
│   ├── __init__.py       # App Factory (`create_app`), registriert Blueprints & Erweiterungen
│   ├── config.py         # Konfigurationsklassen (Development, Production)
│   ├── db_migration.py   # Skript zur Anwendung von DB-Schemaänderungen
│   ├── schema.sql        # (Referenz) SQL-Schema der Haupt-DB
│   └── wsgi.py           # WSGI-Einstiegspunkt für Produktionsserver
├── backups/              # Verzeichnis für DB-Backups (ignoriert von Git)
├── instance/             # Instanz-Daten (z.B. Sessions, ignoriert von Git)
├── venv/                 # Virtuelle Python-Umgebung (ignoriert von Git)
├── .gitignore            # Definiert von Git zu ignorierende Dateien/Ordner
├── backup.py             # Skript für Backup-Logik (wird in __init__.py verwendet)
├── Dockerfile            # (Optional) Docker-Konfiguration
├── gunicorn.conf.py      # (Optional) Gunicorn-Konfiguration
├── LICENSE               # Lizenzdatei
├── README.md             # Diese Datei
├── requirements.txt      # Python-Abhängigkeiten
└── run.py                # Skript zum Starten des Flask-Entwicklungs-Servers
```

## Datenbank

- **Technologie:** SQLite
- **Speicherorte:**
    - `app/database/inventory.db`: Hauptdatenbank für Werkzeuge, Material, Mitarbeiter, Ausleihen, Einstellungen etc.
    - `app/database/users.db`: Separate Datenbank nur für Benutzerdaten (Username, Passwort-Hash). Wird von `app/routes/auth.py` und `app/utils/auth_utils.py` verwendet.
- **Schema & Migration:**
    - Das ursprüngliche Schema für `inventory.db` kann in `app/schema.sql` eingesehen werden.
    - Schemaänderungen werden durch das Skript `app/db_migration.py` verwaltet und angewendet. Dieses Skript enthält `ALTER TABLE`-Befehle und sollte nach Codeänderungen, die neue Spalten erfordern, ausgeführt werden (`python app/db_migration.py`).
- **Datenzugriff:** Erfolgt primär über die Klasse `Database` in `app/models/database.py`. Diese Klasse bietet Methoden (`query`, `execute`, `get_db`, `get_db_connection`), die meist direkt SQL-Abfragen ausführen.
- **Modelle (`app/models/`):**
    - Definieren teilweise Klassen (`User`, `Tool`, `Worker`, `Consumable`), die aber nicht als vollwertiges ORM (wie SQLAlchemy) genutzt werden. Sie dienen eher der Strukturierung und teilweise der Datenvalidierung oder einfachen Abfragen (`User.get_by_id`).
    - Die meiste Logik findet in den Routen (`app/routes/`) statt, die direkt `Database.query` aufrufen.

## Konfiguration

- **Datei:** `app/config.py`
- **Klassen:**
    - `Config`: Basis-Konfiguration, plattformunabhängige Pfade (`BASE_DIR`, `DATABASE_DIR`, `DATABASE`, `BACKUP_DIR`).
    - `DevelopmentConfig`: Erbt von `Config`, setzt `DEBUG = True`.
    - `ProductionConfig`: Erbt von `Config`, setzt `DEBUG = False`, Session-Sicherheitseinstellungen, überschreibt Pfade für spezifische Umgebungen (z.B. PythonAnywhere).
- **Auswahl:** Die `config`-Variable am Ende der Datei wählt die passende Konfiguration basierend auf Umgebungsvariablen oder Plattform (z.B. `is_pythonanywhere()`). Die Flask-App (`create_app` in `app/__init__.py`) lädt die `default`-Konfiguration.

## Backend (Flask)

- **App Factory:** Die Funktion `create_app` in `app/__init__.py` erstellt die Flask-Anwendungsinstanz.
    - **Wichtige Aktionen:** Lädt Konfiguration, initialisiert Logging, registriert Blueprints, Filter, Context Processors, Fehlerbehandler, initialisiert Datenbankverbindung und führt initiale DB-Prüfungen/Setup-Schritte aus.
- **Blueprints (`app/routes/`):** Jeder Blueprint ist für einen Teilbereich der Anwendung zuständig.
    - **Beispiel `tools.py`:** Definiert Routen wie `/` (Werkzeugliste), `/<barcode>` (Detailansicht, POST für Update), `/add` (neues Werkzeug). Interagiert typischerweise mit der `Database`-Klasse, um Werkzeugdaten zu lesen/schreiben und rendert Templates aus `app/templates/tools/`.
    - **Beispiel `auth.py`:** Definiert `/login` und `/logout`. Verwendet die separate `users.db` und die `User`-Klasse (`app/models/user.py`) sowie Werkzeug-Security-Funktionen (`check_password_hash`).
    - **Abhängigkeiten:** Routen-Funktionen verwenden oft Decorators aus `app/utils/decorators.py` (`@login_required`, `@admin_required`) zur Zugriffskontrolle.
- **Utilities (`app/utils/`):**
    - `decorators.py`: Definiert `@login_required` (prüft Session und `needs_setup()`) und `@admin_required` (prüft Admin-Status in Session).
    - `auth_utils.py`: Enthält `needs_setup()` (prüft `users`-Tabelle in `users.db`) und `check_password()`.
    - `database.py` (in `app/models/`): Ist zentral für alle Datenbankoperationen.
    - `filters.py`: Definiert benutzerdefinierte Jinja2-Filter (registriert in `app/__init__.py`).
    - `context_processors.py`: Stellt globale Variablen für Templates bereit (z.B. Mülleimer-Anzahl, registriert in `app/__init__.py`).

## Frontend

- **Templates (`app/templates/`):**
    - **Vererbung:** `base.html` ist das Hauptlayout. Listenansichten (wie `tools/index.html`) erben oft von `shared/list_base.html`, welches wiederum von `base.html` erbt.
    - **Komponenten:** `components/` enthält wiederverwendbare Teile, z.B. `quickscan_modal.html`, das in `base.html` eingebunden wird.
    - **Daten:** Templates erhalten Daten von den Flask-Routen über das `render_template()`-Argument.
- **Styling:** Tailwind CSS & DaisyUI über CDN. Spezifische Anpassungen in `app/static/css/main.css`.
- **JavaScript (`app/static/js/`):**
    - `quickscan.js`: Enthält die komplexe Logik für das Barcode-Scanning-Modal (Schrittabfolge, API-Aufrufe an `/quick_scan/process`, UI-Updates).
    - `lending-service.js`: Stellt wahrscheinlich Funktionen für Ausleihe/Rückgabe bereit, die von anderen Teilen des Frontends (z.B. Buttons in Tabellen) aufgerufen werden könnten (interagiert ggf. mit der API).
    - `toast.js`: Zeigt kurze Benachrichtigungen (Toasts) an.
    - Interaktionen erfolgen oft durch direkte DOM-Manipulation und `fetch`-Aufrufe an Backend-Routen/API-Endpunkte.

## Deployment

- Der Code enthält eine `wsgi.py`-Datei, die als Einstiegspunkt für WSGI-Server wie Gunicorn dient.
- Eine `gunicorn.conf.py` ist vorhanden.
- Für ein Produktionsdeployment sollte ein robuster WSGI-Server (wie Gunicorn) hinter einem Reverse Proxy (wie Nginx) verwendet werden.
- Stellen Sie sicher, dass `SECRET_KEY` in der Produktionsumgebung sicher als Umgebungsvariable gesetzt ist.
- Die `ProductionConfig` in `app/config.py` sollte aktiviert sein (dies geschieht i.d.R. automatisch, wenn die App nicht lokal läuft, kann aber explizit gesetzt werden).
- Achten Sie auf die korrekten Datenbank- und Dateipfade in der `ProductionConfig`, falls diese von der Entwicklungsumgebung abweichen. 