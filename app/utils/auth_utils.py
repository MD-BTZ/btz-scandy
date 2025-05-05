from app.models.database import Database
from werkzeug.security import check_password_hash
# Hinweis: get_auth_db_connection wird nicht mehr benötigt

def needs_setup():
    """Überprüft, ob ein Admin-Benutzer in der Hauptdatenbank existiert.

    Returns:
        bool: True, wenn kein Admin-Benutzer gefunden wurde oder ein Fehler auftrat,
              andernfalls False.
    """
    # Importiere hier nicht mehr
    try:
        # Prüfe, ob mindestens ein Admin existiert
        admin_user = Database.query("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1", one=True)
        return admin_user is None # True wenn kein Admin gefunden wurde
    except Exception as e:
        # Wenn Tabelle oder DB nicht existiert oder anderer Fehler, ist Setup nötig
        print(f"Fehler beim Prüfen auf Admin-Benutzer für Setup: {e}")
        return True

# Entferne die veraltete check_password Funktion
# def check_password(username, password):
#     ... 