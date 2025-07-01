from flask import current_app, g
from app.constants import Routes
from app.config.version import VERSION
import traceback
import logging
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

def get_colors():
    """Holt die Farbeinstellungen aus der MongoDB"""
    try:
        colors = {}
        color_docs = mongodb.find('settings', {'key': {'$regex': '^color_'}})
        for doc in color_docs:
            key = doc['key'].replace('color_', '')
            # Prüfe ob das value Feld existiert
            if 'value' in doc:
                colors[key] = doc['value']
        return colors
    except Exception as e:
        logger.error(f"Fehler beim Laden der Farben: {str(e)}")
        return {
            'primary': '#2c3e50',
            'secondary': '#4c5789',
            'accent': '#e74c3c',
            'background': '#ffffff',
            'text': '#2c3e50'
        }

def inject_colors():
    """Injiziert die Farbeinstellungen aus MongoDB in alle Templates"""
    try:
        color_docs = mongodb.find('settings', {'key': {'$regex': '^color_'}})
        if color_docs:
            color_dict = {}
            for doc in color_docs:
                key = doc['key'].replace('color_', '')
                # Prüfe ob das value Feld existiert
                if 'value' in doc:
                    value = doc['value']
                    color_dict[key] = value
            return {'colors': color_dict}
    except Exception as e:
        logger.error(f"Fehler beim Laden der Farben: {e}")
        logger.debug(traceback.format_exc())
    
    # Fallback-Farben
    return {
        'colors': {
            'primary': '259 94% 51%',
            'primary_content': '0 0% 100%',
            'secondary': '314 100% 47%',
            'secondary_content': '0 0% 100%',
            'accent': '174 60% 51%',
            'accent_content': '0 0% 100%',
            'neutral': '219 14% 28%',
            'neutral_content': '0 0% 100%',
            'base': '0 0% 100%',
            'base_content': '219 14% 28%'
        }
    }

def inject_routes():
    """Fügt die Routen-Konstanten in den Template-Kontext ein"""
    return {'routes': Routes}

def inject_version():
    """Fügt die aktuelle Version zu allen Templates hinzu"""
    return {
        'version': VERSION
    }

def inject_app_labels():
    """Fügt die App-Labels in alle Templates ein"""
    try:
        label_docs = mongodb.find('settings', {'key': {'$regex': '^label_'}})
        app_labels = {
            'tools': {'name': 'Werkzeuge', 'icon': 'fas fa-tools'},
            'consumables': {'name': 'Verbrauchsmaterial', 'icon': 'fas fa-box-open'},
            'tickets': {'name': 'Tickets', 'icon': 'fas fa-ticket-alt'}
        }
        
        # Labels aus der Datenbank laden
        for doc in label_docs:
            key = doc['key'].replace('label_', '')
            # Prüfe ob das value Feld existiert
            if 'value' not in doc:
                continue
            value = doc['value']
            
            # Label-Typ und Attribut extrahieren (z.B. tools_name -> tools.name)
            parts = key.split('_')
            if len(parts) == 2:
                label_type, attr = parts
                if label_type in app_labels:
                    app_labels[label_type][attr] = value
        
        return {'app_labels': app_labels}
    except Exception as e:
        logger.error(f"Fehler beim Laden der App-Labels: {str(e)}")
        return {
            'app_labels': {
                'tools': {'name': 'Werkzeuge', 'icon': 'fas fa-tools'},
                'consumables': {'name': 'Verbrauchsmaterial', 'icon': 'fas fa-box-open'},
                'tickets': {'name': 'Tickets', 'icon': 'fas fa-ticket-alt'}
            }
        }

def inject_unfilled_timesheet_days():
    """Berechnet die Anzahl fehlender Wochenberichte für alle Templates"""
    try:
        from flask import current_app, g
        from flask_login import current_user
        from datetime import datetime, timedelta
        
        # Nur für eingeloggte Benutzer mit aktiviertem Wochenbericht-Feature berechnen
        if not hasattr(current_user, 'is_authenticated') or not current_user.is_authenticated:
            return {'unfilled_timesheet_days': 0}
        
        # Prüfe ob Wochenbericht-Feature aktiviert ist
        if not hasattr(current_user, 'timesheet_enabled') or not current_user.timesheet_enabled:
            return {'unfilled_timesheet_days': 0}
        
        # Berechne unausgefüllte Tage für den aktuellen Benutzer
        user_id = current_user.username
        today = datetime.now()
        
        # Hole alle Timesheets des Benutzers
        timesheets = list(mongodb.find('timesheets', {'user_id': user_id}))
        
        # Berechne unausgefüllte Tage für alle Wochen
        unfilled_days = 0
        for ts in timesheets:
            # Berechne den Wochenstart
            week_start = datetime.fromisocalendar(ts['year'], ts['kw'], 1)  # 1 = Montag
            days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
            
            for i, day in enumerate(days):
                # Berechne das Datum für den aktuellen Tag
                current_day = week_start + timedelta(days=i)
                
                # Prüfe nur vergangene Tage
                if current_day.date() < today.date():
                    has_times = ts.get(f'{day}_start') or ts.get(f'{day}_end')
                    has_tasks = ts.get(f'{day}_tasks')
                    if not (has_times and has_tasks):
                        unfilled_days += 1
        
        return {'unfilled_timesheet_days': unfilled_days}
        
    except Exception as e:
        logger.error(f"Fehler beim Berechnen der fehlenden Wochenberichte: {str(e)}")
        return {'unfilled_timesheet_days': 0}

def register_context_processors(app):
    """Registriert alle Context Processors"""
    app.context_processor(inject_colors)
    app.context_processor(inject_routes)
    app.context_processor(inject_version)
    app.context_processor(inject_app_labels)
    app.context_processor(inject_unfilled_timesheet_days)