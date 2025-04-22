import os
import sys

# Füge den Projektpfad zum Python-Pfad hinzu
project_home = '/home/pi/scandy'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Setze die Umgebungsvariablen
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'

# Importiere und erstelle die Flask-App
from app import create_app
application = create_app()

if __name__ == '__main__':
    application.run() 