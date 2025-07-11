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
cp -r app/ "$INSTANCE2_DIR/"
cp -r docs/ "$INSTANCE2_DIR/"
cp -r mongo-init/ "$INSTANCE2_DIR/"
cp -r static/ "$INSTANCE2_DIR/"
cp -r uploads/ "$INSTANCE2_DIR/"
cp -r backups/ "$INSTANCE2_DIR/"
cp -r logs/ "$INSTANCE2_DIR/"

# Kopiere wichtige Dateien
cp docker-compose-instance2.yml "$INSTANCE2_DIR/docker-compose.yml"
cp Dockerfile "$INSTANCE2_DIR/"
cp requirements.txt "$INSTANCE2_DIR/"
cp package.json "$INSTANCE2_DIR/"
cp tailwind.config.js "$INSTANCE2_DIR/"
cp postcss.config.js "$INSTANCE2_DIR/"
cp .dockerignore "$INSTANCE2_DIR/"

# Kopiere Skripte
cp start_instance2.sh "$INSTANCE2_DIR/start.sh"
cp stop_instance2.sh "$INSTANCE2_DIR/stop.sh"
cp status_instance2.sh "$INSTANCE2_DIR/status.sh"

# Erstelle .env-Datei
cp env_instance2.example "$INSTANCE2_DIR/.env"

echo "Erstelle .gitignore für Instance 2..."
cat > "$INSTANCE2_DIR/.gitignore" << 'EOF'
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
cat > "$INSTANCE2_DIR/README.md" << 'EOF'
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
chmod +x "$INSTANCE2_DIR/start.sh"
chmod +x "$INSTANCE2_DIR/stop.sh"
chmod +x "$INSTANCE2_DIR/status.sh"

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