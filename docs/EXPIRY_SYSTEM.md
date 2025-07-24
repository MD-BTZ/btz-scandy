# Ablaufdatum-System für Scandy

## Übersicht

Das Ablaufdatum-System ermöglicht es, automatische Ablaufdaten für Benutzerkonten und Jobanzeigen zu setzen. Abgelaufene Konten und Jobs werden automatisch deaktiviert und können optional gelöscht werden.

## Funktionen

### Benutzerkonten
- **Ablaufdatum setzen**: Administratoren können für jeden Benutzer ein Ablaufdatum festlegen
- **Automatische Deaktivierung**: Abgelaufene Konten werden automatisch deaktiviert
- **Warnungen**: System zeigt Warnungen für bald ablaufende Konten an
- **Automatische Bereinigung**: Abgelaufene Konten können automatisch gelöscht werden

### Jobanzeigen
- **Ablaufdatum setzen**: Job-Ersteller können ein Ablaufdatum für ihre Anzeigen festlegen
- **Automatische Deaktivierung**: Abgelaufene Jobs werden automatisch deaktiviert
- **Warnungen**: System zeigt Warnungen für bald ablaufende Jobs an
- **Automatische Bereinigung**: Abgelaufene Jobs können automatisch gelöscht werden

## Technische Implementierung

### Datenbank-Schema

#### Benutzer (users collection)
```javascript
{
  "_id": ObjectId,
  "username": "string",
  "role": "string",
  "is_active": boolean,
  "expires_at": Date,  // NEU: Ablaufdatum
  "created_at": Date,
  "updated_at": Date,
  // ... weitere Felder
}
```

#### Jobs (jobs collection)
```javascript
{
  "_id": ObjectId,
  "title": "string",
  "company": "string",
  "is_active": boolean,
  "expires_at": Date,  // NEU: Ablaufdatum
  "created_at": Date,
  "updated_at": Date,
  // ... weitere Felder
}
```

### Modelle

#### User-Modell (app/models/user.py)
```python
class User(UserMixin):
    def __init__(self, user_data=None):
        # ... bestehende Felder ...
        self.expires_at = user_data.get('expires_at')
        
    @property
    def is_active(self):
        # Prüfe Ablaufdatum
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return self._active
    
    @property
    def is_expired(self):
        """Prüft ob der Account abgelaufen ist"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def days_until_expiry(self):
        """Gibt die Anzahl der Tage bis zum Ablauf zurück"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now()
        return delta.days
```

#### Job-Modell (app/models/job.py)
```python
class Job:
    def __init__(self, data=None):
        # ... bestehende Felder ...
        self.expires_at = data.get('expires_at')
        
    @property
    def is_expired(self):
        """Prüft ob der Job abgelaufen ist"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def days_until_expiry(self):
        """Gibt die Anzahl der Tage bis zum Ablauf zurück"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now()
        return delta.days
```

### Services

#### CleanupService (app/services/cleanup_service.py)
```python
class CleanupService:
    @staticmethod
    def cleanup_all() -> Dict[str, Any]:
        """Führt alle Cleanup-Operationen aus"""
        
    @staticmethod
    def get_expiry_warnings() -> Dict[str, Any]:
        """Gibt Warnungen für bald ablaufende Accounts und Jobs zurück"""
        
    @staticmethod
    def get_expiry_statistics() -> Dict[str, Any]:
        """Gibt Statistiken zu ablaufenden Accounts und Jobs zurück"""
```

#### AdminUserService (erweitert)
```python
class AdminUserService:
    @staticmethod
    def cleanup_expired_users() -> Tuple[int, str]:
        """Bereinigt abgelaufene Benutzerkonten"""
```

#### JobService (erweitert)
```python
class JobService:
    @staticmethod
    def cleanup_expired_jobs() -> Tuple[int, str]:
        """Bereinigt abgelaufene Jobs"""
```

## Admin-Interface

### Ablaufdatum-Verwaltung
- **Route**: `/admin/expiry_management`
- **Template**: `app/templates/admin/expiry_management.html`
- **Funktionen**:
  - Statistiken anzeigen
  - Warnungen für bald ablaufende Accounts
  - Manuelle Bereinigung auslösen
  - Links zu Benutzer- und Job-Verwaltung

### Benutzer-Formular (erweitert)
- **Template**: `app/templates/admin/user_form.html`
- **Neues Feld**: `expires_at` (datetime-local)
- **Funktionen**:
  - Ablaufdatum setzen/bearbeiten
  - Validierung des Datums
  - Anzeige des aktuellen Ablaufdatums

### Benutzer-Liste (erweitert)
- **Template**: `app/templates/admin/users.html`
- **Neue Spalte**: Ablaufdatum
- **Anzeige**:
  - Unbegrenzt (kein Ablaufdatum)
  - Datum (normal)
  - Warnung (≤ 7 Tage)
  - Abgelaufen (überfällig)

## Job-Interface

### Job-Formulare (erweitert)
- **Templates**: `app/templates/jobs/create.html`, `app/templates/jobs/edit.html`
- **Neues Feld**: `expires_at` (datetime-local)
- **Funktionen**:
  - Ablaufdatum setzen/bearbeiten
  - Validierung des Datums
  - Anzeige des aktuellen Ablaufdatums

## Automatische Bereinigung

### Cron-Job Script
- **Datei**: `cleanup_expired.py`
- **Funktion**: Automatische Bereinigung abgelaufener Daten
- **Logging**: `logs/cleanup.log`

### Cron-Job Einrichtung
```bash
# Täglich um 2:00 Uhr ausführen
0 2 * * * /usr/bin/python3 /path/to/scandy/cleanup_expired.py

# Oder wöchentlich am Sonntag um 3:00 Uhr
0 3 * * 0 /usr/bin/python3 /path/to/scandy/cleanup_expired.py
```

## API-Endpunkte

### Ablaufwarnungen
- **Route**: `/admin/api/expiry_warnings`
- **Methode**: GET
- **Berechtigung**: Admin
- **Response**: JSON mit Warnungen für bald ablaufende Accounts

### Ablauf-Statistiken
- **Route**: `/admin/api/expiry_statistics`
- **Methode**: GET
- **Berechtigung**: Admin
- **Response**: JSON mit Statistiken zu ablaufenden Accounts

## Sicherheitsaspekte

### Admin-Schutz
- Admin-Benutzer werden bei der automatischen Bereinigung **nicht** gelöscht
- Auch abgelaufene Admin-Accounts bleiben erhalten
- Nur manuelle Löschung von Admin-Accounts möglich

### Datenintegrität
- Abgelaufene Konten werden nur deaktiviert, nicht sofort gelöscht
- Soft-Delete für bessere Datenverfolgung
- Logging aller Cleanup-Operationen

## Konfiguration

### Umgebungsvariablen
```bash
# Cleanup-Logging aktivieren
CLEANUP_LOGGING=true

# Automatische Bereinigung deaktivieren (für Tests)
DISABLE_AUTO_CLEANUP=false
```

### Einstellungen
- **Warnungszeitraum**: 7 Tage vor Ablauf
- **Bereinigung**: Täglich oder wöchentlich
- **Logging**: Alle Cleanup-Operationen werden geloggt

## Migration

### Bestehende Daten
- Bestehende Benutzer und Jobs ohne Ablaufdatum bleiben unbegrenzt
- Keine automatische Zuweisung von Ablaufdaten
- Manuelle Bearbeitung erforderlich für Ablaufdaten

### Datenbank-Migration
```javascript
// Optional: Standard-Ablaufdatum für neue Benutzer setzen
db.users.updateMany(
  { "expires_at": { "$exists": false } },
  { "$set": { "expires_at": null } }
);

// Optional: Standard-Ablaufdatum für neue Jobs setzen
db.jobs.updateMany(
  { "expires_at": { "$exists": false } },
  { "$set": { "expires_at": null } }
);
```

## Troubleshooting

### Häufige Probleme

1. **Ablaufdatum wird nicht gespeichert**
   - Prüfen Sie das Datumsformat (YYYY-MM-DDTHH:MM)
   - Stellen Sie sicher, dass das Feld nicht leer ist

2. **Automatische Bereinigung funktioniert nicht**
   - Prüfen Sie die Cron-Job-Konfiguration
   - Überprüfen Sie die Logs in `logs/cleanup.log`
   - Stellen Sie sicher, dass die Berechtigungen korrekt sind

3. **Warnungen werden nicht angezeigt**
   - Prüfen Sie die Datenbankverbindung
   - Überprüfen Sie die Ablaufdatum-Felder in der Datenbank
   - Stellen Sie sicher, dass die Zeitstempel korrekt sind

### Debugging

```python
# Manuelle Bereinigung testen
from app.services.cleanup_service import CleanupService
results = CleanupService.cleanup_all()
print(results)

# Warnungen abrufen
warnings = CleanupService.get_expiry_warnings()
print(warnings)

# Statistiken abrufen
stats = CleanupService.get_expiry_statistics()
print(stats)
```

## Zukünftige Erweiterungen

### Geplante Features
- **E-Mail-Benachrichtigungen**: Warnungen per E-Mail vor Ablauf
- **Erweiterte Statistiken**: Detaillierte Ablauf-Statistiken
- **Bulk-Operationen**: Massenbearbeitung von Ablaufdaten
- **Templates**: Vordefinierte Ablaufzeiträume (30 Tage, 90 Tage, etc.)

### API-Erweiterungen
- **REST-API**: Vollständige API für Ablaufdatum-Verwaltung
- **Webhooks**: Benachrichtigungen bei Ablauf
- **Integration**: Anbindung an externe Systeme 