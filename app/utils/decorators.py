from functools import wraps
from flask import session, redirect, url_for, request, flash
from datetime import datetime
from app.utils.logger import loggers
# needs_setup wird nur in login_required verwendet
# from app.utils.auth_utils import needs_setup

def login_required(f):
    """Decorator, der sicherstellt, dass ein Benutzer eingeloggt ist.

    Prüft zuerst, ob das System-Setup benötigt wird (via needs_setup()).
    Wenn ja, wird zur Login-Seite weitergeleitet mit einer Flash-Nachricht.
    Wenn nein, wird geprüft, ob eine 'user_id' in der Session vorhanden ist.
    Wenn nicht, wird zur Login-Seite weitergeleitet.
    Andernfalls wird die ursprüngliche Funktion ausgeführt.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Importiere needs_setup hier, um Zirkelimporte zu vermeiden
        from app.utils.auth_utils import needs_setup

        # Wenn Setup benötigt wird, zur Login-Seite weiterleiten
        if needs_setup():
            flash('System-Setup erforderlich. Bitte als Administrator anmelden.', 'info')
            return redirect(url_for('auth.login')) # Geändert von auth.setup

        # Wenn nicht eingeloggt, zum Login weiterleiten
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))

        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator, der sicherstellt, dass der eingeloggte Benutzer Admin-Rechte hat.

    Prüft, ob 'is_admin' in der Session True ist.
    Wenn nicht, wird zum Login weitergeleitet mit einer Flash-Nachricht.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bitte melden Sie sich als Administrator an.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def log_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        loggers['user_actions'].info(
            f"Route aufgerufen: {request.endpoint} - "
            f"Methode: {request.method} - "
            f"IP: {request.remote_addr} - "
            f"User-Agent: {request.user_agent} - "
            f"Args: {kwargs}"
        )
        
        if request.form:
            safe_form = {k: v for k, v in request.form.items() if 'password' not in k.lower()}
            loggers['user_actions'].info(f"Form-Daten: {safe_form}")
            
        if request.args:
            loggers['user_actions'].info(f"Query-Parameter: {dict(request.args)}")
            
        try:
            result = f(*args, **kwargs)
            return result
        except Exception as e:
            loggers['errors'].error(
                f"Fehler in {request.endpoint}: {str(e)}",
                exc_info=True
            )
            raise
    return decorated_function

def log_db_operation(operation):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = f(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                loggers['database'].info(
                    f"DB Operation: {operation} - "
                    f"Dauer: {duration:.2f}s - "
                    f"Erfolgreich: Ja"
                )
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                loggers['database'].error(
                    f"DB Operation: {operation} - "
                    f"Dauer: {duration:.2f}s - "
                    f"Fehler: {str(e)}"
                )
                raise
        return wrapper
    return decorator 