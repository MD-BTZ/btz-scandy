from app.models.ticket_db import TicketDatabase
from werkzeug.security import check_password_hash
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
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
        ticket_db = TicketDatabase()
        admin_user = ticket_db.query("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1", one=True)
        return admin_user is None # True wenn kein Admin gefunden wurde
    except Exception as e:
        # Wenn Tabelle oder DB nicht existiert oder anderer Fehler, ist Setup nötig
        print(f"Fehler beim Prüfen auf Admin-Benutzer für Setup: {e}")
        return True

def is_admin_user_present():
    ticket_db = TicketDatabase()
    admin_user = ticket_db.query("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1", one=True)
    return admin_user is not None

# Entferne die veraltete check_password Funktion
# def check_password(username, password):
#     ... 

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Sie haben keine Berechtigung für diese Aktion.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function 