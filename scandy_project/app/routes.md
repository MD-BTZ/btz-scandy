# Scandy - Routen-Dokumentation

## Authentifizierung (/auth)
- GET, POST `/auth/login` - Login-Formular und Verarbeitung
- GET `/auth/logout` - Benutzer ausloggen
- GET `/auth/test` - Test-Route

## Admin-Bereich (/)
- GET `/` - Dashboard
- GET `/manual_lending` - Manuelle Ausleihe
- POST `/update_design` - Design-Einstellungen aktualisieren
- POST `/process_lending` - Ausleihe verarbeiten
- POST `/process_return` - Rückgabe verarbeiten

## API (/api)
- GET `/api/workers` - Liste aller Mitarbeiter
- GET `/api/tools/<barcode>` - Tool-Details
- POST `/api/settings/colors` - Farbeinstellungen aktualisieren
- POST `/api/lending/process` - Ausleihe-Prozess
- POST `/api/lending/return` - Rückgabe-Prozess

## Verbrauchsmaterial (/consumables)
- GET `/consumables/` - Übersicht
- GET, POST `/consumables/add` - Hinzufügen
- GET `/consumables/<barcode>` - Details
- GET, POST `/consumables/<barcode>/edit` - Bearbeiten
- POST `/consumables/<barcode>/delete` - Löschen

## Inventar (/inventory)
### Verbrauchsmaterial
- GET `/inventory/consumables/<barcode>` - Details
- POST `/inventory/consumables/update/<barcode>` - Aktualisieren

### Werkzeuge
- GET `/inventory/tools/<barcode>` - Details
- GET `/inventory/tools` - Übersicht
- POST `/inventory/tools/<barcode>/update` - Aktualisieren

### Mitarbeiter
- GET `/inventory/workers/<barcode>` - Details
- GET `/inventory/workers` - Übersicht
- POST `/inventory/workers/update/<barcode>` - Aktualisieren

### Sonstiges
- GET `/inventory/manual-lending` - Manuelle Ausleihe

## Quick Scan
- GET `/quick_scan` - Quick-Scan-Interface

## Werkzeuge (/tools)
- GET `/tools` - Übersicht
- GET, POST `/tools/add` - Hinzufügen
- GET `/tools/<barcode>` - Details
- GET, POST `/tools/<barcode>/edit` - Bearbeiten
- POST `/tools/<barcode>/delete` - Löschen
- GET `/tools/search` - Suche

## Mitarbeiter (/workers)
- GET `/workers` - Übersicht
- GET, POST `/workers/add` - Hinzufügen
- GET `/workers/<barcode>` - Details
- GET, POST `/workers/<barcode>/edit` - Bearbeiten

## Historie
- GET `/history` - Ausleih-Historie

## Startseite
- GET `/` - Weiterleitung zur Werkzeug-Übersicht

## Zugriffsrechte
- Admin-Bereiche erfordern Admin-Rechte (`@admin_required`)
- Geschützte Bereiche erfordern Login (`@login_required`)

## Parameter-Erklärung
- `<barcode>`: Barcode-ID des jeweiligen Items
- Alle POST-Routen erwarten entsprechende Formulardaten
- API-Routen erwarten/liefern JSON-Daten 