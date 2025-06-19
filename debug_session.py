#!/usr/bin/env python3
"""
Debug-Script für Session-Probleme
"""
from app import create_app
from flask_login import current_user
from app.models.mongodb_models import MongoDBUser

app = create_app()

with app.app_context():
    print("=== Session Debug ===")
    
    # Prüfe MongoDB-Verbindung
    try:
        users = list(MongoDBUser.get_all())
        print(f"Anzahl Benutzer in MongoDB: {len(users)}")
        for user in users:
            print(f"  - {user['username']} (ID: {user['_id']}, Role: {user.get('role', 'anwender')})")
    except Exception as e:
        print(f"Fehler beim Laden der Benutzer: {e}")
    
    # Prüfe Session-Verzeichnis
    import os
    session_dir = app.config.get('SESSION_FILE_DIR')
    print(f"Session-Verzeichnis: {session_dir}")
    print(f"Session-Verzeichnis existiert: {os.path.exists(session_dir)}")
    
    # Prüfe Session-Konfiguration
    print(f"SESSION_TYPE: {app.config.get('SESSION_TYPE')}")
    print(f"SESSION_PERMANENT: {app.config.get('SESSION_PERMANENT')}")
    print(f"SECRET_KEY gesetzt: {bool(app.config.get('SECRET_KEY'))}") 