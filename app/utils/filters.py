from datetime import datetime

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
    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['to_datetime'] = to_datetime
    app.jinja_env.filters['format_duration'] = format_duration 