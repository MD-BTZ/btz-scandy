# Systemarchitektur

## Übersicht

Scandy ist eine moderne Webanwendung mit einer klaren Trennung zwischen Frontend und Backend. Die Anwendung folgt dem Model-View-Controller (MVC) Muster und verwendet eine SQLite-Datenbank für die Datenspeicherung.

## Technologie-Stack

### Backend
- **Programmiersprache**: Python 3.x
- **Web-Framework**: Flask
- **Datenbank**: SQLite
- **WSGI-Server**: Gunicorn (Produktion)
- **Template-Engine**: Jinja2

### Frontend
- **HTML5**: Struktur
- **CSS**: Tailwind CSS, DaisyUI
- **JavaScript**: Vanilla JS
- **Responsive Design**: Mobile-first Ansatz

## Systemkomponenten

### 1. Datenbank

#### Struktur
- **inventory.db**: Hauptdatenbank
  - Werkzeuge
  - Verbrauchsmaterial
  - Mitarbeiter
  - Ausleihen
  - Einstellungen

- **users.db**: Benutzerdatenbank
  - Benutzerkonten
  - Berechtigungen
  - Sessions

#### Tabellen (inventory.db)
```sql
-- Werkzeuge
CREATE TABLE tools (
    id INTEGER PRIMARY KEY,
    barcode TEXT UNIQUE,
    name TEXT,
    category TEXT,
    location TEXT,
    status TEXT,
    notes TEXT
);

-- Verbrauchsmaterial
CREATE TABLE consumables (
    id INTEGER PRIMARY KEY,
    name TEXT,
    category TEXT,
    quantity INTEGER,
    min_quantity INTEGER,
    location TEXT
);

-- Mitarbeiter
CREATE TABLE workers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    active BOOLEAN
);

-- Ausleihen
CREATE TABLE lendings (
    id INTEGER PRIMARY KEY,
    tool_id INTEGER,
    worker_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    status TEXT,
    FOREIGN KEY(tool_id) REFERENCES tools(id),
    FOREIGN KEY(worker_id) REFERENCES workers(id)
);
```

### 2. Backend

#### Flask-Applikation
- **App Factory**: `app/__init__.py`
- **Konfiguration**: `app/config.py`
- **Blueprints**: `app/routes/`
- **Modelle**: `app/models/`
- **Utilities**: `app/utils/`

#### Wichtige Module
1. **Database**: Zentrale Datenbankzugriffsklasse
2. **Auth**: Benutzerauthentifizierung
3. **Tools**: Werkzeugverwaltung
4. **Consumables**: Materialverwaltung
5. **Workers**: Mitarbeiterverwaltung
6. **Lending**: Ausleihsystem
7. **Tickets**: Ticketsystem

### 3. Frontend

#### Templates
- **Basis**: `base.html`
- **Layouts**: `shared/`
- **Komponenten**: `components/`
- **Seiten**: `tools/`, `workers/`, `consumables/`

#### JavaScript-Module
1. **quickscan.js**: Barcode-Scanning
2. **lending-service.js**: Ausleihverwaltung
3. **toast.js**: Benachrichtigungen
4. **form-validation.js**: Formularvalidierung

## Datenfluss

1. **Benutzerinteraktion**
   - Frontend sendet HTTP-Request
   - Flask-Route verarbeitet Request
   - Controller greift auf Model zu
   - Daten werden in Datenbank gespeichert
   - Response wird generiert

2. **Barcode-Scanning**
   - Scanner sendet Barcode
   - JavaScript verarbeitet Eingabe
   - API-Request an Backend
   - Datenbankabfrage
   - Response mit Werkzeugdaten

3. **Ausleihprozess**
   - Benutzer wählt Werkzeug
   - System prüft Verfügbarkeit
   - Ausleihdatensatz wird erstellt
   - Status wird aktualisiert
   - Bestätigung wird angezeigt

## Sicherheit

### Authentifizierung
- Session-basierte Authentifizierung
- Passwort-Hashing mit Werkzeug-Security
- CSRF-Schutz
- Rate Limiting

### Autorisierung
- Rollenbasierte Zugriffskontrolle
- Admin-Berechtigungen
- Ressourcenbeschränkungen

### Datenbank
- SQL-Injection-Schutz
- Prepared Statements
- Eingabevalidierung

## Skalierbarkeit

### Horizontale Skalierung
- Stateless Design
- Session-Externalisierung
- Load Balancing

### Vertikale Skalierung
- Caching
- Datenbankoptimierung
- Ressourcenmanagement

## Monitoring

### Logging
- Application Logs
- Error Tracking
- Performance Monitoring

### Metriken
- Response Times
- Datenbank-Performance
- Benutzeraktivität 