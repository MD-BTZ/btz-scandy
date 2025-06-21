# Scandy Auto-Installation

## Übersicht

Diese automatischen Installationsskripte installieren Scandy ohne Benutzerinteraktion mit festen, vorkonfigurierten Werten. Das verhindert Fehler und macht die Installation reproduzierbar.

## Verfügbare Skripte

### 1. Automatische Installation (Linux/macOS)
```bash
./install_auto.sh
```

### 2. Automatische Installation (Windows)
```cmd
install_auto.bat
```

### 3. Update bestehender Installation
```bash
./update.sh
```

## Feste Konfiguration

Alle Skripte verwenden diese festen Werte:

| Einstellung | Wert | Beschreibung |
|-------------|------|--------------|
| Container Name | `scandy` | Name der Docker-Container |
| App Port | `5000` | Port für die Scandy-Anwendung |
| MongoDB Port | `27017` | Port für MongoDB |
| Mongo Express Port | `8081` | Port für MongoDB Web-UI |
| MongoDB User | `admin` | MongoDB Admin-Benutzer |
| MongoDB Password | `scandy123` | MongoDB Admin-Passwort |
| Datenverzeichnis | `./scandy_data` | Lokales Datenverzeichnis |

## Voraussetzungen

- Docker installiert und läuft
- Docker Compose installiert
- Git installiert (für Updates)

## Installation

### Linux/macOS
```bash
# Skript ausführbar machen
chmod +x install_auto.sh

# Installation starten
./install_auto.sh
```

### Windows
```cmd
# Installation starten
install_auto.bat
```

## Nach der Installation

### Zugriff auf die Anwendung
- **Scandy**: http://localhost:5000
- **MongoDB Express**: http://localhost:8081 (admin/scandy123)

### Nützliche Befehle
```bash
# Container-Status prüfen
docker-compose ps

# Logs anzeigen
docker-compose logs -f

# Container stoppen
docker-compose down

# Container neu starten
docker-compose restart

# Update durchführen
./update.sh
```

## Datenverzeichnis-Struktur

```
scandy_data/
├── mongodb/          # MongoDB-Daten
├── uploads/          # Hochgeladene Dateien
├── backups/          # Backups
├── logs/             # Log-Dateien
└── static/           # Statische Dateien
```

## Troubleshooting

### Port-Konflikte
Falls Port 5000, 27017 oder 8081 bereits verwendet werden:
1. Stoppen Sie andere Anwendungen auf diesen Ports
2. Oder ändern Sie die Ports in den Skripten

### Docker-Probleme
```bash
# Docker-Status prüfen
docker info

# Docker neu starten
sudo systemctl restart docker  # Linux
# Docker Desktop neu starten   # Windows/macOS
```

### Container-Probleme
```bash
# Container-Logs anzeigen
docker-compose logs app
docker-compose logs mongodb

# Container neu bauen
docker-compose down
docker-compose up -d --build
```

## Vorteile der automatischen Installation

✅ **Keine Benutzerinteraktion** - Läuft vollautomatisch  
✅ **Reproduzierbar** - Immer gleiche Konfiguration  
✅ **Fehlerfrei** - Keine Tippfehler bei der Eingabe  
✅ **Schnell** - Keine Wartezeiten für Benutzereingaben  
✅ **Deployment-freundlich** - Ideal für CI/CD-Pipelines  

## Anpassung der Konfiguration

Falls Sie andere Werte verwenden möchten, bearbeiten Sie die Variablen am Anfang der Skripte:

```bash
# In install_auto.sh
CONTAINER_NAME="scandy"
APP_PORT="5000"
MONGO_PORT="27017"
# ... weitere Einstellungen
```

```cmd
REM In install_auto.bat
set CONTAINER_NAME=scandy
set APP_PORT=5000
set MONGO_PORT=27017
REM ... weitere Einstellungen
``` 