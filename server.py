import os
import logging
from app.models.database import Database
from app.models.init_db import init_users

def list_app_files():
    logging.info("=================")
    logging.info("Durchsuche App-Dateien...")
    
    for root, dirs, files in os.walk("app"):
        for file in files:
            if file.endswith((".py", ".html")):
                logging.info(f"Datei: {os.path.join(root, file)}")
    
    logging.info("=================")

if __name__ == "__main__":
    # Logging konfigurieren
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Starte Entwicklungsserver...")
    
    # Dateien auflisten
    list_app_files()
    
    # Flask-App importieren und starten
    from app import create_app
    app = create_app()
    
    # Produktionseinstellungen
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # Produktionsmodus
        app.run(debug=False, host='0.0.0.0', port=5000) 