#!/bin/bash

echo "=== LXC Layout Debug Script ==="

# 1. Prüfe Static Files
echo "1. Prüfe Static Files..."
if [ -d "app/static" ]; then
    echo "✅ Static-Verzeichnis gefunden"
    ls -la app/static/
else
    echo "❌ Static-Verzeichnis fehlt"
fi

# 2. Prüfe CSS-Dateien
echo "2. Prüfe CSS-Dateien..."
if [ -f "app/static/css/main.css" ]; then
    echo "✅ main.css gefunden"
    ls -la app/static/css/
else
    echo "❌ main.css fehlt - kompiliere Tailwind CSS"
    if command -v npx &> /dev/null; then
        npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/main.css
    else
        echo "npm/npx nicht verfügbar"
    fi
fi

# 3. Prüfe Berechtigungen
echo "3. Prüfe Berechtigungen..."
if [ -d "app/static" ]; then
    chmod -R 755 app/static/
    echo "✅ Berechtigungen korrigiert"
fi

# 4. Prüfe Flask-Konfiguration
echo "4. Prüfe Flask-Konfiguration..."
python3 -c "
from app import create_app
app = create_app()
print(f'Static Folder: {app.static_folder}')
print(f'Static URL Path: {app.static_url_path}')
print(f'Debug Mode: {app.debug}')
"

# 5. Prüfe Netzwerk-Zugriff
echo "5. Prüfe Netzwerk-Zugriff..."
curl -s http://localhost:5000/static/css/main.css > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Static Files über HTTP erreichbar"
else
    echo "❌ Static Files nicht erreichbar"
fi

echo "=== Debug abgeschlossen ===" 