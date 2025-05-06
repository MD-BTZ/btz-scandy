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

# Starte Gunicorn mit Reload-Funktion
echo "Starte Gunicorn mit Reload-Überwachung für tmp/needs_restart..."
gunicorn -w 4 -b 0.0.0.0:5000 --reload --reload-extra-file tmp/needs_restart app.wsgi:application 