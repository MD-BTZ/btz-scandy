#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Funktion zur Überprüfung, ob ein Befehl existiert
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Installiere Scandy..."

# --- Python & Pip --- 
echo "[1/4] Überprüfe Python und Pip..."
if ! command_exists python3; then
    echo "FEHLER: Python 3 ist nicht installiert. Bitte installieren Sie Python 3." >&2
    exit 1
fi
if ! command_exists pip3; then
    echo "FEHLER: pip3 ist nicht installiert. Bitte installieren Sie pip für Python 3 (oft python3-pip)." >&2
    exit 1
fi

# --- Virtuelle Umgebung --- 
echo "[2/4] Erstelle virtuelle Umgebung (venv)..."
python3 -m venv venv
source venv/bin/activate

# --- Python-Abhängigkeiten --- 
echo "[3/4] Installiere Python-Abhängigkeiten aus requirements.txt..."
pip install -r requirements.txt

# --- Node.js, npm & Tailwind CSS --- 
echo "[4/4] Richte Tailwind CSS ein..."
if ! command_exists node || ! command_exists npm; then
    echo "WARNUNG: Node.js und/oder npm nicht gefunden."
    echo "Tailwind CSS benötigt Node.js und npm zum Kompilieren der Stylesheets."
    echo "Bitte installieren Sie Node.js und npm manuell."
    echo "Für Debian/Ubuntu/Raspberry Pi OS: sudo apt update && sudo apt install nodejs npm"
    echo "Nach der Installation führen Sie bitte manuell folgende Befehle im Projektverzeichnis aus:"
    echo "1. npm install"
    echo "2. npm run build:css"
    # Optional: Skript hier beenden oder weitermachen?
    # Wir machen weiter, aber CSS wird fehlen, bis manuell nachgeholt.
    echo "Installation wird fortgesetzt, aber CSS wird möglicherweise nicht korrekt generiert."
else
    echo "Installiere npm-Abhängigkeiten (tailwindcss, daisyui)..."
    npm install
    echo "Generiere CSS-Datei mit Tailwind..."
    npm run build:css
fi

deactivate

# Update-Skript ausführbar machen
chmod +x app/update.sh

echo "------------------------------------"
echo "Scandy Installation abgeschlossen!"
echo ""
echo "So starten Sie die Anwendung:"
echo "1. Aktivieren Sie die virtuelle Umgebung: source venv/bin/activate"
echo "2. Starten Sie den Server: ./start.sh"
echo "------------------------------------" 