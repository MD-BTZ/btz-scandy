# Versionscheck für Scandy

## Übersicht

Der Versionscheck prüft automatisch, ob Updates für Scandy verfügbar sind, indem er die lokale Version mit der neuesten Version auf GitHub vergleicht.

## Funktionsweise

### Versionsverwaltung

- **Lokale Version**: Wird in `app/config/version.py` definiert
- **GitHub-Version**: Wird von der GitHub API oder direkt aus der `version.py` Datei abgerufen
- **Vergleich**: Automatischer Vergleich der Versionen

### API-Endpunkte

#### `/admin/version/check`
- **Methode**: GET
- **Zugriff**: Admin-Berechtigung erforderlich
- **Rückgabe**: JSON mit Versionsstatus

```json
{
  "status": "up_to_date|update_available|error",
  "message": "Beschreibung",
  "local_version": "beta 0.3.2",
  "github_version": "beta 0.3.3",
  "update_url": "https://github.com/woschj/Scandy2/releases/latest"
}
```

#### `/admin/version/info`
- **Methode**: GET
- **Zugriff**: Admin-Berechtigung erforderlich
- **Rückgabe**: Detaillierte Versionsinformationen

```json
{
  "local_version": "beta 0.3.2",
  "github_version": "beta 0.3.3",
  "is_up_to_date": false,
  "update_available": true,
  "error": null
}
```

### Admin-Interface

#### Dashboard-Integration
- **Ort**: Admin-Dashboard unter "System-Status"
- **Anzeige**: Aktuelle Version und Update-Status
- **Link**: Direkter Zugang zur Versionscheck-Seite

#### Versionscheck-Seite
- **URL**: `/admin/version`
- **Features**:
  - Live-Versionsstatus
  - Detaillierte Versionsinformationen
  - Update-Anleitung
  - Automatische Aktualisierung alle 5 Minuten

## Implementierung

### VersionChecker Klasse

```python
from app.utils.version_checker import VersionChecker

# Globale Instanz
version_checker = VersionChecker()

# Versionscheck durchführen
result = version_checker.check_for_updates()
```

### GitHub-Integration

1. **GitHub API**: Versucht zuerst die neueste Release-Version abzurufen
2. **Fallback**: Liest direkt aus der `version.py` Datei auf GitHub
3. **Fehlerbehandlung**: Robuste Fehlerbehandlung bei Netzwerkproblemen

### Versionsformat

- **Aktuell**: `"beta 0.3.2"`
- **Semantic Versioning**: Unterstützt für zukünftige Releases
- **Flexibel**: Verschiedene Versionsformate möglich

## Verwendung

### Für Administratoren

1. **Dashboard**: Versionsstatus wird automatisch angezeigt
2. **Versionscheck-Seite**: Detaillierte Informationen und Update-Anleitung
3. **Automatische Prüfung**: Alle 5 Minuten wird der Status aktualisiert

### Für Entwickler

```python
# Versionscheck programmatisch
from app.utils.version_checker import check_version

result = check_version()
if result['status'] == 'update_available':
    print(f"Update verfügbar: {result['github_version']}")
```

## Konfiguration

### Version ändern

```python
# app/config/version.py
VERSION = "beta 0.3.3"  # Neue Version
```

### GitHub-Repository

- **Repository**: `woschj/Scandy2`
- **Branch**: `main`
- **Version-Datei**: `app/config/version.py`

## Fehlerbehandlung

### Netzwerkprobleme
- Timeout nach 10 Sekunden
- Fallback auf lokale Version
- Benutzerfreundliche Fehlermeldungen

### GitHub-API-Limits
- Automatischer Fallback auf direkte Datei-Abfrage
- Caching für bessere Performance

## Sicherheit

- **Admin-Zugriff**: Nur Administratoren können Versionschecks durchführen
- **Rate Limiting**: Automatische Begrenzung der API-Aufrufe
- **Fehlerbehandlung**: Sichere Behandlung von Netzwerkfehlern

## Monitoring

### Logs
- Versionscheck-Logs in `logs/auto_backup.log`
- Fehler werden detailliert protokolliert

### Dashboard
- Live-Status im Admin-Dashboard
- Farbkodierte Badges für schnelle Übersicht

## Zukünftige Erweiterungen

1. **Automatische Updates**: Integration mit Update-Skripten
2. **E-Mail-Benachrichtigungen**: Bei verfügbaren Updates
3. **Changelog-Integration**: Anzeige der Änderungen
4. **Rollback-Funktion**: Zurück zu vorherigen Versionen 