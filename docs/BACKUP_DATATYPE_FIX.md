# Backup Datentyp-Konsistenz Fix

## Problem
Bei der Erstellung und Wiederherstellung von Backups wurden Datentypen nicht korrekt behandelt:
- `ObjectId` Felder wurden als Strings exportiert
- `datetime` Objekte wurden als Strings exportiert
- Bei der Wiederherstellung blieben diese als Strings, was zu Dashboard-Problemen führte

## Lösung
Implementierung eines robusten Backup-Systems mit Datentyp-Erhaltung:

### 1. Neue Backup-Funktionen
- `_serialize_for_backup()`: Serialisiert Objekte mit Datentyp-Informationen
- `_deserialize_from_backup()`: Deserialisiert mit Datentyp-Wiederherstellung
- Unterstützung für alte Backup-Formate mit automatischer Konvertierung

### 2. Verbesserte Datentyp-Behandlung
- **ObjectId Konvertierung**: Strings werden automatisch zu ObjectId konvertiert
- **Datetime Konvertierung**: Unterstützt verschiedene Datetime-Formate
- **Rückwärtskompatibilität**: Alte Backups werden automatisch konvertiert

### 3. Automatische Dashboard-Fixes
- `AdminBackupService.fix_dashboard_after_backup()`: Behebt Inkonsistenzen nach Backup-Import
- Automatische Ausführung nach jedem Backup-Import

## Neue Features (Version 0.4.0)

### Alte Backup-Unterstützung
Das System erkennt automatisch alte Backup-Formate und konvertiert:
- String `_id` Felder zu ObjectId
- String Datetime-Felder zu datetime Objekten
- Unterstützt verschiedene Datetime-Formate:
  - `%Y-%m-%d %H:%M:%S.%f`
  - `%Y-%m-%d %H:%M:%S`
  - `%Y-%m-%d`
  - `%Y-%m-%dT%H:%M:%S.%f`
  - `%Y-%m-%dT%H:%M:%S`

### Verbesserte Logging
- Detaillierte Konvertierungsstatistiken
- Fehlerbehandlung mit Fallback-Optionen
- Transparente Berichterstattung über Konvertierungen

### Robuste Fehlerbehandlung
- Graceful Degradation bei Konvertierungsfehlern
- Fallback zu ursprünglichen Werten bei Problemen
- Keine Datenverluste durch fehlgeschlagene Konvertierungen

## Verwendung

### Backup erstellen
```python
backup_manager = BackupManager()
filename = backup_manager.create_backup()
```

### Backup wiederherstellen
```python
backup_manager = BackupManager()
success = backup_manager.restore_backup(file)
```

### Manuelle Dashboard-Fixes
```python
from app.services.admin_backup_service import AdminBackupService
fixes = AdminBackupService.fix_dashboard_after_backup()
```

## Technische Details

### Backup-Format (Version 2.0)
```json
{
  "metadata": {
    "version": "2.0",
    "created_at": "2024-01-01T12:00:00",
    "datatype_preservation": true,
    "collections": ["tools", "workers", ...]
  },
  "data": {
    "tools": [
      {
        "__type__": "ObjectId",
        "value": "68591682ce03d6c3fc7e5b7e"
      },
      {
        "__type__": "datetime",
        "value": "2024-01-01T12:00:00"
      }
    ]
  }
}
```

### Alte Backup-Unterstützung
Das System erkennt automatisch alte Backups und konvertiert:
```json
{
  "tools": [
    {
      "_id": "68591682ce03d6c3fc7e5b7e",  // String -> ObjectId
      "updated_at": "2024-01-01 12:00:00.000000"  // String -> datetime
    }
  ]
}
```

## Migration

### Von alten Backups
1. Alte Backups werden automatisch erkannt
2. Datentypen werden während des Imports konvertiert
3. Dashboard-Fixes werden automatisch angewendet
4. Keine manuellen Schritte erforderlich

### Zu neuen Backups
1. Neue Backups enthalten Datentyp-Informationen
2. Vollständige Datentyp-Erhaltung
3. Bessere Kompatibilität zwischen Versionen

## Vorteile

1. **Rückwärtskompatibilität**: Alte Backups funktionieren weiterhin
2. **Datentyp-Erhaltung**: Keine Datenverluste bei Export/Import
3. **Automatische Reparatur**: Dashboard-Probleme werden automatisch behoben
4. **Transparenz**: Detaillierte Logging über Konvertierungen
5. **Robustheit**: Graceful Degradation bei Problemen

## Version
- **Aktuelle Version**: Beta 0.4.0
- **Datum**: Januar 2025
- **Autor**: Andreas Klann 