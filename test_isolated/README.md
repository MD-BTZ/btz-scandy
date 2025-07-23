# Scandy test_isolated Instance

Diese Instanz ist vollständig isoliert von anderen Scandy-Instanzen.

## Services

- **Web-App**: http://localhost:5003
- **MongoDB**: localhost:27020
- **Mongo Express**: http://localhost:8084

## Management

```bash
# Starten
./manage.sh start

# Status prüfen
./manage.sh status

# Logs anzeigen
./manage.sh logs

# Stoppen
./manage.sh stop
```

## Isolierung

Diese Instanz verwendet:
- Eigene MongoDB-Datenbank: `scandy_test_isolated`
- Eigene Session-Verzeichnisse: `flask_session_test_isolated`
- Eigene Docker-Netzwerke: `scandy-network-test_isolated`
- Eigene Volumes für Daten, Backups, Logs und Sessions
- Eigene Ports für alle Services

## Backup

```bash
./manage.sh backup
```

## Update

```bash
./manage.sh update
```
