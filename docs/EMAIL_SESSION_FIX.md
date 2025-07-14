# E-Mail Session-Fix Dokumentation

## Problem

Beim Speichern der E-Mail-Einstellungen wird der Benutzer ausgeloggt:
```
Statt das sie gespeichert werden loggt mich die app aus
```

## Ursache

Das Problem liegt daran, dass beim Speichern der E-Mail-Einstellungen die Session verloren geht oder beschädigt wird. Dies kann mehrere Ursachen haben:

1. **Session-Dateien werden beschädigt** beim Speichern
2. **Session-Konflikte** zwischen Multi-Instance-Setups
3. **Session-Persistierung** funktioniert nicht korrekt
4. **Datenbank-Operationen** beeinflussen die Session

## Lösung

### 1. Session-Persistierung in der E-Mail-Route

Die `email_settings` Route wurde erweitert um Session-Persistierung:

```python
# Session-Persistierung vor dem Speichern
current_user_id = session.get('user_id')
current_username = session.get('username')
current_role = session.get('role')
current_authenticated = session.get('is_authenticated', False)

# ... E-Mail-Einstellungen speichern ...

# Session wiederherstellen nach dem Speichern
if current_user_id:
    session['user_id'] = current_user_id
if current_username:
    session['username'] = current_username
if current_role:
    session['role'] = current_role
if current_authenticated:
    session['is_authenticated'] = current_authenticated
```

### 2. Session-Fix-Tool

Das `fix_email_session.sh` Tool bereinigt Session-Probleme:

```bash
# Session-Fix ausführen
./fix_email_session.sh

# Container neu starten
./manage.sh restart
```

### 3. Vollständige Session-Bereinigung

Bei hartnäckigen Problemen:

```bash
# Vollständige Session-Bereinigung
./cleanup_sessions.sh

# Container neu starten
./manage.sh restart
```

## Anwendung

### Sofortige Lösung

1. **Session-Fix ausführen:**
   ```bash
   ./fix_email_session.sh
   ```

2. **Container neu starten:**
   ```bash
   ./manage.sh restart
   ```

3. **E-Mail-Einstellungen testen:**
   - Gehe zu Admin → E-Mail-Einstellungen
   - Speichere Einstellungen
   - Prüfe ob Session erhalten bleibt

### Bei hartnäckigen Problemen

1. **Vollständige Bereinigung:**
   ```bash
   ./cleanup_sessions.sh
   ```

2. **Container neu starten:**
   ```bash
   ./manage.sh restart
   ```

3. **Erneut testen**

### Multi-Instance-Setup

Für mehrere Instanzen:

```bash
# Haupt-Instanz
./fix_email_session.sh
./manage.sh restart

# Verwaltung-Instanz
cd verwaltung
../fix_email_session.sh
./manage.sh restart

# Werkstatt-Instanz
cd werkstatt
../fix_email_session.sh
./manage.sh restart
```

## Debugging

### Session-Status prüfen

```bash
# Session-Debug-Route
curl http://localhost:5000/admin/debug/session
```

### Container-Logs prüfen

```bash
# App-Logs
docker logs scandy-app-scandy -f

# MongoDB-Logs
docker logs scandy-mongodb-scandy -f
```

### Session-Dateien manuell prüfen

```bash
# Session-Dateien auflisten
find app/flask_session -name "*.session" -ls

# Session-Dateien löschen
rm -rf app/flask_session/*.session
```

## Prävention

### Best Practices

1. **Regelmäßige Session-Cleanups:**
   ```bash
   # Wöchentlich ausführen
   ./cleanup_sessions.sh
   ```

2. **Session-Monitoring:**
   ```bash
   # Session-Größe überwachen
   du -sh app/flask_session/
   ```

3. **Backup vor Änderungen:**
   ```bash
   # Session-Backup erstellen
   tar -czf session_backup_$(date +%Y%m%d).tar.gz app/flask_session/
   ```

### Konfiguration

Die Session-Konfiguration ist in `app/config/config.py`:

```python
# Flask-Session
SESSION_TYPE = os.environ.get('SESSION_TYPE', 'filesystem')
SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR', os.path.join(BASE_DIR, 'app', 'flask_session'))
SESSION_PERMANENT = os.environ.get('SESSION_PERMANENT', 'True').lower() == 'true'
PERMANENT_SESSION_LIFETIME = int(os.environ.get('PERMANENT_SESSION_LIFETIME', '86400'))
```

## Troubleshooting

### Session wird immer verloren

1. **Prüfe Session-Verzeichnis:**
   ```bash
   ls -la app/flask_session/
   ```

2. **Prüfe Berechtigungen:**
   ```bash
   chmod 755 app/flask_session/
   ```

3. **Prüfe Disk-Space:**
   ```bash
   df -h
   ```

### Multi-Instance-Konflikte

1. **Separate Session-Verzeichnisse:**
   ```bash
   # Jede Instanz hat eigenes Session-Verzeichnis
   ls -la */app/flask_session/
   ```

2. **Instance-spezifische Session-Konfiguration:**
   ```bash
   # Prüfe .env-Dateien
   grep SESSION_ */env
   ```

### E-Mail-Einstellungen speichern nicht

1. **Datenbank-Verbindung prüfen:**
   ```bash
   docker logs scandy-mongodb-scandy --tail 20
   ```

2. **App-Logs prüfen:**
   ```bash
   docker logs scandy-app-scandy --tail 20
   ```

3. **Manueller Test:**
   ```bash
   # In App-Container wechseln
   docker exec -it scandy-app-scandy bash
   python -c "from app.models.mongodb_database import mongodb; print(mongodb.find_one('settings', {'key': 'email_smtp_server'}))"
   ```

## Technische Details

### Session-Mechanismus

- **filesystem:** Session-Dateien auf Disk
- **Permanent:** 24 Stunden Session-Lifetime
- **Multi-Instance:** Separate Session-Verzeichnisse

### E-Mail-Speicherung

- **Datenbank:** E-Mail-Einstellungen in `settings` Collection
- **Verschlüsselung:** Passwörter werden verschlüsselt gespeichert
- **Session-Persistierung:** Session wird vor/nach Speicherung gesichert

### Debug-Routen

- `/admin/debug/session` - Session-Informationen
- `/admin/debug/clear-session` - Session löschen
- `/admin/debug/fix-session/<username>` - Session reparieren 