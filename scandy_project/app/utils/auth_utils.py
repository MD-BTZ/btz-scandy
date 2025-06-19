from functools import wraps
from flask import session, redirect, url_for, flash, request, g
import logging
from werkzeug.security import check_password_hash
from app.models.mongodb_database import MongoDB

logger = logging.getLogger(__name__)
mongodb = MongoDB()

def needs_setup():
    """Überprüft, ob ein Admin-Benutzer in der MongoDB existiert.

    Returns:
        bool: True, wenn kein Admin-Benutzer gefunden wurde oder ein Fehler auftrat,
              andernfalls False.
    """
    try:
        # Prüfe, ob mindestens ein Admin existiert
        admin_count = mongodb.count_documents('users', {'role': 'admin'})
        return admin_count == 0  # True wenn kein Admin gefunden wurde
    except Exception as e:
        # Wenn Collection oder DB nicht existiert oder anderer Fehler, ist Setup nötig
        print(f"Fehler beim Prüfen auf Admin-Benutzer für Setup: {e}")
        return True

def is_admin_user_present():
    try:
        admin_count = mongodb.count_documents('users', {'role': 'admin'})
        return admin_count > 0
    except Exception as e:
        print(f"Fehler beim Prüfen auf Admin-Benutzer: {e}")
        return False

# Entferne die veraltete check_password Funktion
# def check_password(username, password):
#     ... 