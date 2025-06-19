# Installation und Setup

## Übersicht

Dieses Dokument beschreibt die Installation von Scandy in verschiedenen Umgebungen:
1. Lokale Entwicklungsumgebung
2. Produktionsserver
3. Docker-Container

## 1. Lokale Entwicklungsumgebung

### Voraussetzungen
- Python 3.x
- Git
- Virtuelle Umgebung (venv)

### Installationsschritte

1. **Repository klonen**
   ```bash
   git clone <repository-url>
   cd scandy
   ```

2. **Virtuelle Umgebung erstellen und aktivieren**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

4. **MongoDB einrichten**
   ```bash
   # Stellen Sie sicher, dass MongoDB läuft
   sudo systemctl start mongod
   sudo systemctl enable mongod
   ```

5. **Entwicklungsserver starten**
   ```bash
   flask run
   ```

Die Anwendung ist nun unter `http://127.0.0.1:5000` erreichbar.

## 2. Produktionsserver

### Voraussetzungen
- Linux-Server (empfohlen: Ubuntu 20.04 LTS oder neuer)
- Python 3.x
- Nginx
- Gunicorn
- Systemd

### Installationsschritte

1. **Systempakete installieren**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx
   ```

2. **Anwendung herunterladen**
   ```bash
   git clone <repository-url>
   cd scandy
   ```

3. **Virtuelle Umgebung erstellen**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install gunicorn
   ```

4. **Systemd-Service erstellen**
   ```bash
   sudo nano /etc/systemd/system/scandy.service
   ```

   Service-Datei-Inhalt:
   ```ini
   [Unit]
   Description=Scandy Web Application
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/scandy
   Environment="PATH=/path/to/scandy/venv/bin"
   ExecStart=/path/to/scandy/venv/bin/gunicorn --workers 3 --bind unix:scandy.sock -m 007 wsgi:app

   [Install]
   WantedBy=multi-user.target
   ```

5. **Nginx konfigurieren**
   ```bash
   sudo nano /etc/nginx/sites-available/scandy
   ```

   Nginx-Konfiguration:
   ```nginx
   server {
       listen 80;
       server_name your_domain.com;

       location / {
           include proxy_params;
           proxy_pass http://unix:/path/to/scandy/scandy.sock;
       }
   }
   ```

6. **Dienste starten**
   ```bash
   sudo systemctl start scandy
   sudo systemctl enable scandy
   sudo systemctl restart nginx
   ```

## 3. Docker-Installation

### Voraussetzungen
- Docker
- Docker Compose

### Installationsschritte

1. **Docker-Image bauen**
   ```bash
   docker build -t scandy .
   ```

2. **Docker Compose starten**
   ```bash
   docker-compose up -d
   ```

Die Anwendung ist nun unter `http://localhost:5000` erreichbar.

## Datenbank-Setup

Die Anwendung verwendet MongoDB als Datenbank. Für die Installation stehen folgende Optionen zur Verfügung:

### Option 1: Lokale MongoDB-Installation

1. **MongoDB installieren:**
   - **Ubuntu/Debian:** `sudo apt-get install mongodb`
   - **CentOS/RHEL:** `sudo yum install mongodb-org`
   - **macOS:** `brew install mongodb-community`
   - **Windows:** Download von [mongodb.com](https://www.mongodb.com/try/download/community)

2. **MongoDB starten:**
   ```bash
   sudo systemctl start mongod
   sudo systemctl enable mongod
   ```

3. **Datenbanken erstellen:**
   ```bash
   mongo
   use scandy
   use scandy_tickets
   ```

### Option 2: Docker (Empfohlen)

Die Anwendung enthält bereits eine `docker-compose.yml` Datei mit MongoDB-Konfiguration:

```bash
docker-compose up -d
```

### Option 3: MongoDB Atlas (Cloud)

1. Konto bei [MongoDB Atlas](https://www.mongodb.com/atlas) erstellen
2. Cluster erstellen
3. Verbindungsstring in der Konfiguration verwenden

## Konfiguration

### Umgebungsvariablen

Wichtige Umgebungsvariablen:
- `SECRET_KEY`: Geheimer Schlüssel für die Anwendung
- `FLASK_ENV`: Entwicklung oder Produktion
- `DATABASE_URL`: Datenbankverbindungs-URL

### Datenbank

Die Anwendung verwendet standardmäßig MongoDB. Für Produktionsumgebungen kann eine andere Datenbank konfiguriert werden.

### Backup-Konfiguration

Backups werden automatisch erstellt. Die Konfiguration erfolgt in `app/config.py`.

## Wichtige Hinweise

1. **Sicherheit**
   - Ändern Sie den `SECRET_KEY` in Produktionsumgebungen
   - Konfigurieren Sie HTTPS
   - Regelmäßige Backups durchführen

2. **Wartung**
   - Regelmäßige Updates durchführen
   - Logs überwachen
   - Speicherplatz überprüfen

3. **Fehlerbehebung**
   - Logs in `logs/` überprüfen
   - Debug-Modus bei Problemen aktivieren
   - Datenbank-Integrität prüfen 