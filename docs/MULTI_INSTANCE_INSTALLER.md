# Multi-Instance Installer Dokumentation

## Übersicht

Das `install_multi_instance.sh` Skript erstellt separate Verzeichnisse für jede Scandy-Instanz, sodass mehrere Instanzen parallel auf einem Server laufen können, ohne sich zu überschreiben.

## Hauptfunktionen

✅ **Separate Verzeichnisse**: Jede Instanz erhält ein eigenes Verzeichnis  
✅ **Eindeutige Ports**: Automatische Port-Berechnung oder manuelle Konfiguration  
✅ **Eindeutige Container**: Jede Instanz hat eigene Container-Namen  
✅ **Eindeutige Volumes**: Separate Datenvolumes für jede Instanz  
✅ **Eindeutige Netzwerke**: Isolierte Docker-Netzwerke  
✅ **Eigene Datenbanken**: Separate MongoDB-Instanzen mit eigenen Passwörtern  
✅ **Management-Skripte**: Jede Instanz hat ihr eigenes `manage.sh`  

## Verwendung

### Grundlegende Installation

```bash
# Neue Instanz erstellen
./install_multi_instance.sh -n verwaltung

# Mit spezifischen Ports
./install_multi_instance.sh -n werkstatt -p 5001 -m 27018 -e 8082
```

### Parameter

| Parameter | Beschreibung | Standard |
|-----------|--------------|----------|
| `-n, --name` | Instance-Name | `scandy` |
| `-p, --port` | Web-App Port | `5000` |
| `-m, --mongodb-port` | MongoDB Port | `27017` |
| `-e, --express-port` | Mongo Express Port | `8081` |
| `-f, --force` | Bestehende Installation überschreiben | `false` |
| `-u, --update` | Nur App aktualisieren | `false` |

### Beispiele

```bash
# Automatische Port-Berechnung
./install_multi_instance.sh -n instance1  # Ports: 5001, 27018, 8082
./install_multi_instance.sh -n instance2  # Ports: 5002, 27019, 8083

# Manuelle Port-Konfiguration
./install_multi_instance.sh -n produktions -p 8080 -m 27020 -e 9090
./install_multi_instance.sh -n test -p 8081 -m 27021 -e 9091

# Update bestehende Instanz
./install_multi_instance.sh -u -n verwaltung
```

## Verzeichnis-Struktur

```
Scandy2/
├── .env                    # Haupt-Instanz (scandy)
├── docker-compose.yml
├── manage.sh
├── verwaltung/            # Zweite Instanz
│   ├── .env
│   ├── docker-compose.yml
│   ├── manage.sh
│   ├── data/
│   ├── backups/
│   └── logs/
└── werkstatt/            # Dritte Instanz
    ├── .env
    ├── docker-compose.yml
    ├── manage.sh
    ├── data/
    ├── backups/
    └── logs/
```

## Container-Struktur

Jede Instanz erstellt folgende Container:

- `scandy-mongodb-{INSTANCE_NAME}`
- `scandy-mongo-express-{INSTANCE_NAME}`
- `scandy-app-{INSTANCE_NAME}`

## Volumes

Jede Instanz hat eigene Volumes:

- `mongodb_data_{INSTANCE_NAME}`
- `app_uploads_{INSTANCE_NAME}`
- `app_backups_{INSTANCE_NAME}`
- `app_logs_{INSTANCE_NAME}`
- `app_sessions_{INSTANCE_NAME}`

## Netzwerke

Jede Instanz hat ein isoliertes Netzwerk:

- `scandy-network-{INSTANCE_NAME}`

## Management

### Haupt-Instanz (scandy)

```bash
# Im Hauptverzeichnis
./manage.sh start
./manage.sh stop
./manage.sh status
```

### Weitere Instanzen

```bash
# Verwaltung-Instanz
cd verwaltung
./manage.sh start
./manage.sh stop
./manage.sh status

# Werkstatt-Instanz
cd werkstatt
./manage.sh start
./manage.sh stop
./manage.sh status
```

## Port-Übersicht

| Instanz | Web-App | MongoDB | Mongo Express | Verzeichnis |
|---------|---------|---------|---------------|-------------|
| scandy | 5000 | 27017 | 8081 | `.` |
| verwaltung | 5001 | 27018 | 8082 | `verwaltung/` |
| werkstatt | 5002 | 27019 | 8083 | `werkstatt/` |

## Automatische Port-Berechnung

Wenn der Instance-Name eine Nummer enthält, werden die Ports automatisch berechnet:

- `instance1` → Ports: 5001, 27018, 8082
- `instance2` → Ports: 5002, 27019, 8083
- `instance3` → Ports: 5003, 27020, 8084

## Sicherheit

- Jede Instanz erhält ein eigenes, sicheres Passwort
- Separate Datenbanken mit eigenen Credentials
- Isolierte Netzwerke
- Eindeutige Container-Namen

## Troubleshooting

### Port-Konflikte

```bash
# Prüfe verfügbare Ports
lsof -i :5000
lsof -i :27017
lsof -i :8081

# Verwende andere Ports
./install_multi_instance.sh -n verwaltung -p 5001 -m 27018 -e 8082
```

### Verzeichnis bereits existiert

```bash
# Überschreiben erzwingen
./install_multi_instance.sh -n verwaltung -f

# Oder manuell löschen
rm -rf verwaltung
./install_multi_instance.sh -n verwaltung
```

### Container-Probleme

```bash
# Status prüfen
cd verwaltung
./manage.sh status

# Logs anzeigen
./manage.sh logs

# Container neu starten
./manage.sh restart
```

## Migration von install_working.sh

Wenn Sie bereits `install_working.sh` verwendet haben:

1. **Haupt-Instanz beibehalten**: Die bestehende Installation bleibt im Hauptverzeichnis
2. **Neue Instanzen**: Verwenden Sie `install_multi_instance.sh` für weitere Instanzen
3. **Keine Datenverluste**: Bestehende Daten bleiben erhalten

## Best Practices

1. **Eindeutige Namen**: Verwenden Sie beschreibende Instance-Namen
2. **Port-Planung**: Planen Sie Ports im Voraus, um Konflikte zu vermeiden
3. **Backups**: Erstellen Sie regelmäßig Backups jeder Instanz
4. **Updates**: Aktualisieren Sie Instanzen einzeln
5. **Monitoring**: Überwachen Sie Ressourcenverbrauch bei mehreren Instanzen 