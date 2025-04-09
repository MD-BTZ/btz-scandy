from functools import wraps
from flask import render_template, flash
import sqlite3
import logging

logger = logging.getLogger(__name__)

def handle_errors(f):
    """Decorator für einheitliche Fehlerbehandlung in Routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"Datenbankfehler in {f.__name__}: {str(e)}")
            flash('Datenbankfehler aufgetreten', 'error')
            return render_template('error.html',
                                message="Es ist ein Datenbankfehler aufgetreten.",
                                details=str(e))
        except Exception as e:
            logger.error(f"Unerwarteter Fehler in {f.__name__}: {str(e)}")
            flash('Ein unerwarteter Fehler ist aufgetreten', 'error')
            return render_template('error.html',
                                message="Ein unerwarteter Fehler ist aufgetreten.",
                                details=str(e))
    return decorated_function

def safe_db_query(func):
    """Decorator für sichere Datenbankabfragen"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"Datenbankfehler in {func.__name__}: {str(e)}")
            return []  # Leere Liste bei Datenbankfehlern
        except Exception as e:
            logger.error(f"Unerwarteter Fehler in {func.__name__}: {str(e)}")
            return []
    return wrapper