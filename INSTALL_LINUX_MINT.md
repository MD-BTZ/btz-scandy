# Scandy Installation auf Linux Mint

## Übersicht

Diese Anleitung hilft Ihnen bei der Installation von Scandy auf Linux Mint. Das ursprüngliche `install_scandy_lxc.sh` Script hat Probleme mit der MongoDB-Installation auf Linux Mint, die hier behoben werden.

## Voraussetzungen

- Linux Mint 19.x, 20.x oder 21.x
- Internetverbindung
- Root-Rechte (sudo)
- Mindestens 2GB freier Speicherplatz

## Installation

### 1. Repository klonen

```bash
git clone <repository-url>
cd scandy
```

### 2. Installation ausführen

```bash
# Scripts ausführbar machen
chmod +x install_scandy_lxc_linux_mint.sh
chmod +x troubleshoot_mongodb.sh
chmod +x fix_permissions.sh

# Bei Berechtigungsproblemen zuerst Fix-Script ausführen
sudo ./fix_permissions.sh

# Installation starten
sudo ./install_scandy_lxc_linux_mint.sh
```

### 3. Installation überwachen

Das Script führt folgende Schritte automatisch aus:

1. **System-Update**: Aktualisiert alle Pakete
2. **Basis-Pakete**: Installiert Python, Nginx, Git, etc.
3. **MongoDB**: Installiert MongoDB 7.0 mit korrekter Linux Mint-Konfiguration
4. **Benutzer**: Erstellt den `scandy`-Benutzer
5. **Python-Umgebung**: Richtet virtuelle Python-Umgebung ein
6. **Konfiguration**: Erstellt `.env`-Datei und Services
7. **Services**: Startet MongoDB, Nginx und Scandy

## Nach der Installation

### Standard-Zugangsdaten

- **Web-Interface**: http://[IHRE-IP]/
- **MongoDB**: localhost:27017
- **Admin-Benutzer**: admin / scandy123456

### Wichtige Sicherheitshinweise

⚠️ **Ändern Sie unbedingt das Standard-Passwort!**

```bash
# .env-Datei bearbeiten
sudo nano /opt/scandy/.env

# Passwort ändern:
# MONGO_INITDB_ROOT_PASSWORD=ihr_neues_sicheres_passwort
# MONGODB_URI=mongodb://admin:ihr_neues_sicheres_passwort@localhost:27017/scandy?authSource=admin
```

### Services verwalten

```bash
# Status prüfen
sudo systemctl status mongod
sudo systemctl status scandy
sudo systemctl status nginx

# Services neu starten
sudo systemctl restart mongod
sudo systemctl restart scandy
sudo systemctl restart nginx

# Logs anzeigen
sudo journalctl -u mongod -f
sudo journalctl -u scandy -f
```

## Troubleshooting

### 1. MongoDB-Probleme

Führen Sie das Troubleshooting-Script aus:

```bash
chmod +x troubleshoot_mongodb.sh
sudo ./troubleshoot_mongodb.sh
```

### 2. Berechtigungsprobleme

Bei Download-Fehlern oder Berechtigungsproblemen:

```bash
chmod +x fix_permissions.sh
sudo ./fix_permissions.sh
```

### 3. Manuelle MongoDB-Installation

Falls das automatische Script weiterhin Probleme hat:

```bash
chmod +x manual_mongodb_install.sh
sudo ./manual_mongodb_install.sh
```

### 2. Häufige Probleme und Lösungen

#### Problem: MongoDB startet nicht
```bash
# Logs prüfen
sudo journalctl -u mongod -n 50

# Berechtigungen korrigieren
sudo chown -R mongodb:mongodb /var/lib/mongodb
sudo chmod 755 /var/lib/mongodb

# MongoDB neu starten
sudo systemctl restart mongod
```

#### Problem: Port 27017 ist belegt
```bash
# Prozess finden
sudo netstat -tlnp | grep :27017

# Prozess beenden (falls nötig)
sudo kill -9 [PID]
```

#### Problem: Repository-Fehler
```bash
# GPG-Key neu hinzufügen
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

# Repository neu hinzufügen (für Linux Mint 22.x - verwendet jammy)
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# System aktualisieren
sudo apt update
```

#### Problem: Download-Berechtigungen
```bash
# Berechtigungen korrigieren
sudo ./fix_permissions.sh

# Alternative: Manueller Download
sudo mkdir -p /tmp/mongodb-download
cd /tmp/mongodb-download
sudo curl -fsSL https://pgp.mongodb.com/server-7.0.asc -o server-7.0.asc
sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg server-7.0.asc
```

#### Problem: GPG-Import-Fehler
```bash
# Manuelle MongoDB-Installation
sudo ./manual_mongodb_install.sh

# Oder manueller GPG-Import
sudo rm -f /usr/share/keyrings/mongodb-server-7.0.gpg
sudo curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
sudo chmod 644 /usr/share/keyrings/mongodb-server-7.0.gpg
```

#### Problem: Python-Abhängigkeiten
```bash
# Virtuelle Umgebung neu erstellen
sudo -u scandy python3 -m venv /opt/scandy/venv --clear
sudo -u scandy /opt/scandy/venv/bin/pip install --upgrade pip
sudo -u scandy /opt/scandy/venv/bin/pip install -r /opt/scandy/requirements.txt
```

#### Problem: Nginx-Fehler
```bash
# Nginx-Konfiguration testen
sudo nginx -t

# Nginx-Logs prüfen
sudo tail -f /var/log/nginx/error.log
```

### 3. Firewall-Konfiguration

```bash
# UFW-Status prüfen
sudo ufw status

# Ports freigeben (falls UFW aktiv ist)
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp
```

### 4. Speicherplatz prüfen

```bash
# Verfügbaren Speicherplatz anzeigen
df -h

# MongoDB-Datenbankgröße prüfen
du -sh /var/lib/mongodb
```

## Deinstallation

```bash
# Services stoppen
sudo systemctl stop scandy
sudo systemctl stop mongod
sudo systemctl stop nginx

# Services deaktivieren
sudo systemctl disable scandy
sudo systemctl disable mongod

# Dateien entfernen
sudo rm -rf /opt/scandy
sudo rm /etc/systemd/system/scandy.service
sudo rm /etc/nginx/sites-enabled/scandy
sudo rm /etc/nginx/sites-available/scandy

# MongoDB entfernen
sudo apt remove --purge mongodb-org*
sudo rm -rf /var/lib/mongodb
sudo rm -rf /var/log/mongodb
sudo rm /etc/mongod.conf

# Systemd neu laden
sudo systemctl daemon-reload
```

## Support

Bei Problemen:

1. Führen Sie das Troubleshooting-Script aus
2. Prüfen Sie die Logs der betroffenen Services
3. Stellen Sie sicher, dass alle Voraussetzungen erfüllt sind
4. Überprüfen Sie die Firewall-Einstellungen

## Unterschiede zum ursprünglichen Script

Das neue Script `install_scandy_lxc_linux_mint.sh` behebt folgende Probleme:

- **Linux Mint Kompatibilität**: Korrekte Erkennung der Linux Mint Version
- **MongoDB Repository**: Verwendet den richtigen Ubuntu-Codename für das Repository
- **Authentifizierung**: Richtet MongoDB-Authentifizierung korrekt ein
- **Fehlerbehandlung**: Bessere Fehlerbehandlung und Logging
- **Berechtigungen**: Korrekte Berechtigungen für alle Verzeichnisse
- **Service-Abhängigkeiten**: Korrekte Abhängigkeiten zwischen Services

## Version

- **Script-Version**: 2.0
- **MongoDB-Version**: 7.0
- **Python-Version**: 3.x
- **Getestet auf**: Linux Mint 21.3, 20.3 