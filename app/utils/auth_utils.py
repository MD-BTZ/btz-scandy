from app.models.database import Database
from werkzeug.security import check_password_hash
# Hinweis: get_auth_db_connection wird lokal in needs_setup importiert, um Zirkelimporte zu vermeiden

def needs_setup():
    """Überprüft, ob die Benutzerdatenbank leer ist (d.h. Setup benötigt wird).

    Verwendet die separate Benutzerdatenbank (users.db).

    Returns:
        bool: True, wenn keine Benutzer in der DB gefunden wurden oder ein Fehler auftrat,
              andernfalls False.
    """
    # Importiere hier lokal, um Zirkelbezug zu vermeiden
    from app.routes.auth import get_user_db as get_auth_db_connection
    try:
        # Verwende die korrekte DB-Verbindung für User
        with get_auth_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            return user_count == 0
    except Exception as e:
        # Wenn Tabelle oder DB nicht existiert oder anderer Fehler, ist Setup nötig
        print(f"Fehler beim Prüfen der User-DB für Setup: {e}")
        return True

def check_password(username, password):
    """Überprüft die Anmeldedaten eines Benutzers gegen die users.db.

    Args:
        username (str): Der eingegebene Benutzername.
        password (str): Das eingegebene Passwort.

    Returns:
        tuple[bool, dict | None]: Ein Tupel (success, user_data).
                                 success ist True bei korrekten Daten, sonst False.
                                 user_data ist das Dictionary des Benutzers bei Erfolg, sonst None.
    """
    # Importiere hier lokal, um Zirkelbezug zu vermeiden
    from app.routes.auth import get_user_db as get_auth_db_connection
    try:
        with get_auth_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                return True, dict(user) # Konvertiere Row zu Dict
            return False, None
    except Exception as e:
        print(f"Fehler bei der Passwortüberprüfung: {str(e)}")
        return False, None 