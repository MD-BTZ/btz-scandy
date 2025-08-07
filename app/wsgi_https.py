import os
import sys
from pathlib import Path

# Füge den Projektpfad zum Python-Pfad hinzu
project_home = str(Path(__file__).parent.parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Setze die Umgebungsvariablen
os.environ['FLASK_ENV'] = 'production'
os.environ['FLASK_CONFIG'] = 'production'

# Importiere und erstelle die Flask-App
from app import create_app
app = create_app()

# Gunicorn erwartet eine 'application' Variable
application = app

if __name__ == '__main__':
    # HTTPS-Konfiguration
    ssl_cert = os.environ.get('SSL_CERT_PATH', '/app/ssl/cert.pem')
    ssl_key = os.environ.get('SSL_KEY_PATH', '/app/ssl/key.pem')
    
    # Prüfe ob SSL-Zertifikate existieren
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        print(f"Starting HTTPS server with SSL certificates...")
        print(f"Certificate: {ssl_cert}")
        print(f"Key: {ssl_key}")
        
        # HTTPS-Server starten
        app.run(
            host='0.0.0.0', 
            port=5000, 
            debug=False,
            ssl_context=(ssl_cert, ssl_key)
        )
    else:
        print("SSL certificates not found, starting HTTP server...")
        print(f"Certificate path: {ssl_cert}")
        print(f"Key path: {ssl_key}")
        app.run(host='0.0.0.0', port=5000, debug=False) 