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
- **Datenbank:** MongoDB
- **Frontend:** HTML, Tailwind CSS, DaisyUI, JavaScript (mit Jinja2 Templating)
- **Server:** Gunicorn (für Produktion empfohlen)

## Setup & Installation

1.  **Repository klonen:** `git clone <repository_url>`
2.  **Virtuelle Umgebung erstellen:** `python -m venv venv`
3.  **Umgebung aktivieren:**
    *   Windows: `.\venv\Scripts\activate`
    *   Linux/macOS: `source venv/bin/activate`
4.  **Abhängigkeiten installieren:** `pip install -r requirements.txt`
5.  **MongoDB einrichten:**
    *   Stellen Sie sicher, dass MongoDB installiert und läuft
    *   Die Anwendung verwendet standardmäßig die Datenbank `scandy` und `scandy_tickets`
    *   Für Docker-Installationen ist MongoDB bereits in der docker-compose.yml konfiguriert
6.  **Entwicklungsserver starten:** `flask run` (oder `python run.py`)

Die Anwendung ist standardmäßig unter `http://127.0.0.1:5000` erreichbar.

## Projektstruktur (Detailliert)

```
scandy/
├── app/                  # Hauptverzeichnis der Flask-Anwendung
│   ├── models/           # Datenbankschicht
│   │   ├── mongodb_database.py # Zentrale MongoDB-Verbindungsklasse
│   │   ├── mongodb_models.py   # MongoDB-Modelle
│   │   ├── tool.py       # Modellklasse für Werkzeuge
│   │   ├── worker.py     # Modellklasse für Mitarbeiter
│   │   ├── consumable.py # Modellklasse für Verbrauchsmaterial
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
│   └── wsgi.py           # WSGI-Einstiegspunkt für Produktionsserver
├── backups/              # Verzeichnis für DB-Backups (ignoriert von Git)
├── instance/             # Instanz-Daten (z.B. Sessions, ignoriert von Git)
├── venv/                 # Virtuelle Python-Umgebung (ignoriert von Git)
├── .gitignore            # Definiert von Git zu ignorierende Dateien/Ordner
├── Dockerfile            # (Optional) Docker-Konfiguration
├── gunicorn.conf.py      # (Optional) Gunicorn-Konfiguration
├── LICENSE               # Lizenzdatei
├── README.md             # Diese Datei
├── requirements.txt      # Python-Abhängigkeiten
└── run.py                # Skript zum Starten des Flask-Entwicklungs-Servers
```

## Datenbank

- **Technologie:** MongoDB
- **Datenbanken:**
    - `scandy`: Hauptdatenbank für Werkzeuge, Material, Mitarbeiter, Ausleihen, Einstellungen etc.
    - `scandy_tickets`: Separate Datenbank für Ticket-System
- **Datenzugriff:** Erfolgt über die Klasse `MongoDBDatabase` in `app/models/mongodb_database.py`. Diese Klasse bietet Methoden für alle MongoDB-Operationen (find, find_one, insert_one, update_one, delete_one, etc.).
- **Modelle (`app/models/`):**
    - Definieren Klassen (`User`, `Tool`, `Worker`, `Consumable`), die mit MongoDB interagieren
    - Die meiste Logik findet in den Routen (`app/routes/`) statt, die direkt MongoDB-Methoden aufrufen

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