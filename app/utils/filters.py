from datetime import datetime, timedelta
from app.config.version import get_version, get_author
from flask import Blueprint

def format_datetime(value):
    """Formatiert ein Datum in deutsches Format ohne Mikrosekunden"""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            # Versuche verschiedene Datumsformate
            for fmt in ['%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            # Falls kein Format passt, versuche ISO-Format
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    return value
        return value.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return value

def format_date(value):
    """Formatiert nur das Datum (ohne Zeit) in deutsches Format"""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            # Versuche verschiedene Datumsformate
            for fmt in ['%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M', '%Y-%m-%d']:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
        return value.strftime('%d.%m.%Y')
    except Exception:
        return value

def format_time(value):
    """Formatiert nur die Zeit"""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            # Versuche verschiedene Zeitformate
            for fmt in ['%Y-%m-%d %H:%M:%S', '%d.%m.%Y %H:%M', '%H:%M:%S', '%H:%M']:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
        return value.strftime('%H:%M')
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

def author_filter(value):
    """Gibt den Autor zurück (unabhängig vom Input-Wert)"""
    return get_author()

def register_filters(app):
    """Registriert alle benutzerdefinierten Filter"""
    
    @app.template_filter('datetime')
    def datetime_filter(value):
        """Formatiert ein Datum im deutschen Format"""
        return format_datetime(value)
    
    @app.template_filter('date')
    def date_filter(value):
        """Formatiert ein Datum nur mit Datum (ohne Zeit)"""
        return format_date(value)
    
    @app.template_filter('time')
    def time_filter(value):
        """Formatiert nur die Zeit"""
        return format_time(value)
    
    @app.template_filter('datetime_short')
    def datetime_short_filter(value):
        """Kurzes Datumsformat (TT.MM.JJJJ HH:MM)"""
        return format_datetime(value)
    
    @app.template_filter('datetime_long')
    def datetime_long_filter(value):
        """Langes Datumsformat mit Wochentag"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        return value.strftime('%A, %d.%m.%Y %H:%M')
    
    @app.template_filter('date_relative')
    def date_relative_filter(value):
        """Relatives Datum (heute, gestern, etc.)"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        
        now = datetime.now()
        today = now.date()
        value_date = value.date()
        
        if value_date == today:
            return f'Heute, {value.strftime("%H:%M")}'
        elif value_date == today - timedelta(days=1):
            return f'Gestern, {value.strftime("%H:%M")}'
        elif value_date == today + timedelta(days=1):
            return f'Morgen, {value.strftime("%H:%M")}'
        else:
            return value.strftime('%d.%m.%Y %H:%M')
    
    @app.template_filter('author')
    def author_filter(value):
        """Gibt den Autor zurück (unabhängig vom Input-Wert)"""
        return get_author()

    app.jinja_env.filters['format_datetime'] = format_datetime
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['format_time'] = format_time
    app.jinja_env.filters['to_datetime'] = to_datetime
    app.jinja_env.filters['format_duration'] = format_duration
    app.jinja_env.filters['nl2br'] = nl2br

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

def nl2br(value):
    """Konvertiert Zeilenumbrüche in HTML <br> Tags"""
    if not value:
        return ''
    return value.replace('\n', '<br>') 