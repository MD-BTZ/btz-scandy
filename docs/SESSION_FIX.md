# Session-Fix für Multi-Instance Setup

## Problem

Bei Multi-Instance-Setups traten Session-Fehler auf:
```
struct error unpack requires a buffer of 4 bytes
warning root: exception raised while handling cache file app/app/flask_session
```

## Ursache

Mehrere Instanzen versuchten, auf dieselben Session-Dateien zuzugreifen oder hatten Session-Konflikte.

## Lösung

### 1. Instance-spezifische Session-Konfiguration

Das `install_multi_instance.sh` Skript wurde erweitert um:

**Session-Umgebungsvariablen:**
```bash
SESSION_FILE_DIR=/app/app/flask_session
SESSION_TYPE=filesystem
SESSION_PERMANENT=True
PERMANENT_SESSION_LIFETIME=86400
```

**Docker-Environment:**
```yaml
environment:
  - SESSION_FILE_DIR=${SESSION_FILE_DIR}
  - SESSION_TYPE=${SESSION_TYPE}
  - SESSION_PERMANENT=${SESSION_PERMANENT}
  - PERMANENT_SESSION_LIFETIME=${PERMANENT_SESSION_LIFETIME}
```

### 2. Separate Session-Volumes

Jede Instanz erhält eigene Session-Volumes:
```yaml
volumes:
  app_sessions_verwaltung:/app/app/flask_session
  app_sessions_werkstatt:/app/app/flask_session
```

### 3. Flask-Konfiguration angepasst

`app/config/config.py` verwendet jetzt Umgebungsvariablen:
```python
SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')
SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', os.path.join(BASE_DIR, 'app', 'flask_session'))
SESSION_PERMANENT = os.environ.get('SESSION_PERMANENT', 'True').lower() == 'true'
PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '86400'))
```

## Anwendung

### Neue Instanzen installieren

```bash
# Neue Instanz mit Session-Fix
./install_multi_instance.sh -n verwaltung -p 5001 -m 27018 -e 8082
```

### Bestehende Session-Probleme beheben

```bash
# Session-Cleanup ausführen
./cleanup_sessions.sh

# Instanzen neu starten
./manage.sh start                    # Haupt-Instanz
cd verwaltung && ./manage.sh start   # Verwaltung-Instanz
cd werkstatt && ./manage.sh start    # Werkstatt-Instanz
```

### Manueller Session-Reset

```bash
# Alle Container stoppen
docker compose down

# Session-Dateien löschen
find app/flask_session -name "*.session" -delete

# Container neu starten
docker compose up -d
```

## Verzeichnis-Struktur

```
Scandy2/
├── app/flask_session/           # Haupt-Instanz Sessions
├── verwaltung/
│   └── app/flask_session/      # Verwaltung-Instanz Sessions
└── werkstatt/
    └── app/flask_session/      # Werkstatt-Instanz Sessions
```

## Troubleshooting

### Session-Fehler nach Update

1. **Cleanup ausführen:**
   ```bash
   ./cleanup_sessions.sh
   ```

2. **Container neu starten:**
   ```bash
   ./manage.sh restart
   ```

### Session-Dateien manuell löschen

```bash
# Haupt-Instanz
rm -rf app/flask_session/*.session

# Verwaltung-Instanz
rm -rf verwaltung/app/flask_session/*.session

# Werkstatt-Instanz
rm -rf werkstatt/app/flask_session/*.session
```

### Docker Volume Reset

```bash
# Volumes löschen (ALLE Daten gehen verloren!)
docker compose down -v
docker volume prune -f

# Neu installieren
./install_multi_instance.sh -n verwaltung -f
```

## Best Practices

1. **Regelmäßige Cleanups:** Führen Sie `./cleanup_sessions.sh` regelmäßig aus
2. **Separate Instanzen:** Verwenden Sie immer `install_multi_instance.sh` für neue Instanzen
3. **Backup vor Cleanup:** Erstellen Sie Backups vor Session-Cleanups
4. **Monitoring:** Überwachen Sie Session-Dateien auf Größe und Anzahl

## Technische Details

### Session-Typen

- **filesystem:** Session-Dateien auf Disk (Standard)
- **redis:** Redis-Server (nicht implementiert)
- **mongodb:** MongoDB-Sessions (nicht implementiert)

### Session-Lifetime

- **Standard:** 86400 Sekunden (24 Stunden)
- **Konfigurierbar:** Über `PERMANENT_SESSION_LIFETIME` Umgebungsvariable

### Session-Sicherheit

- **HTTPOnly:** Verhindert JavaScript-Zugriff
- **Secure:** Nur über HTTPS (in Produktion)
- **SameSite:** CSRF-Schutz 