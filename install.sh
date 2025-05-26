#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Funktion zur Überprüfung, ob ein Befehl existiert
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Funktion zum Überprüfen, ob ein Port verfügbar ist
check_port() {
    if command_exists netstat; then
        netstat -tuln | grep -q ":$1 "
        return $?
    elif command_exists ss; then
        ss -tuln | grep -q ":$1 "
        return $?
    else
        echo "WARNUNG: Kann Port-Verfügbarkeit nicht prüfen. Bitte stellen Sie sicher, dass Port $1 frei ist."
        return 0
    fi
}

echo "Installiere Scandy..."

# Port-Abfrage
while true; do
    read -p "Bitte geben Sie den gewünschten Port ein (Standard: 5002): " PORT
    PORT=${PORT:-5002}
    
    # Prüfe ob Port eine Zahl ist
    if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
        echo "Bitte geben Sie eine gültige Portnummer ein."
        continue
    fi
    
    # Prüfe ob Port im gültigen Bereich ist
    if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
        echo "Bitte geben Sie einen Port zwischen 1024 und 65535 ein."
        continue
    fi
    
    # Prüfe ob Port bereits verwendet wird
    if check_port "$PORT"; then
        echo "WARNUNG: Port $PORT scheint bereits verwendet zu werden. Möchten Sie trotzdem fortfahren? (j/n)"
        read -p "> " answer
        if [[ "$answer" =~ ^[Jj]$ ]]; then
            break
        fi
    else
        break
    fi
done

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

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo "Docker ist nicht installiert. Installation wird gestartet..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker wurde installiert. Bitte melden Sie sich ab und wieder an, damit die Änderungen wirksam werden."
    exit 1
fi

# Prüfe ob Docker Compose installiert ist
if ! command -v docker compose &> /dev/null; then
    echo "Docker Compose ist nicht installiert. Installation wird gestartet..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# Erstelle Verzeichnisse
mkdir -p uploads_test backups_test

# Lade die Docker-Compose-Datei herunter
curl -o docker-compose.test.yml https://raw.githubusercontent.com/woschj/scandy2/main/docker-compose.test.yml

# Lade das Dockerfile herunter
curl -o Dockerfile https://raw.githubusercontent.com/woschj/scandy2/main/Dockerfile

# Passe den Port in der Docker-Compose-Datei an
sed -i "s/5002:5000/$PORT:5000/" docker-compose.test.yml

# Starte die Container
docker compose -f docker-compose.test.yml up -d --build

echo "Installation abgeschlossen. Die Anwendung ist unter http://localhost:$PORT erreichbar." 