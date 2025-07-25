# Scandy Linux Mint Installation (ohne Docker)

Diese Anleitung beschreibt die Installation von Scandy auf einem Linux Mint System ohne Docker oder Containerisierung.

## Voraussetzungen

- Linux Mint 20.x oder neuer
- Internetverbindung
- Sudo-Rechte für den Benutzer
- Mindestens 2GB freier Speicherplatz

## Installation

### 1. Repository klonen

```bash
git clone <repository-url>
cd scandy
```

### 2. Installationsskript ausführbar machen

```bash
chmod +x install_linux_mint.sh
```

### 3. Installation starten

```bash
# Empfohlen: Mit sudo für bessere Berechtigungen
sudo ./install_linux_mint.sh

# Oder ohne sudo (falls Berechtigungsprobleme auftreten)
./install_linux_mint.sh
```

Das Skript führt automatisch folgende Schritte aus:

- System-Updates
- Installation aller Abhängigkeiten (Python, MongoDB, Node.js)
- Konfiguration von MongoDB
- Erstellung eines Python Virtual Environment
- Installation aller Python-Pakete
- Erstellung notwendiger Verzeichnisse
- Konfiguration der .env Datei
- Erstellung eines Systemd Service
- Optionale Nginx-Installation
- Firewall-Konfiguration
- Erstellung von Backup- und Update-Skripten

## Was wird installiert?

### System-Pakete
- **Python 3**: Für die Flask-Anwendung
- **MongoDB 7.0**: Datenbank
- **Node.js 18**: Für CSS-Build (Tailwind)
- **Nginx**: Optional als Reverse Proxy
- **UFW**: Firewall

### Python-Pakete
Alle Pakete aus `requirements.txt` werden installiert:
- Flask und Erweiterungen
- MongoDB-Treiber
- Bildverarbeitung (Pillow)
- E-Mail-Funktionalität
- Dokumentenverarbeitung

## Konfiguration

### .env Datei

Nach der Installation wird eine `.env` Datei erstellt. Bearbeiten Sie diese für Ihre spezifischen Einstellungen:

```bash
nano .env
```

Wichtige Einstellungen:
- `MAIL_USERNAME` und `MAIL_PASSWORD`: Für E-Mail-Funktionen
- `BASE_URL`: Die öffentliche URL Ihrer Anwendung
- `SECRET_KEY`: Wird automatisch generiert

### E-Mail-Konfiguration

Für Gmail:
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=ihre-email@gmail.com
MAIL_PASSWORD=ihr-app-passwort
```

**Hinweis**: Für Gmail benötigen Sie ein App-Passwort, nicht Ihr normales Passwort.

## Verwaltung

### Service-Verwaltung

```bash
# Status prüfen
./manage_scandy.sh status

# Starten
./manage_scandy.sh start

# Stoppen
./manage_scandy.sh stop

# Neustart
./manage_scandy.sh restart

# Logs anzeigen
./manage_scandy.sh logs
```

### Backups

```bash
# Manuelles Backup erstellen
./manage_scandy.sh backup

# Oder direkt
./backup_scandy.sh
```

### Updates

```bash
# Scandy aktualisieren
./manage_scandy.sh update

# Oder direkt
./update_scandy.sh
```

## Zugriff auf die Anwendung

Nach erfolgreicher Installation ist Scandy verfügbar unter:

- **Lokal**: http://localhost:5000
- **Netzwerk**: http://[IP-Adresse]:5000
- **Über Nginx**: http://[IP-Adresse] (falls installiert)

## Erste Schritte

1. **Admin-Benutzer erstellen**: Öffnen Sie die Web-Oberfläche und erstellen Sie den ersten Administrator
2. **E-Mail konfigurieren**: Bearbeiten Sie die `.env` Datei für E-Mail-Funktionen
3. **Backup-Strategie**: Richten Sie regelmäßige Backups ein

## Troubleshooting

### MongoDB-Probleme

```bash
# MongoDB Status prüfen
sudo systemctl status mongod

# MongoDB Logs anzeigen
sudo journalctl -u mongod -f

# MongoDB neu starten
sudo systemctl restart mongod
```

### Scandy-Probleme

```bash
# Scandy Status prüfen
sudo systemctl status scandy.service

# Scandy Logs anzeigen
sudo journalctl -u scandy.service -f

# Scandy neu starten
sudo systemctl restart scandy.service
```

### Nginx-Probleme

```bash
# Nginx Status prüfen
sudo systemctl status nginx

# Nginx Konfiguration testen
sudo nginx -t

# Nginx Logs anzeigen
sudo tail -f /var/log/nginx/error.log
```

### Firewall-Probleme

```bash
# Firewall Status prüfen
sudo ufw status

# Port 5000 freigeben
sudo ufw allow 5000
```

## Sicherheit

### Firewall
Die Installation konfiguriert automatisch UFW mit folgenden Regeln:
- SSH (Port 22)
- HTTP (Port 80)
- HTTPS (Port 443)
- Scandy (Port 5000)

### Updates
Regelmäßige System-Updates sind wichtig:

```bash
sudo apt update && sudo apt upgrade
```

### Backups
Erstellen Sie regelmäßige Backups:

```bash
# Automatisches Backup (cron job)
crontab -e
# Fügen Sie hinzu: 0 2 * * * /pfad/zu/scandy/backup_scandy.sh
```

## Deinstallation

Falls Sie Scandy entfernen möchten:

```bash
# Service stoppen und entfernen
sudo systemctl stop scandy.service
sudo systemctl disable scandy.service
sudo rm /etc/systemd/system/scandy.service
sudo systemctl daemon-reload

# MongoDB entfernen (optional)
sudo apt remove --purge mongodb-org*
sudo rm -rf /var/lib/mongodb

# Nginx entfernen (optional)
sudo apt remove --purge nginx
sudo rm -rf /etc/nginx/sites-available/scandy
sudo rm -rf /etc/nginx/sites-enabled/scandy

# Python Environment entfernen
rm -rf venv

# Anwendungsverzeichnis entfernen
cd ..
rm -rf scandy
```

## Support

Bei Problemen:
1. Prüfen Sie die Logs: `./manage_scandy.sh logs`
2. Prüfen Sie den Service-Status: `./manage_scandy.sh status`
3. Erstellen Sie ein Backup vor Änderungen
4. Dokumentieren Sie Fehler für Support-Anfragen

## Lizenz

Diese Installation unterliegt der gleichen Lizenz wie die Scandy-Anwendung. 