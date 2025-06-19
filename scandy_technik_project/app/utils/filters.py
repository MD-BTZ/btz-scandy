from datetime import datetime
from app.config.version import get_version, get_author

def format_datetime(value):
    """Formatiert ein Datum in deutsches Format"""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            # Versuche verschiedene Datumsformate
            for fmt in ['%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M']:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
        return value.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return value

def to_datetime(value):
    """Konvertiert einen String in ein datetime Objekt"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

def format_duration(duration):
    """Formatiert eine Zeitdauer benutzerfreundlich"""
    total_seconds = int(duration.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} {'Tag' if days == 1 else 'Tage'}")
    if hours > 0:
        parts.append(f"{hours} {'Stunde' if hours == 1 else 'Stunden'}")
    if minutes > 0 and days == 0:  # Minuten nur anzeigen wenn weniger als 1 Tag
        parts.append(f"{minutes} {'Minute' if minutes == 1 else 'Minuten'}")
    
    return ' '.join(parts) if parts else 'Weniger als 1 Minute'

def register_filters(app):
    """Registriert Template-Filter für die Flask-Anwendung"""
    
    @app.template_filter('version')
    def version_filter(s):
        return get_version()
    
    @app.template_filter('author')
    def author_filter(s):
        return get_author()

    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['to_datetime'] = to_datetime
    app.jinja_env.filters['format_duration'] = format_duration

def status_color(status):
    """Gibt die Bootstrap-Farbe für einen Ticket-Status zurück"""
    colors = {
        'offen': 'warning',
        'in_bearbeitung': 'info',
        'wartet_auf_antwort': 'secondary',
        'gelöst': 'success',
        'geschlossen': 'dark'
    }
    return colors.get(status.lower(), 'secondary')

def priority_color(priority):
    """Gibt die Bootstrap-Farbe für eine Ticket-Priorität zurück"""
    colors = {
        'niedrig': 'success',
        'mittel': 'warning',
        'hoch': 'danger',
        'dringend': 'danger'
    }
    return colors.get(priority.lower(), 'secondary') 