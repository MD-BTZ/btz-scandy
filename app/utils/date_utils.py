"""
Zentrale Datumsformatierungsfunktionen für Scandy
Alle Funktionen verwenden das deutsche Datumsformat (TT.MM.JJJJ)
"""
from datetime import datetime, timedelta
from app.config.config import Config

def format_datetime(dt, format_type='datetime'):
    """
    Formatiert ein Datum im deutschen Format
    
    Args:
        dt: Datum (datetime, string oder None)
        format_type: 'date', 'time', 'datetime', 'datetime_full'
    
    Returns:
        String im deutschen Format
    """
    return Config.format_datetime(dt, format_type)

def format_date(dt):
    """Formatiert nur das Datum (TT.MM.JJJJ)"""
    return format_datetime(dt, 'date')

def format_time(dt):
    """Formatiert nur die Zeit (HH:MM)"""
    return format_datetime(dt, 'time')

def format_datetime_full(dt):
    """Formatiert Datum und Zeit mit Sekunden (TT.MM.JJJJ HH:MM:SS)"""
    return format_datetime(dt, 'datetime_full')

def parse_datetime(date_string, format_type='datetime'):
    """
    Parst ein Datum aus deutschem Format
    
    Args:
        date_string: Datum als String
        format_type: 'date', 'time', 'datetime', 'datetime_full'
    
    Returns:
        datetime Objekt oder None
    """
    return Config.parse_datetime(date_string, format_type)

def format_relative_date(dt):
    """
    Formatiert ein relatives Datum (heute, gestern, etc.)
    
    Args:
        dt: Datum (datetime, string oder None)
    
    Returns:
        String mit relativem Datum
    """
    if not dt:
        return ''
    
    if isinstance(dt, str):
        dt = parse_datetime(dt)
        if not dt:
            return dt
    
    now = datetime.now()
    today = now.date()
    dt_date = dt.date()
    
    if dt_date == today:
        return f'Heute, {dt.strftime("%H:%M")}'
    elif dt_date == today - timedelta(days=1):
        return f'Gestern, {dt.strftime("%H:%M")}'
    elif dt_date == today + timedelta(days=1):
        return f'Morgen, {dt.strftime("%H:%M")}'
    else:
        return format_datetime(dt)

def format_duration(duration):
    """
    Formatiert eine Zeitdauer benutzerfreundlich
    
    Args:
        duration: timedelta Objekt
    
    Returns:
        String mit formatierter Dauer
    """
    if not duration:
        return '0 Minuten'
    
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

def get_week_dates(year, week):
    """
    Gibt die Datumsangaben für eine Kalenderwoche zurück
    
    Args:
        year: Jahr
        week: Kalenderwoche
    
    Returns:
        Liste mit Datumsangaben für Montag bis Freitag
    """
    week_start = datetime.fromisocalendar(year, week, 1)  # Montag
    dates = []
    
    for i in range(5):  # Montag bis Freitag
        date = week_start + timedelta(days=i)
        dates.append({
            'date': date,
            'formatted': format_date(date),
            'day_name': ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag'][i]
        })
    
    return dates

def is_workday(date):
    """
    Prüft ob ein Datum ein Arbeitstag ist (Montag-Freitag)
    
    Args:
        date: datetime Objekt
    
    Returns:
        True wenn Arbeitstag, False wenn Wochenende
    """
    return date.weekday() < 5  # 0-4 = Montag bis Freitag

def get_next_workday(date=None):
    """
    Gibt den nächsten Arbeitstag zurück
    
    Args:
        date: Startdatum (default: heute)
    
    Returns:
        datetime Objekt des nächsten Arbeitstags
    """
    if date is None:
        date = datetime.now()
    
    next_day = date + timedelta(days=1)
    while not is_workday(next_day):
        next_day += timedelta(days=1)
    
    return next_day

def format_datetime_for_database(dt):
    """
    Formatiert ein Datum für die Datenbank (internes Format)
    
    Args:
        dt: datetime Objekt
    
    Returns:
        String im Datenbankformat
    """
    if not dt:
        return None
    
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def parse_datetime_from_database(date_string):
    """
    Parst ein Datum aus der Datenbank
    
    Args:
        date_string: Datum als String aus der Datenbank
    
    Returns:
        datetime Objekt oder None
    """
    if not date_string:
        return None
    
    try:
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        return None

def get_current_week():
    """
    Gibt die aktuelle Kalenderwoche zurück
    
    Returns:
        Tuple (Jahr, Kalenderwoche)
    """
    now = datetime.now()
    return now.isocalendar()[0], now.isocalendar()[1]

def format_week_range(year, week):
    """
    Formatiert einen Wochenbereich (z.B. "15.04.2024 - 19.04.2024")
    
    Args:
        year: Jahr
        week: Kalenderwoche
    
    Returns:
        String mit Wochenbereich
    """
    dates = get_week_dates(year, week)
    start_date = format_date(dates[0]['date'])
    end_date = format_date(dates[-1]['date'])
    return f"{start_date} - {end_date}" 