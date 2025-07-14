# Scandy Multi-Instance Setup

## Übersicht

Das Scandy-System unterstützt die Installation mehrerer Instances auf einem Server. Jede Instance hat:

- Eigene Container-Namen
- Separate Ports
- Individuelle Datenbanken
- Isolierte Volumes und Networks

## Installation

### Einheitliches Installationsskript

```bash
# Standard-Installation
./install_unified.sh

# Installation mit Instance-Name (automatische Port-Berechnung)
./install_unified.sh -n verwaltung

# Installation mit custom Ports
./install_unified.sh -n werkstatt -p 8080 -m 27018 -e 8082

# Update-Modus (keine Daten löschen)
./install_unified.sh -u
```

### Optionen

| Option | Beschreibung | Standard |
|--------|-------------|----------|
| `-n, --name NAME` | Instance-Name | `scandy` |
| `-p, --port PORT` | Web-App Port | `5000` |
| `-m, --mongodb-port PORT` | MongoDB Port | `27017` |
| `-e, --express-port PORT` | Mongo Express Port | `8081` |
| `-f, --force` | Bestehende Installation überschreiben | `false` |
| `-u, --update` | Nur App aktualisieren | `false` |

### Port-Berechnung

Bei Verwendung eines Instance-Namens werden Ports automatisch berechnet:

- **Web-Port**: `5000 + Instance-Nummer`
- **MongoDB-Port**: `27017 + Instance-Nummer`
- **Mongo Express-Port**: `8081 + Instance-Nummer`

Beispiele:
- `verwaltung` → Web: 5001, MongoDB: 27018, Express: 8082
- `werkstatt` → Web: 5002, MongoDB: 27019, Express: 8083

## Multi-Instance Manager

### Verwaltung aller Instances

```bash
# Alle Instances auflisten
./manage_all_instances.sh list

# Status aller Instances
./manage_all_instances.sh status

# Spezifische Instance starten
./manage_all_instances.sh start verwaltung

# Alle Instances stoppen
./manage_all_instances.sh stop

# Neue Instance installieren
./manage_all_instances.sh install btz -p 8080
```

### Befehle

| Befehl | Beschreibung |
|--------|-------------|
| `list` | Alle Instances auflisten |
| `status [INSTANCE]` | Status aller oder einer Instance |
| `start [INSTANCE]` | Alle oder eine Instance starten |
| `stop [INSTANCE]` | Alle oder eine Instance stoppen |
| `restart [INSTANCE]` | Alle oder eine Instance neustarten |
| `logs [INSTANCE]` | Logs aller oder einer Instance |
| `update [INSTANCE]` | Alle oder eine Instance aktualisieren |
| `install NAME [OPTIONS]` | Neue Instance installieren |

## Instance-Verwaltung

### Einzelne Instance verwalten

Jede Instance hat ihr eigenes `manage.sh` Skript:

```bash
# In das Instance-Verzeichnis wechseln
cd /path/to/instance

# Instance-spezifische Befehle
./manage.sh start
./manage.sh status
./manage.sh logs
./manage.sh info
./manage.sh update
./manage.sh backup
./manage.sh shell
./manage.sh clean
```

## Beispiel-Setup

### Szenario: Drei Instances

```bash
# 1. Verwaltung (Standard-Ports)
./install_unified.sh -n verwaltung

# 2. Werkstatt (Custom-Ports)
./install_unified.sh -n werkstatt -p 8080 -m 27018 -e 8082

# 3. BTZ (Automatische Port-Berechnung)
./install_unified.sh -n btz
```

### Resultierende Konfiguration

| Instance | Web-Port | MongoDB-Port | Express-Port | URL |
|----------|----------|--------------|--------------|-----|
| verwaltung | 5001 | 27018 | 8082 | http://localhost:5001 |
| werkstatt | 8080 | 27018 | 8082 | http://localhost:8080 |
| btz | 5003 | 27020 | 8084 | http://localhost:5003 |

## Datenbank-Isolation

Jede Instance hat:

- **Eigene Datenbank**: `{instance_name}_scandy`
- **Separate Volumes**: `mongodb_data_{instance_name}`
- **Isolierte Networks**: `scandy-network-{instance_name}`
- **Individuelle Container**: `scandy-app-{instance_name}`

## Sicherheit

### Passwort-Generierung

Das Skript generiert automatisch:
- Sichere MongoDB-Passwörter
- Flask Secret Keys

### Produktions-Empfehlungen

1. **Passwörter ändern**: Ändere die Standard-Passwörter in `.env`
2. **Firewall**: Konfiguriere Firewall-Regeln für die Ports
3. **SSL/TLS**: Verwende Reverse-Proxy mit SSL-Terminierung
4. **Backups**: Regelmäßige Backups aller Instances

## Troubleshooting

### Port-Konflikte

```bash
# Prüfe Port-Verfügbarkeit
lsof -i :5000
lsof -i :27017
lsof -i :8081

# Verwende andere Ports
./install_unified.sh -p 8080 -m 27018 -e 8082
```

### Container-Probleme

```bash
# Container-Logs anzeigen
docker compose logs

# Container neustarten
docker compose restart

# Container komplett neu erstellen
docker compose down
docker compose up -d --build
```

### Multi-Instance-Probleme

```bash
# Alle Instances auflisten
./manage_all_instances.sh list

# Spezifische Instance prüfen
./manage_all_instances.sh status verwaltung

# Instance neu installieren
./manage_all_instances.sh install verwaltung
```

## Backup und Migration

### Backup erstellen

```bash
# Einzelne Instance
./manage.sh backup

# Alle Instances
./manage_all_instances.sh backup
```

### Migration

```bash
# 1. Backup erstellen
./manage.sh backup

# 2. Daten exportieren
docker compose exec scandy-mongodb-{instance} mongodump --out /backup

# 3. Auf neuem Server installieren
./install_unified.sh -n {instance}

# 4. Daten importieren
docker compose exec scandy-mongodb-{instance} mongorestore /backup
```

## Monitoring

### Health Checks

Alle Container haben Health Checks:
- **MongoDB**: Ping-Test alle 10s
- **App**: HTTP-Health-Check alle 30s

### Logs

```bash
# Container-Logs
docker compose logs -f

# Spezifische Service-Logs
docker compose logs -f scandy-app-{instance}
docker compose logs -f scandy-mongodb-{instance}
```

## Best Practices

### Installation

1. **Planung**: Definiere Port-Bereiche und Instance-Namen
2. **Verzeichnisse**: Verwende separate Verzeichnisse für jede Instance
3. **Dokumentation**: Dokumentiere Konfigurationen und Zugangsdaten
4. **Backup-Strategie**: Implementiere regelmäßige Backups

### Wartung

1. **Updates**: Regelmäßige Updates aller Instances
2. **Monitoring**: Überwachung der System-Ressourcen
3. **Logs**: Regelmäßige Log-Analyse
4. **Sicherheit**: Regelmäßige Sicherheits-Updates

## Support

Bei Problemen:

1. **Logs prüfen**: `./manage.sh logs`
2. **Status prüfen**: `./manage.sh status`
3. **Container neustarten**: `./manage.sh restart`
4. **Komplett neu installieren**: `./manage.sh clean` + Neuinstallation 