#!/bin/bash

# Setup-Skript für Scandy Instance 2 auf Server
echo "========================================"
echo "Scandy Instance 2 Server Setup"
echo "========================================"

# Server-spezifische Einstellungen
SERVER_DIR="/opt/scandy-instance2"
CURRENT_DIR=$(pwd)

# Prüfe ob Zielordner bereits existiert
if [ -d "$SERVER_DIR" ]; then
    echo "Warnung: Ordner '$SERVER_DIR' existiert bereits!"
    read -p "Möchtest du ihn überschreiben? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup abgebrochen."
        exit 1
    fi
    sudo rm -rf "$SERVER_DIR"
fi

echo "Erstelle Server-Ordner für Instance 2..."
sudo mkdir -p "$SERVER_DIR"
sudo chown $USER:$USER "$SERVER_DIR"

echo "Kopiere alle Dateien..."
cp -r app/ "$SERVER_DIR/"
cp -r docs/ "$SERVER_DIR/"
cp -r mongo-init/ "$SERVER_DIR/"
cp -r static/ "$SERVER_DIR/"
cp -r uploads/ "$SERVER_DIR/"
cp -r backups/ "$SERVER_DIR/"
cp -r logs/ "$SERVER_DIR/"

# Kopiere wichtige Dateien
cp docker-compose-instance2.yml "$SERVER_DIR/docker-compose.yml"
cp Dockerfile "$SERVER_DIR/"
cp requirements.txt "$SERVER_DIR/"
cp package.json "$SERVER_DIR/"
cp tailwind.config.js "$SERVER_DIR/"
cp postcss.config.js "$SERVER_DIR/"
cp .dockerignore "$SERVER_DIR/"

# Kopiere Skripte
cp start_instance2.sh "$SERVER_DIR/start.sh"
cp stop_instance2.sh "$SERVER_DIR/stop.sh"
cp status_instance2.sh "$SERVER_DIR/status.sh"

# Erstelle .env-Datei
cp env_instance2.example "$SERVER_DIR/.env"

echo "Erstelle .gitignore für Instance 2..."
cat > "$SERVER_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Datenbanken
*.db
*.sqlite
*.sqlite3
app/database/
backups/

# Scandy Datenverzeichnisse
scandy_data/
scandy_project/scandy_data/
DATA_DIR/
REPO_DIR/

# Logs
*.log
logs/

# Uploads
app/uploads/
app/static/uploads/

# Generierte Word-Dokumente
app/uploads/**/*.docx
app/uploads/**/*.doc
app/uploads/**/*.pdf
app/uploads/**/*.xlsx
app/uploads/**/*.xls
app/static/uploads/**/*.docx
app/static/uploads/**/*.doc
app/static/uploads/**/*.pdf
app/static/uploads/**/*.xlsx
app/static/uploads/**/*.xls

# Temporäre generierte Dateien
*ticket_*_export.docx
*woplan_*.docx
*auftrag_*.docx
*tmp*.docx

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Temporäre Dateien
*.tmp
*.bak
*.swp
*~

# Flask Session
app/flask_session/*
!app/flask_session/.gitkeep
instance/flask_session/*
!instance/flask_session/.gitkeep

# Build artifacts
*.spec
dist/
*.egg-info/
/htmlcov/
.pytest_cache/
.coverage

# Archivdateien
*.tar.gz
scandy.tar.gz
scandy_docker.tar.gz

# Node.js / npm
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
package-lock.json

# Environment files
.env
.env.local
.env.production

# Docker volumes
*_project/

# Build artifacts
*.css.map
*.js.map
EOF

echo "Erstelle README für Instance 2..."
cat > "$SERVER_DIR/README.md" << 'EOF'
# Scandy Instance 2 (Server)

Dies ist eine separate Installation von Scandy auf dem Server.

## Ports
- **App**: http://localhost:5001
- **MongoDB Admin**: http://localhost:8082
- **MongoDB**: localhost:27018

## Verwaltung
```bash
# Starten
./start.sh

# Stoppen
./stop.sh

# Status
./status.sh
```

## Datenbank
- **Datenbank-Name**: scandy_instance2
- **Separate Daten**: Diese Instanz hat ihre eigene Datenbank

## Updates
Diese Instanz kann unabhängig von der Hauptinstallation aktualisiert werden.

## Server-spezifische Hinweise
- Installiert in: /opt/scandy-instance2
- Separate Docker-Volumes
- Unabhängige Logs und Backups
EOF

echo "Berechtigungen setzen..."
chmod +x "$SERVER_DIR/start.sh"
chmod +x "$SERVER_DIR/stop.sh"
chmod +x "$SERVER_DIR/status.sh"

echo "Erstelle systemd Service (optional)..."
cat > "$SERVER_DIR/scandy-instance2.service" << EOF
[Unit]
Description=Scandy Instance 2
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$SERVER_DIR
ExecStart=$SERVER_DIR/start.sh
ExecStop=$SERVER_DIR/stop.sh
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

echo "========================================"
echo "Server Setup abgeschlossen!"
echo "========================================"
echo
echo "Instance 2 wurde erstellt in: $SERVER_DIR"
echo
echo "Nächste Schritte:"
echo "1. cd $SERVER_DIR"
echo "2. Bearbeite .env-Datei (Passwörter, etc.)"
echo "3. ./start.sh"
echo
echo "Optional - Systemd Service installieren:"
echo "sudo cp $SERVER_DIR/scandy-instance2.service /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable scandy-instance2"
echo "sudo systemctl start scandy-instance2"
echo
echo "Zugriff:"
echo "- App: http://localhost:5001"
echo "- MongoDB Admin: http://localhost:8082"
echo 