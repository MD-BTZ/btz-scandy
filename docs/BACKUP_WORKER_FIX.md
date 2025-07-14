# Backup Worker-Koordination Fix

## Problem
In der Produktionsumgebung mit Gunicorn und 4 Workern führte jeder Worker das automatische Backup aus, was zu mehrfachen Backups zur gleichen Zeit führte.

## Lösung
Implementierung einer Worker-Koordination basierend auf Datenbank-Locks.

### Funktionsweise

1. **Worker-ID Generierung**: Jeder Worker erhält eine eindeutige ID basierend auf Hostname, PID und Zufallszahl
2. **Lock-Mechanismus**: Vor jedem Backup wird versucht, einen Lock in der Datenbank zu setzen
3. **Nur ein Worker**: Nur der Worker, der den Lock erfolgreich setzt, führt das Backup aus
4. **Automatische Bereinigung**: Abgelaufene Locks werden alle 10 Minuten bereinigt

### Implementierte Änderungen

#### `app/utils/auto_backup.py`

- **Worker-ID System**: `_generate_worker_id()` erstellt eindeutige Worker-IDs
- **Lock-Mechanismus**: `_is_primary_worker()` prüft ob dieser Worker das Backup ausführen soll
- **Lock-Freigabe**: `_release_backup_lock()` gibt den Lock nach dem Backup frei
- **Lock-Bereinigung**: `_cleanup_expired_locks()` entfernt abgelaufene Locks

#### Backup-Ausführung

```python
# Prüfe ob dieser Worker das Backup ausführen soll
if not self._is_primary_worker():
    logger.info(f"Worker {self.worker_id} überspringt Backup (nicht primär)")
    return

# Backup erstellen...
# ...

finally:
    # Lock freigeben
    self._release_backup_lock()
```

### Datenbank-Schema

Neue Collection: `system_locks`

```javascript
{
  "key": "backup_running_20250115_0600",
  "worker_id": "server1-1234-5678",
  "created_at": ISODate("2025-01-15T06:00:00Z"),
  "expires_at": ISODate("2025-01-15T06:05:00Z")
}
```

### Bereinigung doppelter Backups

Das Skript `cleanup_duplicate_backups.py` entfernt bestehende doppelte Backups:

```bash
python cleanup_duplicate_backups.py
```

### Vorteile

1. **Keine doppelten Backups**: Nur ein Worker führt das Backup aus
2. **Robust**: Fallback auf Backup-Ausführung bei Lock-Fehlern
3. **Automatische Bereinigung**: Abgelaufene Locks werden entfernt
4. **Logging**: Detaillierte Logs für Debugging

### Monitoring

- Logs in `logs/auto_backup.log`
- Worker-IDs in den Logs sichtbar
- Lock-Status in der Datenbank einsehbar

### Deployment

Nach dem Deployment:

1. Skript ausführen um bestehende doppelte Backups zu bereinigen
2. Automatisches Backup-System neu starten
3. Logs überwachen um sicherzustellen, dass nur ein Worker Backups erstellt 