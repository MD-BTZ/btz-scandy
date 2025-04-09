from app.models.database import Database
from werkzeug.security import check_password_hash

def needs_setup():
    """Überprüft, ob die Anwendung noch eingerichtet werden muss"""
    try:
        with Database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            return user_count == 0
    except Exception:
        return True

def check_password(username, password):
    """Überprüft die Anmeldedaten eines Benutzers"""
    try:
        with Database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                return True, user
            return False, None
    except Exception as e:
        print(f"Fehler bei der Passwortüberprüfung: {str(e)}")
        return False, None 