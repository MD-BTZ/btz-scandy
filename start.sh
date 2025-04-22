#!/bin/bash

# Aktiviere die virtuelle Umgebung
source venv/bin/activate

# Starte Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app.wsgi:application 