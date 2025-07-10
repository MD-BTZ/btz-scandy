# Multi-Instance Setup für Scandy

## Übersicht

Jede Abteilung bekommt ihre **eigene, komplett unabhängige** Scandy-Instanz mit separater Datenbank. Das ist viel einfacher als Multi-Tenant!

## Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   BTZ System    │    │ Werkstatt System│    │Verwaltung System│
│                 │    │                 │    │                 │
│ Port: 5003      │    │ Port: 5001      │    │ Port: 5002      │
│ MongoDB: 27020  │    │ MongoDB: 27018  │    │ MongoDB: 27019  │
│ DB: btz_scandy  │    │ DB: werkstatt_  │    │ DB: verwaltung_ │
│                 │    │ scandy          │    │ scandy          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Vorteile

✅ **Komplett unabhängig** - Keine Datenvermischung  
✅ **Einfach zu verwalten** - Jede Abteilung für sich  
✅ **Keine komplexe Multi-Tenant-Logik**  
✅ **Einfache Backups** - Pro Abteilung  
✅ **Sichere Trennung** - Keine Zugriffsprobleme  
✅ **Einfache Updates** - Pro Abteilung möglich  

## Installation

### 1. Alle Systeme starten
```bash
start_all.bat
```

### 2. Einzelne Abteilung starten
```bash
# BTZ
start_btz.bat

# Werkstatt  
start_werkstatt.bat

# Verwaltung
start_verwaltung.bat
```

### 3. Alle Systeme stoppen
```bash
stop_all.bat
```

## Zugriff

| Abteilung | Web-Interface | MongoDB | Datenbank |
|-----------|---------------|---------|-----------|
| BTZ | http://localhost:5003 | localhost:27020 | btz_scandy |
| Werkstatt | http://localhost:5001 | localhost:27018 | werkstatt_scandy |
| Verwaltung | http://localhost:5002 | localhost:27019 | verwaltung_scandy |

## Datenverzeichnisse

```
data/
├── btz/           # BTZ-Daten (Uploads, Logs, etc.)
├── werkstatt/     # Werkstatt-Daten
└── verwaltung/    # Verwaltungs-Daten
```

## Backup & Restore

### Backup einer Abteilung
```bash
# BTZ Backup
docker exec btz-mongodb mongodump --out /backup/btz_$(date +%Y%m%d)

# Werkstatt Backup  
docker exec werkstatt-mongodb mongodump --out /backup/werkstatt_$(date +%Y%m%d)

# Verwaltung Backup
docker exec verwaltung-mongodb mongodump --out /backup/verwaltung_$(date +%Y%m%d)
```

### Restore einer Abteilung
```bash
# BTZ Restore
docker exec btz-mongodb mongorestore /backup/btz_20241201/

# Werkstatt Restore
docker exec werkstatt-mongodb mongorestore /backup/werkstatt_20241201/

# Verwaltung Restore  
docker exec verwaltung-mongodb mongorestore /backup/verwaltung_20241201/
```

## Updates

### Alle Systeme aktualisieren
```bash
# Stoppen
stop_all.bat

# Code aktualisieren (git pull)

# Alle neu starten
start_all.bat
```

### Einzelne Abteilung aktualisieren
```bash
# Nur BTZ neu starten
docker-compose -f docker-compose.btz.yml down
docker-compose -f docker-compose.btz.yml up -d --build
```

## Monitoring

### Status aller Systeme prüfen
```bash
docker ps | grep scandy
```

### Logs einer Abteilung
```bash
# BTZ Logs
docker logs btz-scandy

# Werkstatt Logs
docker logs werkstatt-scandy

# Verwaltung Logs
docker logs verwaltung-scandy
```

## Sicherheit

- **Separate Passwörter** für jede MongoDB-Instanz
- **Separate Secret Keys** für jede App-Instanz
- **Keine Datenvermischung** zwischen Abteilungen
- **Einfache Zugriffskontrolle** - nur lokale Netzwerk-Zugriffe

## Troubleshooting

### Port-Konflikte
Falls Ports bereits belegt sind, ändere die Ports in den docker-compose-Dateien:

```yaml
# In docker-compose.btz.yml
ports:
  - "5003:5000"  # Ändern zu z.B. "5010:5000"
```

### Datenbank-Verbindung
Prüfe die MongoDB-Verbindung:
```bash
# BTZ
docker exec btz-mongodb mongosh --eval "db.adminCommand('ping')"

# Werkstatt
docker exec werkstatt-mongodb mongosh --eval "db.adminCommand('ping')"

# Verwaltung
docker exec verwaltung-mongodb mongosh --eval "db.adminCommand('ping')"
```

### Container-Neustart
```bash
# BTZ neu starten
docker-compose -f docker-compose.btz.yml restart

# Alle neu starten
docker-compose -f docker-compose.btz.yml restart
docker-compose -f docker-compose.werkstatt.yml restart  
docker-compose -f docker-compose.verwaltung.yml restart
``` 