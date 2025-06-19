# Systemarchitektur

## Übersicht

Scandy ist eine moderne Webanwendung mit einer klaren Trennung zwischen Frontend und Backend. Die Anwendung folgt dem Model-View-Controller (MVC) Muster und verwendet eine MongoDB-Datenbank für die Datenspeicherung.

## Technologie-Stack

### Backend
- **Programmiersprache**: Python 3.x
- **Web-Framework**: Flask
- **Datenbank**: MongoDB
- **WSGI-Server**: Gunicorn (Produktion)
- **Template-Engine**: Jinja2

### Frontend
- **HTML5**: Struktur
- **CSS**: Tailwind CSS, DaisyUI
- **JavaScript**: Vanilla JS
- **Responsive Design**: Mobile-first Ansatz

## Systemkomponenten

### 1. Datenbank

#### Collections (Hauptdatenbank)

#### Werkzeuge (tools)
- `barcode`: Eindeutiger Barcode
- `name`: Name des Werkzeugs
- `description`: Beschreibung
- `status`: Status (verfügbar, ausgeliehen, defekt, etc.)
- `category`: Kategorie
- `location`: Standort
- `condition`: Zustand
- `purchase_date`: Kaufdatum
- `next_maintenance`: Nächste Wartung
- `deleted`: Soft-Delete-Flag
- `created_at`: Erstellungsdatum
- `updated_at`: Aktualisierungsdatum

#### Verbrauchsmaterialien (consumables)
- `barcode`: Eindeutiger Barcode
- `name`: Name des Materials
- `description`: Beschreibung
- `quantity`: Aktuelle Menge
- `min_quantity`: Mindestbestand
- `category`: Kategorie
- `location`: Standort
- `unit`: Einheit
- `deleted`: Soft-Delete-Flag
- `created_at`: Erstellungsdatum
- `updated_at`: Aktualisierungsdatum

#### Mitarbeiter (workers)
- `barcode`: Eindeutiger Barcode
- `firstname`: Vorname
- `lastname`: Nachname
- `department`: Abteilung
- `email`: E-Mail
- `phone`: Telefonnummer
- `deleted`: Soft-Delete-Flag
- `created_at`: Erstellungsdatum
- `updated_at`: Aktualisierungsdatum

#### Ausleihen (lendings)
- `tool_barcode`: Barcode des Werkzeugs
- `worker_barcode`: Barcode des Mitarbeiters
- `lent_at`: Ausleihdatum
- `returned_at`: Rückgabedatum
- `notes`: Notizen
- `created_at`: Erstellungsdatum

#### Verbrauchsmaterial-Nutzung (consumable_usages)
- `consumable_barcode`: Barcode des Materials
- `worker_barcode`: Barcode des Mitarbeiters
- `quantity`: Verbrauchte Menge
- `used_at`: Verbrauchsdatum
- `created_at`: Erstellungsdatum

#### Benutzer (users)
- `username`: Benutzername
- `password_hash`: Gehashtes Passwort
- `email`: E-Mail
- `firstname`: Vorname
- `lastname`: Nachname
- `role`: Rolle (admin, mitarbeiter)
- `is_active`: Aktiv-Status
- `created_at`: Erstellungsdatum
- `last_login`: Letzter Login

#### Einstellungen (settings)
- `key`: Einstellungsschlüssel
- `value`: Einstellungswert
- `description`: Beschreibung
- `created_at`: Erstellungsdatum
- `updated_at`: Aktualisierungsdatum

#### Kategorien (categories)
- `name`: Kategoriename
- `description`: Beschreibung
- `deleted`: Soft-Delete-Flag
- `created_at`: Erstellungsdatum
- `updated_at`: Aktualisierungsdatum

#### Standorte (locations)
- `name`: Standortname
- `description`: Beschreibung
- `deleted`: Soft-Delete-Flag
- `created_at`: Erstellungsdatum
- `updated_at`: Aktualisierungsdatum

#### Abteilungen (departments)
- `name`: Abteilungsname
- `description`: Beschreibung
- `deleted`: Soft-Delete-Flag
- `created_at`: Erstellungsdatum
- `updated_at`: Aktualisierungsdatum

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