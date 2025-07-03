# Scandy - Werkzeug- und Verbrauchsgüterverwaltung

Eine moderne Web-Anwendung zur Verwaltung von Werkzeugen, Verbrauchsgütern und Aufgaben.

## 🚀 Schnellstart

### Voraussetzungen
- Docker Desktop installiert und gestartet
- Git (zum Klonen des Repositories)

### Installation

1. **Repository klonen:**
   ```bash
   git clone <repository-url>
   cd scandy
   ```

2. **Installation starten:**

   **Windows:**
   ```cmd
   install.bat
   ```

   **Linux/macOS:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Konfiguration anpassen:**
   - Die `.env`-Datei wird automatisch erstellt
   - Passe die Werte in `.env` an deine Umgebung an
   - **Wichtig:** Ändere die Passwörter!

4. **Anwendung öffnen:**
   - Web-App: http://localhost:5000
   - Mongo Express: http://localhost:8081

### Standard-Zugangsdaten
- **Benutzer:** admin
- **Passwort:** admin123

## 🔄 Updates

### App-Update (ohne Datenverlust)

**Windows:**
```cmd
update.bat
```

**Linux/macOS:**
```bash
chmod +x update.sh
./update.sh
```

**Was passiert beim Update:**
- ✅ Nur der App-Container wird aktualisiert
- ✅ MongoDB-Daten bleiben unberührt
- ✅ Schneller Update-Prozess
- ✅ Keine Downtime für die Datenbank

## 📋 Funktionen

- **Werkzeugverwaltung:** Werkzeuge erfassen, verleihen und zurücknehmen
- **Verbrauchsgüterverwaltung:** Verbrauchsgüter bestellen und verwalten
- **Aufgabenverwaltung:** Tickets erstellen und bearbeiten
- **Benutzerverwaltung:** Mitarbeiter und Berechtigungen verwalten
- **Berichte:** Auswertungen und Statistiken
- **Backup-System:** Automatische Datensicherung

## 🛠️ Entwicklung

### Container verwalten

```bash
# Container starten
docker-compose up -d

# Container stoppen
docker-compose down

# Logs anzeigen
docker-compose logs -f

# Container-Status prüfen
docker-compose ps
```

### Datenbank verwalten

```bash
# MongoDB-Shell öffnen
docker exec -it scandy-mongodb mongosh

# Datenbank sichern
docker exec scandy-mongodb mongodump --out /backup

# Datenbank wiederherstellen
docker exec scandy-mongodb mongorestore /backup
```

## 📁 Projektstruktur

```
scandy/
├── app/                    # Flask-Anwendung
│   ├── models/            # Datenbankmodelle
│   ├── routes/            # API-Routen
│   ├── templates/         # HTML-Templates
│   ├── static/            # CSS, JS, Bilder
│   └── utils/             # Hilfsfunktionen
├── mongo-init/            # MongoDB-Initialisierung
├── docker-compose.yml     # Docker-Konfiguration
├── Dockerfile             # Container-Build
├── install.bat            # Windows-Installation
├── install.sh             # Linux/macOS-Installation
├── update.bat             # Windows-App-Update
├── update.sh              # Linux/macOS-App-Update
└── README.md              # Diese Datei
```

## 🔧 Konfiguration

Die Anwendung kann über Umgebungsvariablen konfiguriert werden:

- `MONGODB_URI`: MongoDB-Verbindungsstring
- `SECRET_KEY`: Flask-Secret-Key
- `SYSTEM_NAME`: Name der Anwendung
- `MAIL_SERVER`: SMTP-Server für E-Mails
- `MAIL_PORT`: SMTP-Port
- `MAIL_USERNAME`: SMTP-Benutzername
- `MAIL_PASSWORD`: SMTP-Passwort

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfe die Logs: `docker-compose logs -f`
2. Stelle sicher, dass Docker läuft
3. Prüfe, ob die Ports 5000 und 8081 frei sind

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