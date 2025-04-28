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

# Starte Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app.wsgi:application 