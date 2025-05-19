import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Basis-Konfiguration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TICKET_DATABASE = os.path.join(basedir, 'app/database/tickets.db')
    SYSTEM_NAME = os.environ.get('SYSTEM_NAME') or 'Scandy'
    TICKET_SYSTEM_NAME = os.environ.get('TICKET_SYSTEM_NAME') or 'Aufgaben'
    # TOOL_SYSTEM_NAME und CONSUMABLE_SYSTEM_NAME werden dynamisch aus der Datenbank geladen
    # und daher hier nicht mehr statisch definiert
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads') 