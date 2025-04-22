#!/bin/bash

# Erstelle virtuelle Umgebung, falls sie nicht existiert
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Aktiviere virtuelle Umgebung
source venv/bin/activate

# Installiere Abhängigkeiten
pip install -r requirements.txt

# Erstelle notwendige Verzeichnisse
mkdir -p app/database
mkdir -p app/logs
mkdir -p app/uploads
mkdir -p app/flask_session

# Mache Startskript ausführbar
chmod +x start.sh

echo "Installation abgeschlossen. Starten Sie die Anwendung mit './start.sh'" 