#!/bin/bash

# Beende laufende Prozesse auf Port 5000
echo "Prüfe auf laufende Prozesse auf Port 5000..."
PID=$(lsof -t -i:5000)
if [ ! -z "$PID" ]; then
    echo "Beende laufende Prozesse auf Port 5000..."
    kill -9 $PID
    sleep 2
fi

# Aktiviere die virtuelle Umgebung
source venv/bin/activate

# Überprüfe und installiere Requirements
echo "Überprüfe und installiere fehlende Pakete..."
pip install -r requirements.txt

# Setze Debug-Umgebungsvariable
export FLASK_DEBUG=1
export FLASK_ENV=development

# Starte Gunicorn mit Reload-Funktion und Debug-Modus
echo "Starte Gunicorn mit Reload-Überwachung und Debug-Modus..."
gunicorn -w 4 -b 0.0.0.0:5000 --reload --reload-extra-file tmp/needs_restart --log-level debug app.wsgi:application 