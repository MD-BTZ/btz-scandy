# Scandy - Werkzeugverwaltungssystem

Ein modernes, webbasiertes Werkzeugverwaltungssystem mit Barcode-Scanner-Unterstützung.

## 🚀 Schnellstart

### Windows
```bash
install.bat
```

### Linux/macOS
```bash
chmod +x install.sh
./install.sh
```

## 📋 Features

- **Werkzeugverwaltung**: Vollständige Verwaltung von Werkzeugen mit Barcode-Scanner
- **Mitarbeiterverwaltung**: Verwaltung von Mitarbeitern und deren Berechtigungen
- **Ausleihsystem**: Einfaches Ausleihen und Zurückgeben von Werkzeugen
- **Verbrauchsgüter**: Verwaltung von Verbrauchsmaterialien
- **Aufgabensystem**: Ticket-basiertes Aufgabensystem für Wartung und Reparaturen
- **Automatische Backups**: Backups werden automatisch bei jedem Start erstellt
- **Docker-basiert**: Einfache Installation und Wartung

## 🛠️ Installation

### Voraussetzungen
- Docker Desktop
- Mindestens 4GB RAM
- 10GB freier Speicherplatz

### Automatische Installation

1. **Repository klonen:**
   ```bash
   git clone <repository-url>
   cd scandy
   ```

2. **Installation starten:**
   
   **Windows:**
   ```bash
   install.bat
   ```
   
   **Linux/macOS:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Installation folgt automatisch:**
   - Docker-Container werden erstellt
   - Datenbank wird initialisiert
   - Automatische Backups werden eingerichtet
   - Anwendung wird gestartet

### Nach der Installation

- **Scandy**: http://localhost:5000
- **Mongo Express**: http://localhost:8081
- **MongoDB**: localhost:27017

## 📁 Projektstruktur

```
scandy_project/
├── docker-compose.yml    # Container-Konfiguration
├── start.bat            # Windows: Container starten
├── stop.bat             # Windows: Container stoppen
├── update.bat           # Windows: System aktualisieren
├── backup.bat           # Windows: Backup erstellen
├── start.sh             # Linux/macOS: Container starten
├── stop.sh              # Linux/macOS: Container stoppen
├── update.sh            # Linux/macOS: System aktualisieren
├── backup.sh            # Linux/macOS: Backup erstellen
└── scandy_data/         # Persistente Daten
    ├── mongodb/         # MongoDB-Daten
    ├── uploads/         # Hochgeladene Dateien
    ├── backups/         # Automatische Backups
    ├── logs/            # Anwendungs-Logs
    └── static/          # Statische Dateien
```

## 🔄 Automatische Backups

Backups werden automatisch erstellt:
- **Bei jedem Start** der Anwendung
- **MongoDB-Dump** mit allen Daten
- **Anwendungsdaten** (Uploads, Logs, etc.)
- **Komprimiert** in ZIP/TAR-Format
- **Zeitstempel** für einfache Verwaltung

### Backup-Verzeichnis
```
scandy_data/backups/
├── mongodb_20250101_120000/     # MongoDB-Dump
├── app_data_20250101_120000.zip # Anwendungsdaten
└── ...
```

## 🛠️ Verwaltung

### Container starten
```bash
# Windows
start.bat

# Linux/macOS
./start.sh
```

### Container stoppen
```bash
# Windows
stop.bat

# Linux/macOS
./stop.sh
```

### System aktualisieren
```bash
# Windows
update.bat

# Linux/macOS
./update.sh
```

### Backup erstellen
```bash
# Windows
backup.bat

# Linux/macOS
./backup.sh
```

### Mit automatischem Backup starten
```bash
# Windows
start-with-backup.bat

# Linux/macOS
./start-with-backup.sh
```

## 🔧 Konfiguration

### Umgebungsvariablen
- `CONTAINER_NAME`: Name der Container (Standard: scandy)
- `APP_PORT`: Port für die Web-Anwendung (Standard: 5000)
- `MONGO_PORT`: Port für MongoDB (Standard: 27017)
- `MONGO_EXPRESS_PORT`: Port für Mongo Express (Standard: 8081)
- `DATA_DIR`: Verzeichnis für persistente Daten (Standard: ./scandy_data)

### Anpassung
Die Konfiguration kann in den Install-Scripts angepasst werden:
- `install.bat` (Windows)
- `install.sh` (Linux/macOS)

## 🐛 Fehlerbehebung

### Container startet nicht
1. Prüfen Sie Docker-Logs: `docker-compose logs`
2. Prüfen Sie Container-Status: `docker-compose ps`
3. Starten Sie Container neu: `docker-compose restart`

### Flask-Modul nicht gefunden
Das System verwendet automatisch eine einfache Dockerfile-Version als Fallback.

### Backup-Probleme
1. Prüfen Sie Schreibrechte im Backup-Verzeichnis
2. Prüfen Sie verfügbaren Speicherplatz
3. Manuelles Backup: `backup.bat` oder `./backup.sh`

## 📞 Support

Bei Problemen:
1. Prüfen Sie die Logs: `docker-compose logs`
2. Prüfen Sie den Container-Status: `docker-compose ps`
3. Erstellen Sie ein Backup vor Änderungen
4. Kontaktieren Sie den Support

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz.

## 📚 Dokumentation

- [Benutzerhandbuch](docs/05_BENUTZERHANDBUCH.md)
- [Admin-Handbuch](docs/06_ADMINHANDBUCH.md)
- [Entwickler-Dokumentation](docs/10_ENTWICKLUNG.md)
- [Multi-Platform Docker](DOCKER_MULTI_PLATFORM.md)

## 🤝 Support

Bei Problemen:

1. **Troubleshooting-Script verwenden**
2. **Logs prüfen**: `docker-compose logs`
3. **Dokumentation lesen**: [docs/](docs/)
4. **Issue erstellen**: GitHub Issues

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei.

## 🔄 Updates

```bash
# System aktualisieren
./update.sh  # Linux/macOS
update.bat   # Windows
```

---

**Scandy** - Moderne Inventarverwaltung für die digitale Arbeitswelt 