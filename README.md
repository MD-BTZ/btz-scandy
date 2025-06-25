# Scandy - Werkzeugverwaltungssystem

Ein modernes, webbasiertes Werkzeugverwaltungssystem für Unternehmen, das die Verwaltung von Werkzeugen, Verbrauchsgütern und Mitarbeitern vereinfacht.

## 🚀 Schnellstart

### Voraussetzungen
- Docker Desktop
- Docker Compose

### Ein-Klick-Installation

**Linux/macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/woschj/scandy-deploy/main/install.sh | bash
```

**Windows:**
```cmd
# Lade install.bat herunter und führe es aus
```

### Manuelle Installation

1. **Repository klonen:**
```bash
git clone https://github.com/woschj/scandy-deploy.git
cd scandy-deploy
```

2. **Container starten:**
```bash
docker-compose up -d
```

3. **Anwendung öffnen:**
- App: http://localhost:5000
- Mongo Express: http://localhost:8081

## 📋 Features

### 🛠️ Werkzeugverwaltung
- Barcode-basierte Identifikation
- Status-Tracking (verfügbar, verliehen, defekt)
- Kategorisierung und Standortverwaltung
- Verleihhistorie

### 👥 Mitarbeiterverwaltung
- Mitarbeiterregistrierung mit Barcodes
- Verleihhistorie pro Mitarbeiter
- Abteilungszuordnung

### 📦 Verbrauchsgüter
- Bestandsverwaltung
- Automatische Nachbestellung
- Verbrauchstracking

### 🎫 Ticket-System
- Aufgabenverwaltung
- Priorisierung
- Zuweisung an Mitarbeiter

### 📊 Berichte
- Verleihstatistiken
- Bestandsübersichten
- Export-Funktionen

## 🏗️ Architektur

### Container
- **scandy-app**: Flask-Anwendung (Port 5000)
- **scandy-mongodb**: MongoDB-Datenbank (Port 27017)
- **scandy-mongo-express**: Web-UI für MongoDB (Port 8081)

### Datenbank
- **MongoDB 7.0** mit Authentifizierung
- Automatische Initialisierung mit Indizes
- Persistente Datenspeicherung

## 🔧 Konfiguration

### Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|----------|--------------|
| `MONGODB_URI` | `mongodb://admin:scandy123@scandy-mongodb:27017/` | MongoDB-Verbindung |
| `MONGODB_DB` | `scandy` | Datenbankname |
| `SECRET_KEY` | `scandy-secret-key-change-in-production` | Flask Secret Key |
| `SYSTEM_NAME` | `Scandy` | Systemname |
| `TZ` | `Europe/Berlin` | Zeitzone |

### Ports

| Service | Standard-Port | Beschreibung |
|---------|---------------|--------------|
| App | 5000 | Web-Anwendung |
| MongoDB | 27017 | Datenbank |
| Mongo Express | 8081 | Datenbank-Web-UI |

## 📁 Projektstruktur

```
scandy-deploy/
├── docker-compose.yml      # Container-Konfiguration
├── mongo-init/
│   └── init.js            # MongoDB-Initialisierung
├── install.sh             # Linux/macOS Installation
├── install.bat            # Windows Installation
├── README.md              # Diese Datei
└── .github/
    └── workflows/
        └── build-and-push.yml  # Automatische Builds
```

## 🛠️ Verwaltung

### Container verwalten

**Starten:**
```bash
./start.sh          # Linux/macOS
start.bat           # Windows
```

**Stoppen:**
```bash
./stop.sh           # Linux/macOS
stop.bat            # Windows
```

**Update:**
```bash
./update.sh         # Linux/macOS
update.bat          # Windows
```

**Backup:**
```bash
./backup.sh         # Linux/macOS
backup.bat          # Windows
```

### Manuelle Docker-Befehle

```bash
# Container-Status anzeigen
docker-compose ps

# Logs anzeigen
docker-compose logs -f scandy-app

# Container neu starten
docker-compose restart scandy-app

# Datenbank-Backup
docker exec scandy-mongodb mongodump --out /tmp/backup
docker cp scandy-mongodb:/tmp/backup ./backup/
```

## 🔒 Sicherheit

### Standard-Credentials
- **MongoDB Admin**: `admin` / `scandy123`
- **Mongo Express**: `admin` / `scandy123`

### Produktionsumgebung
⚠️ **Wichtig**: Ändern Sie die Standard-Passwörter in einer Produktionsumgebung!

```yaml
# docker-compose.yml anpassen:
environment:
  MONGO_INITDB_ROOT_PASSWORD: IhrSicheresPasswort
  ME_CONFIG_MONGODB_ADMINPASSWORD: IhrSicheresPasswort
  SECRET_KEY: IhrSichererSecretKey
```

## 🐛 Troubleshooting

### Häufige Probleme

**Container startet nicht:**
```bash
# Logs prüfen
docker-compose logs scandy-app

# Container neu bauen
docker-compose down
docker-compose up -d --build
```

**Datenbank-Verbindungsfehler:**
```bash
# MongoDB-Container Status prüfen
docker-compose ps scandy-mongodb

# MongoDB-Logs anzeigen
docker-compose logs scandy-mongodb
```

**Port bereits belegt:**
```bash
# Verfügbare Ports prüfen
netstat -tuln | grep :5000

# Anderen Port in docker-compose.yml verwenden
```

### Logs analysieren

```bash
# App-Logs
docker-compose logs -f scandy-app

# MongoDB-Logs
docker-compose logs -f scandy-mongodb

# Alle Logs
docker-compose logs -f
```

## 📈 Monitoring

### Health Checks
- **App**: `http://localhost:5000/health`
- **MongoDB**: Automatischer Ping alle 30s
- **Mongo Express**: Abhängig von MongoDB

### Metriken
- Container-Status über `docker-compose ps`
- Ressourcenverbrauch über `docker stats`
- Logs über `docker-compose logs`

## 🔄 Updates

### Automatische Updates
Das System wird automatisch über GitHub Actions aktualisiert:
- Bei jedem Push zum `main` Branch
- Bei neuen Tags (v1.0, v1.1, etc.)
- Multi-Architecture Support (AMD64, ARM64)

### Manuelle Updates
```bash
# Neueste Version holen
docker-compose pull

# Container neu starten
docker-compose up -d
```

## 🤝 Beitragen

1. Fork das Repository
2. Erstelle einen Feature Branch
3. Committe deine Änderungen
4. Push zum Branch
5. Erstelle einen Pull Request

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.

## 🆘 Support

Bei Problemen oder Fragen:
1. Prüfen Sie die [Troubleshooting-Sektion](#-troubleshooting)
2. Schauen Sie in die [Issues](https://github.com/woschj/scandy-deploy/issues)
3. Erstellen Sie ein neues Issue mit detaillierter Beschreibung

## 🔗 Links

- **Docker Hub**: https://hub.docker.com/r/woschj/scandy
- **GitHub Repository**: https://github.com/woschj/scandy-deploy
- **Dokumentation**: Diese README 