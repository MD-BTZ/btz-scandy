# Scandy Multi-Platform Docker Installation

## Übersicht

Scandy unterstützt jetzt Multi-Platform Docker Builds für verschiedene Betriebssysteme und Architekturen:

- **Linux AMD64** (Standard x86_64)
- **Linux ARM64** (Raspberry Pi, Apple Silicon)
- **macOS** (Intel und Apple Silicon)
- **Windows** (Intel und ARM)

## Voraussetzungen

### Docker Installation

1. **Docker Desktop** (empfohlen für Windows/macOS)
   - [Docker Desktop für Windows](https://docs.docker.com/desktop/install/windows/)
   - [Docker Desktop für macOS](https://docs.docker.com/desktop/install/mac/)

2. **Docker Engine** (für Linux)
   - [Docker Engine für Linux](https://docs.docker.com/engine/install/)

3. **Docker Buildx** (für Multi-Platform Builds)
   - Wird normalerweise mit Docker Desktop/Engine installiert
   - Manuelle Installation: [Docker Buildx Guide](https://docs.docker.com/buildx/working-with-buildx/)

### Systemanforderungen

- **RAM**: Mindestens 4GB (8GB empfohlen)
- **Speicher**: Mindestens 10GB freier Speicher
- **CPU**: 2 Kerne (4 Kerne empfohlen)

## Installation

### Automatische Installation

#### Windows
```bash
# Führe das Install-Script aus
install_scandy.bat
```

#### Linux/macOS
```bash
# Mache das Script ausführbar
chmod +x install.sh

# Führe das Install-Script aus
./install.sh
```

### Manuelle Installation

1. **Repository klonen**
```bash
git clone <repository-url>
cd scandy
```

2. **Multi-Platform Build erstellen**
```bash
# Linux/macOS
./build-multi-platform.sh

# Windows
build-multi-platform.bat
```

3. **Container starten**
```bash
docker-compose up -d
```

## Plattform-spezifische Hinweise

### Linux AMD64 (Standard)
- **Empfohlen für**: Desktop/Laptop mit Intel/AMD Prozessor
- **Performance**: Beste Performance
- **Kompatibilität**: Höchste Kompatibilität

### Linux ARM64
- **Empfohlen für**: 
  - Raspberry Pi 4 (8GB RAM empfohlen)
  - Apple Silicon Macs (M1/M2/M3)
  - ARM-basierte Server
- **Performance**: Gut (etwas langsamer als AMD64)
- **Kompatibilität**: Hoch

### macOS
- **Intel Macs**: Verwendet Linux AMD64 Container
- **Apple Silicon**: Verwendet Linux ARM64 Container
- **Docker Desktop**: Erforderlich

### Windows
- **Intel**: Verwendet Linux AMD64 Container
- **ARM**: Verwendet Linux ARM64 Container
- **Docker Desktop**: Erforderlich
- **WSL2**: Empfohlen für bessere Performance

## Build-Optionen

### Single-Platform Build
```bash
# Nur für aktuelle Plattform
docker-compose build
```

### Multi-Platform Build
```bash
# Für alle unterstützten Plattformen
./build-multi-platform.sh --push
```

### Spezifische Plattform
```bash
# Nur ARM64
docker buildx build --platform linux/arm64 -t scandy:arm64 .

# Nur AMD64
docker buildx build --platform linux/amd64 -t scandy:amd64 .
```

## Troubleshooting

### Build-Fehler

#### "no matching manifest for linux/amd64" Fehler
```bash
# Problem: Multi-Platform Build erstellt kein Image für aktuelle Plattform
# Lösung: Verwende Platform-Specific Build oder einfache Dockerfile

# Option 1: Quick Fix (Windows)
quick-fix.bat

# Option 2: Platform-Specific Build
build-platform-specific.bat  # Windows
./build-platform-specific.sh # Linux/macOS

# Option 3: Manuell
copy Dockerfile.simple Dockerfile
docker-compose build --no-cache
```

#### "npm ci --only=production" Fehler
```bash
# Problem: npm ci --only=production ist kein gültiger Befehl
# Lösung: Verwende das Troubleshooting-Script
fix-docker-build.bat  # Windows
./fix-docker-build.sh # Linux/macOS

# Oder manuell:
# 1. Verwende einfache Dockerfile
copy Dockerfile.simple Dockerfile
docker-compose build --no-cache

# 2. Oder leere Cache
docker system prune -f
docker builder prune -f
```

#### "Docker Buildx nicht verfügbar"
```bash
# Docker Buildx installieren
docker buildx install
```

#### "Platform nicht unterstützt"
```bash
# Verfügbare Plattformen prüfen
docker buildx ls

# Builder erstellen
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

#### "Nicht genug Speicher"
```bash
# Docker Buildx mit mehr Speicher
docker buildx create --name multiarch --driver docker-container --use --driver-opt network=host
```

### Performance-Probleme

#### Langsame Builds
- Verwende SSD für bessere I/O-Performance
- Erhöhe Docker-Ressourcen in Docker Desktop
- Verwende Build-Cache: `docker buildx build --cache-from type=local,src=/tmp/.buildx-cache`

#### Container startet nicht
```bash
# Logs prüfen
docker-compose logs

# Container-Status prüfen
docker-compose ps
```

### Häufige Probleme

#### Node.js Dependencies
```bash
# Problem: npm ci schlägt fehl
# Lösung: Verwende einfache Dockerfile
copy Dockerfile.simple Dockerfile
docker-compose build --no-cache
```

#### Multi-Stage Build Probleme
```bash
# Problem: Multi-Stage Build schlägt fehl
# Lösung: Verwende einfache Version
# Das Install-Script wechselt automatisch zur einfachen Version
```

#### Cache-Probleme
```bash
# Problem: Alte Cache-Daten verursachen Probleme
# Lösung: Cache leeren
docker system prune -f
docker builder prune -f
```

## Konfiguration

### Umgebungsvariablen

Die wichtigsten Umgebungsvariablen in `docker-compose.yml`:

```yaml
environment:
  - DATABASE_MODE=mongodb
  - MONGODB_URI=mongodb://admin:password@mongodb:27017/
  - FLASK_ENV=production
  - SECRET_KEY=your-secret-key
  - TZ=Europe/Berlin
```

### Ports

Standard-Ports (können in `docker-compose.yml` geändert werden):
- **App**: 5000
- **MongoDB**: 27017
- **Mongo Express**: 8081

### Volumes

Datenverzeichnisse werden automatisch erstellt:
- `./data/uploads` - Hochgeladene Dateien
- `./data/backups` - Backups
- `./data/logs` - Log-Dateien
- `./data/static` - Statische Dateien

## Wartung

### Updates
```bash
# Container stoppen
docker-compose down

# Neues Image bauen
./build-multi-platform.sh

# Container neu starten
docker-compose up -d
```

### Backups
```bash
# Backup erstellen
./backup.bat  # Windows
./backup.sh   # Linux/macOS
```

### Logs
```bash
# App-Logs
docker-compose logs app

# MongoDB-Logs
docker-compose logs mongodb

# Alle Logs
docker-compose logs -f
```

## Support

Bei Problemen:

1. **Logs prüfen**: `docker-compose logs`
2. **Container-Status**: `docker-compose ps`
3. **Docker-Info**: `docker info`
4. **Buildx-Status**: `docker buildx ls`

## Bekannte Probleme

### Apple Silicon (M1/M2/M3)
- **Problem**: Langsame Builds bei ersten Mal
- **Lösung**: Build-Cache verwenden, zweiter Build ist schneller

### Raspberry Pi
- **Problem**: Wenig RAM
- **Lösung**: Docker-Swaps erhöhen, weniger Container gleichzeitig

### Windows WSL2
- **Problem**: Dateisystem-Performance
- **Lösung**: Projekt in WSL2-Dateisystem, nicht in Windows-Dateisystem 