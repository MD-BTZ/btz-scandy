# Scandy Working Installer

## Übersicht

Der `install_working.sh` ist ein 100% funktionierender Installer, der auf den bewährten alten Installern basiert. Er verwendet eine konsistente Namenskonvention und vermeidet die Hostname-Probleme der vorherigen Version.

## Warum funktioniert dieser Installer?

### 1. Konsistente Namenskonvention
- **Service-Name**: `mongodb-{instance}` (z.B. `mongodb-scandy`)
- **Container-Name**: `scandy-mongodb-{instance}` (z.B. `scandy-mongodb-scandy`)
- **Hostname in URI**: Exakt der Service-Name (z.B. `mongodb-scandy`)

### 2. Bewährte Struktur
- Basierend auf den funktionierenden alten Installern
- Verwendet die gleiche Namenskonvention wie `docker-compose-instance2.yml`
- Keine Inkonsistenzen zwischen Service-Namen und Hostnamen

### 3. Robuste Konfiguration
- Automatische Passwort-Generierung
- Sichere Umgebungsvariablen
- Health Checks für alle Services

## Installation

### Standard-Installation
```bash
./install_working.sh
```

### Installation mit Instance-Name
```bash
./install_working.sh -n verwaltung
```

### Installation mit Custom Ports
```bash
./install_working.sh -n werkstatt -p 8080 -m 27018 -e 8082
```

### Update-Modus
```bash
./install_working.sh -u
```

## Optionen

| Option | Beschreibung | Standard |
|--------|-------------|----------|
| `-n, --name NAME` | Instance-Name | `scandy` |
| `-p, --port PORT` | Web-App Port | `5000` |
| `-m, --mongodb-port PORT` | MongoDB Port | `27017` |
| `-e, --express-port PORT` | Mongo Express Port | `8081` |
| `-f, --force` | Bestehende Installation überschreiben | `false` |
| `-u, --update` | Nur App aktualisieren | `false` |

## Port-Berechnung

Bei Verwendung eines Instance-Namens werden Ports automatisch berechnet:

- **Web-Port**: `5000 + Instance-Nummer`
- **MongoDB-Port**: `27017 + Instance-Nummer`
- **Mongo Express-Port**: `8081 + Instance-Nummer`

Beispiele:
- `verwaltung` → Web: 5001, MongoDB: 27018, Express: 8082
- `werkstatt` → Web: 5002, MongoDB: 27019, Express: 8083

## Docker Compose Struktur

### Services
```yaml
services:
  mongodb-{instance}:          # Service-Name
    container_name: scandy-mongodb-{instance}
    # ...

  mongo-express-{instance}:    # Service-Name
    container_name: scandy-mongo-express-{instance}
    # ...

  app-{instance}:              # Service-Name
    container_name: scandy-app-{instance}
    environment:
      - MONGODB_URI=mongodb://${MONGO_INITDB_ROOT_USERNAME}:${MONGO_INITDB_ROOT_PASSWORD}@mongodb-{instance}:27017/${MONGODB_DB}
    # ...
```

### Wichtige Punkte
1. **Service-Name** = Hostname in der URI
2. **Container-Name** = Eindeutiger Container-Name
3. **Netzwerk** = `scandy-network-{instance}`
4. **Volumes** = `{service}_data_{instance}`

## .env-Datei

Die `.env`-Datei wird automatisch erstellt mit:

```env
# MongoDB Konfiguration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=<generiertes_sicheres_passwort>
MONGO_INITDB_DATABASE={instance}_scandy
MONGODB_DB={instance}_scandy

# System-Namen
SYSTEM_NAME=Scandy {instance}
TICKET_SYSTEM_NAME=Aufgaben {instance}
TOOL_SYSTEM_NAME=Werkzeuge {instance}
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter {instance}

# Sicherheit
SECRET_KEY=<generiertes_sicheres_secret>
```

## Management

### Einzelne Instance verwalten
```bash
./manage.sh start
./manage.sh status
./manage.sh logs
./manage.sh update
./manage.sh backup
./manage.sh shell
./manage.sh clean
```

### Alle Instances verwalten
```bash
./manage_all_instances.sh list
./manage_all_instances.sh status
./manage_all_instances.sh start verwaltung
```

## Beispiel-Setup

### Szenario: Drei Instances
```bash
# 1. Verwaltung
./install_working.sh -n verwaltung

# 2. Werkstatt
./install_working.sh -n werkstatt -p 8080 -m 27018 -e 8082

# 3. BTZ
./install_working.sh -n btz
```

### Resultierende Konfiguration

| Instance | Service-Name | Container-Name | Web-Port | MongoDB-Port | Express-Port |
|----------|-------------|----------------|----------|--------------|--------------|
| verwaltung | `mongodb-verwaltung` | `scandy-mongodb-verwaltung` | 5001 | 27018 | 8082 |
| werkstatt | `mongodb-werkstatt` | `scandy-mongodb-werkstatt` | 8080 | 27018 | 8082 |
| btz | `mongodb-btz` | `scandy-mongodb-btz` | 5003 | 27020 | 8084 |

## Troubleshooting

### Port-Konflikte
```bash
# Prüfe Port-Verfügbarkeit
lsof -i :5000
lsof -i :27017
lsof -i :8081

# Verwende andere Ports
./install_working.sh -p 8080 -m 27018 -e 8082
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

### Datenbank-Probleme
```bash
# MongoDB-Container prüfen
docker compose exec mongodb-{instance} mongosh

# Datenbank zurücksetzen
docker compose down -v
docker compose up -d
```

## Vorteile

### 1. Konsistenz
- Service-Name = Hostname in URI
- Keine Inkonsistenzen zwischen verschiedenen Namensräumen

### 2. Bewährt
- Basierend auf funktionierenden alten Installern
- Getestete Namenskonvention

### 3. Robust
- Automatische Passwort-Generierung
- Health Checks für alle Services
- Sichere Umgebungsvariablen

### 4. Einfach
- Klare Namenskonvention
- Automatische Port-Berechnung
- Einfache Verwaltung

## Migration von alter Installation

### 1. Backup erstellen
```bash
./manage.sh backup
```

### 2. Neue Installation
```bash
./install_working.sh -n {instance}
```

### 3. Daten migrieren
```bash
# Daten exportieren
docker compose exec mongodb-{old_instance} mongodump --out /backup

# Daten importieren
docker compose exec mongodb-{new_instance} mongorestore /backup
```

## Best Practices

### 1. Namenskonvention
- Verwende beschreibende Instance-Namen (z.B. `verwaltung`, `werkstatt`, `btz`)
- Vermeide Sonderzeichen und Leerzeichen

### 2. Ports
- Verwende automatische Port-Berechnung für Multi-Instance-Setups
- Dokumentiere manuelle Port-Zuweisungen

### 3. Sicherheit
- Ändere Standard-Passwörter in Produktion
- Verwende sichere Secret Keys
- Implementiere regelmäßige Backups

### 4. Monitoring
- Überwache Container-Health
- Prüfe regelmäßig Logs
- Monitoriere Ressourcen-Verbrauch

## Support

Bei Problemen:

1. **Logs prüfen**: `./manage.sh logs`
2. **Status prüfen**: `./manage.sh status`
3. **Container neustarten**: `./manage.sh restart`
4. **Komplett neu installieren**: `./manage.sh clean` + Neuinstallation

## Changelog

### Version 1.0
- Basierend auf bewährten alten Installern
- Konsistente Namenskonvention
- Automatische Port-Berechnung
- Robuste Fehlerbehandlung
- Sichere Passwort-Generierung 