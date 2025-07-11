#!/bin/bash

# Setup-Skript für Scandy Instance 2 in separatem Ordner
echo "========================================"
echo "Scandy Instance 2 Setup"
echo "========================================"

# Prüfe ob Zielordner bereits existiert
INSTANCE2_DIR="scandy-instance2"
if [ -d "$INSTANCE2_DIR" ]; then
    echo "Warnung: Ordner '$INSTANCE2_DIR' existiert bereits!"
    read -p "Möchtest du ihn überschreiben? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup abgebrochen."
        exit 1
    fi
    rm -rf "$INSTANCE2_DIR"
fi

echo "Erstelle Ordner für Instance 2..."
mkdir -p "$INSTANCE2_DIR"

echo "Kopiere alle Dateien..."
# Kopiere das gesamte Verzeichnis
cp -r . "$INSTANCE2_DIR/"

echo "Bereinige Instance 2 Ordner..."
cd "$INSTANCE2_DIR"

# Entferne nicht benötigte Dateien
rm -rf .git
rm -rf venv
rm -rf node_modules
rm -rf __pycache__
rm -rf .DS_Store
rm -f backup.log
rm -f package-lock.json

# Entferne andere Docker-Compose-Dateien
rm -f docker-compose.btz.yml
rm -f docker-compose.dynamic.yml
rm -f docker-compose.verwaltung.yml
rm -f docker-compose.werkstatt.yml

# Entferne andere Skripte
rm -f start_*.sh
rm -f stop_*.sh
rm -f status_*.sh
rm -f setup_*.sh

# Erstelle angepasste Skripte für Instance 2
echo "Erstelle angepasste Skripte für Instance 2..."

# Start-Skript
cat > "start.sh" << 'EOF'
#!/bin/bash

# Start-Skript für Scandy Instance 2
echo "Starte Scandy Instance 2..."

# Prüfe ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo "Fehler: Docker läuft nicht!"
    exit 1
fi

# Starte die zweite Instanz
docker compose up -d

echo "Scandy Instance 2 wird gestartet..."
echo "App wird verfügbar sein unter: http://localhost:5001"
echo "MongoDB Admin unter: http://localhost:8082"
echo ""
echo "Status prüfen mit: docker compose ps"
EOF

# Stop-Skript
cat > "stop.sh" << 'EOF'
#!/bin/bash

# Stopp-Skript für Scandy Instance 2
echo "Stoppe Scandy Instance 2..."

# Stoppe die zweite Instanz
docker compose down

echo "Scandy Instance 2 wurde gestoppt."
EOF

# Status-Skript
cat > "status.sh" << 'EOF'
#!/bin/bash

# Status-Skript für Scandy Instance 2
echo "Status von Scandy Instance 2:"
echo "================================"

# Zeige Container-Status
docker compose ps

echo ""
echo "Logs der letzten 20 Zeilen:"
echo "================================"
docker compose logs --tail=20
EOF

# Erstelle .env-Datei aus der Vorlage
cp env_instance2.example .env

echo "Erstelle .gitignore für Instance 2..."
cat > ".gitignore" << 'EOF'
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
cat > "README.md" << 'EOF'
# Scandy Instance 2

Dies ist eine separate Installation von Scandy.

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
EOF

echo "Berechtigungen setzen..."
chmod +x "start.sh"
chmod +x "stop.sh"
chmod +x "status.sh"

cd ..

echo "========================================"
echo "Setup abgeschlossen!"
echo "========================================"
echo
echo "Instance 2 wurde erstellt in: $INSTANCE2_DIR"
echo
echo "Nächste Schritte:"
echo "1. cd $INSTANCE2_DIR"
echo "2. Bearbeite .env-Datei (Passwörter, etc.)"
echo "3. ./start.sh"
echo
echo "Zugriff:"
echo "- App: http://localhost:5001"
echo "- MongoDB Admin: http://localhost:8082"
echo 