# 🐳 Scandy Docker-Installation

## Übersicht

Diese Anleitung zeigt, wie Sie Scandy mit MongoDB und der App in separaten Docker-Containern installieren.

## 📋 Voraussetzungen

- **Docker Desktop** (Windows/Mac) oder **Docker Engine** (Linux)
- **Docker Compose**
- Mindestens **4GB RAM** verfügbar
- Mindestens **10GB freier Speicherplatz**

## 🚀 Schnellstart

### Option 1: Automatische Installation (Empfohlen)

#### Linux/macOS:
```bash
chmod +x install_docker_complete.sh
./install_docker_complete.sh
```

#### Windows:
```cmd
install_docker_complete.bat
```

### Option 2: Manuelle Installation

1. **Repository klonen:**
```bash
git clone https://github.com/woschj/scandy2.git
cd scandy2
```

2. **Docker Compose starten:**
```bash
docker-compose -f docker-compose.production.yml up -d
```

## 📁 Projektstruktur nach Installation

```
scandy_project/
├── docker-compose.yml          # Docker Compose Konfiguration
├── Dockerfile                  # App Container Definition
├── mongo-init/                 # MongoDB Initialisierung
│   └── init.js
├── app/                        # Anwendungscode
├── data/                       # Persistente Daten
│   ├── mongodb/               # MongoDB Daten
│   ├── uploads/               # Hochgeladene Dateien
│   ├── backups/               # Backups
│   ├── logs/                  # Log-Dateien
│   └── static/                # Statische Dateien
├── start.bat                  # Start-Skript (Windows)
├── stop.bat                   # Stop-Skript (Windows)
├── update.bat                 # Update-Skript (Windows)
├── backup.bat                 # Backup-Skript (Windows)
├── start.sh                   # Start-Skript (Linux/macOS)
├── stop.sh                    # Stop-Skript (Linux/macOS)
├── update.sh                  # Update-Skript (Linux/macOS)
└── backup.sh                  # Backup-Skript (Linux/macOS)
```

## 🌐 Zugriff auf die Anwendung

Nach erfolgreicher Installation sind folgende Services verfügbar:

| Service | URL | Beschreibung |
|---------|-----|--------------|
| **Scandy App** | http://localhost:5000 | Hauptanwendung |
| **Mongo Express** | http://localhost:8081 | MongoDB Web-UI |
| **MongoDB** | localhost:27017 | Datenbank (direkt) |

### Standard-Anmeldedaten

- **MongoDB Admin:** `admin` / `scandy123`
- **Mongo Express:** `admin` / `scandy123`

## 🛠️ Verwaltung

### Container starten
```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

### Container stoppen
```bash
# Linux/macOS
./stop.sh

# Windows
stop.bat
```

### Container aktualisieren
```bash
# Linux/macOS
./update.sh

# Windows
update.bat
```

### Backup erstellen
```bash
# Linux/macOS
./backup.sh

# Windows
backup.bat
```

### Container-Status prüfen
```bash
docker-compose ps
```

### Logs anzeigen
```bash
# Alle Services
docker-compose logs

# Spezifischer Service
docker-compose logs scandy-app
docker-compose logs scandy-mongodb
```

## 🔧 Konfiguration

### Umgebungsvariablen

Die wichtigsten Umgebungsvariablen können in der `docker-compose.yml` angepasst werden:

```yaml
environment:
  - MONGODB_URI=mongodb://admin:scandy123@scandy-mongodb:27017/
  - MONGODB_DB=scandy
  - FLASK_ENV=production
  - SECRET_KEY=your-secret-key
  - SYSTEM_NAME=Scandy
  - TICKET_SYSTEM_NAME=Aufgaben
  - TOOL_SYSTEM_NAME=Werkzeuge
  - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
```

### Ports ändern

Um die Standard-Ports zu ändern, bearbeiten Sie die `ports`-Sektionen in der `docker-compose.yml`:

```yaml
# App Port
ports:
  - "8080:5000"  # Ändert App-Port von 5000 auf 8080

# MongoDB Port
ports:
  - "27018:27017"  # Ändert MongoDB-Port von 27017 auf 27018

# Mongo Express Port
ports:
  - "8082:8081"  # Ändert Mongo Express-Port von 8081 auf 8082
```

## 🔒 Sicherheit

### Produktionsumgebung

Für die Produktionsumgebung sollten Sie:

1. **Starke Passwörter verwenden:**
```yaml
environment:
  MONGO_INITDB_ROOT_PASSWORD: Ihr-sicheres-Passwort
```

2. **Mongo Express deaktivieren** (nur für Entwicklung):
```yaml
# Kommentieren Sie den mongo-express Service aus
# scandy-mongo-express:
#   ...
```

3. **Externe Ports schützen:**
```yaml
# Nur lokalen Zugriff erlauben
ports:
  - "127.0.0.1:5000:5000"
```

4. **SSL/TLS konfigurieren** (über Reverse Proxy)

## 🐛 Fehlerbehebung

### Container startet nicht

1. **Logs prüfen:**
```bash
docker-compose logs scandy-app
```

2. **Ports prüfen:**
```bash
netstat -tuln | grep :5000
```

3. **Docker-Ressourcen prüfen:**
```bash
docker system df
```

### MongoDB-Verbindungsfehler

1. **MongoDB-Container-Status prüfen:**
```bash
docker-compose ps scandy-mongodb
```

2. **MongoDB-Logs prüfen:**
```bash
docker-compose logs scandy-mongodb
```

3. **Netzwerk prüfen:**
```bash
docker network ls
docker network inspect scandy_scandy-network
```

### Datenverlust vermeiden

- **Regelmäßige Backups erstellen**
- **Volumes nicht löschen**
- **Updates nur nach Backup durchführen**

## 📊 Monitoring

### Health Checks

Alle Container haben Health Checks konfiguriert:

```bash
docker-compose ps
```

### Ressourcenverbrauch

```bash
docker stats
```

### Log-Rotation

Logs werden automatisch rotiert (max. 10MB pro Datei, 3 Dateien):

```bash
docker-compose logs --tail=100 scandy-app
```

## 🔄 Updates

### Automatisches Update

```bash
# Linux/macOS
./update.sh

# Windows
update.bat
```

### Manuelles Update

```bash
# Container stoppen
docker-compose down

# Images aktualisieren
docker-compose pull

# Neu bauen
docker-compose build --no-cache

# Container starten
docker-compose up -d
```

## 📞 Support

Bei Problemen:

1. **Logs prüfen:** `docker-compose logs`
2. **Container-Status prüfen:** `docker-compose ps`
3. **Issue auf GitHub erstellen** mit Logs und Konfiguration

## 📝 Changelog

### Version 1.0.0
- Initiale Docker-Installation
- MongoDB 7.0 Integration
- Mongo Express Web-UI
- Automatische Health Checks
- Backup-Funktionalität
- Update-Skripte 