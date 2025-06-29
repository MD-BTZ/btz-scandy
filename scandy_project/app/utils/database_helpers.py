"""
Datenbank-Hilfsfunktionen für Scandy
"""

from app.models.mongodb_database import mongodb
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_ticket_categories_from_settings():
    """Lädt Ticket-Kategorien aus der settings Collection"""
    try:
        settings_doc = mongodb.find_one('settings', {'key': 'ticket_categories'})
        if settings_doc and 'value' in settings_doc:
            return settings_doc['value']
        return []
    except Exception as e:
        logger.error(f"Fehler beim Laden der Ticket-Kategorien: {e}")
        return []

def get_categories_from_settings():
    """Lädt Kategorien aus der settings Collection oder der categories Collection"""
    try:
        # Versuche zuerst die settings Collection
        settings_doc = mongodb.find_one('settings', {'key': 'categories'})
        if settings_doc and 'value' in settings_doc:
            value = settings_doc['value']
            # Wenn es ein String ist, splitte ihn an Kommas
            if isinstance(value, str):
                return [cat.strip() for cat in value.split(',') if cat.strip()]
            # Wenn es bereits eine Liste ist, verwende sie direkt
            elif isinstance(value, list):
                return value
        return []
        
        # Fallback: Verwende die ursprüngliche categories Collection
        categories = mongodb.find('categories', {'deleted': {'$ne': True}})
        return [cat['name'] for cat in categories if 'name' in cat]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Kategorien: {e}")
        return []

def get_locations_from_settings():
    """Lädt Standorte aus der settings Collection oder der locations Collection"""
    try:
        # Versuche zuerst die settings Collection
        settings_doc = mongodb.find_one('settings', {'key': 'locations'})
        if settings_doc and 'value' in settings_doc:
            value = settings_doc['value']
            # Wenn es ein String ist, splitte ihn an Kommas
            if isinstance(value, str):
                return [loc.strip() for loc in value.split(',') if loc.strip()]
            # Wenn es bereits eine Liste ist, verwende sie direkt
            elif isinstance(value, list):
                return value
        return []
        
        # Fallback: Verwende die ursprüngliche locations Collection
        locations = mongodb.find('locations', {'deleted': {'$ne': True}})
        return [loc['name'] for loc in locations if 'name' in loc]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Standorte: {e}")
        return []

def get_departments_from_settings():
    """Lädt Abteilungen aus der settings Collection oder der departments Collection"""
    try:
        # Versuche zuerst die settings Collection
        settings_doc = mongodb.find_one('settings', {'key': 'departments'})
        if settings_doc and 'value' in settings_doc:
            value = settings_doc['value']
            # Wenn es ein String ist, splitte ihn an Kommas
            if isinstance(value, str):
                return [dept.strip() for dept in value.split(',') if dept.strip()]
            # Wenn es bereits eine Liste ist, verwende sie direkt
            elif isinstance(value, list):
                return value
        return []
        
        # Fallback: Verwende die ursprüngliche departments Collection
        departments = mongodb.find('departments', {'deleted': {'$ne': True}})
        return [dept['name'] for dept in departments if 'name' in dept]
    except Exception as e:
        logger.error(f"Fehler beim Laden der Abteilungen: {e}")
        return []

def ensure_default_settings():
    """
    Stellt sicher, dass die settings Collection existiert, aber ohne Standardwerte.
    Die Werte werden ausschließlich über das Dashboard verwaltet.
    """
    try:
        # Prüfe und erstelle leere Kategorien-Collection
        if not mongodb.find_one('settings', {"key": "categories"}):
            mongodb.insert_one('settings', {
                "key": "categories",
                "value": []
            })
            logger.info("Kategorien-Collection initialisiert")
        
        # Prüfe und erstelle leere Standorte-Collection
        if not mongodb.find_one('settings', {"key": "locations"}):
            mongodb.insert_one('settings', {
                "key": "locations",
                "value": []
            })
            logger.info("Standorte-Collection initialisiert")
        
        # Prüfe und erstelle leere Abteilungen-Collection
        if not mongodb.find_one('settings', {"key": "departments"}):
            mongodb.insert_one('settings', {
                "key": "departments",
                "value": []
            })
            logger.info("Abteilungen-Collection initialisiert")
        
        # Prüfe und erstelle leere Ticket-Kategorien-Collection
        if not mongodb.find_one('settings', {"key": "ticket_categories"}):
            mongodb.insert_one('settings', {
                "key": "ticket_categories",
                "value": []
            })
            logger.info("Ticket-Kategorien-Collection initialisiert")
            
    except Exception as e:
        logger.error(f"Fehler beim Initialisieren der Settings Collections: {e}")
        raise

def validate_reference_data():
    """Validiert und gibt Referenzdaten zurück"""
    try:
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        departments = get_departments_from_settings()
        
        return {
            'categories': categories,
            'locations': locations,
            'departments': departments
        }
    except Exception as e:
        logger.error(f"Fehler bei der Validierung der Referenzdaten: {e}")
        return {
            'categories': [],
            'locations': [],
            'departments': []
        }

def migrate_old_data_to_settings():
    """Migriert alte Daten zu settings Collection (falls vorhanden)"""
    try:
        # Prüfe ob alte Collections existieren und migriere sie
        old_categories = mongodb.find('categories', {})
        old_locations = mongodb.find('locations', {})
        old_departments = mongodb.find('departments', {})
        old_ticket_categories = mongodb.find('ticket_categories', {})
        
        # Migriere Kategorien
        if old_categories:
            categories_data = []
            for cat in old_categories:
                if 'name' in cat:
                    categories_data.append(cat['name'])
            
            if categories_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'categories'},
                    {'$set': {'value': categories_data}},
                    upsert=True
                )
        
        # Migriere Standorte
        if old_locations:
            locations_data = []
            for loc in old_locations:
                if 'name' in loc:
                    locations_data.append(loc['name'])
            
            if locations_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'locations'},
                    {'$set': {'value': locations_data}},
                    upsert=True
                )
        
        # Migriere Abteilungen
        if old_departments:
            departments_data = []
            for dept in old_departments:
                if 'name' in dept:
                    departments_data.append(dept['name'])
            
            if departments_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'departments'},
                    {'$set': {'value': departments_data}},
                    upsert=True
                )
        
        # Migriere Ticket-Kategorien
        if old_ticket_categories:
            ticket_categories_data = []
            for cat in old_ticket_categories:
                if 'name' in cat:
                    ticket_categories_data.append(cat['name'])
            
            if ticket_categories_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'ticket_categories'},
                    {'$set': {'value': ticket_categories_data}},
                    upsert=True
                )
                
        logger.info("Migration der alten Daten abgeschlossen")
        
    except Exception as e:
        logger.error(f"Fehler bei der Migration der alten Daten: {e}")
        raise

def get_next_ticket_number():
    """Generiert die nächste Auftragsnummer im Format YYMM-XXX"""
    current_date = datetime.now()
    year_suffix = str(current_date.year)[-2:]  # Letzte 2 Ziffern des Jahres
    month = f"{current_date.month:02d}"  # Monat mit führender Null
    
    # Basis für die Nummer (z.B. "2506")
    base_number = f"{year_suffix}{month}"
    
    # Finde die höchste Nummer für diesen Monat
    existing_tickets = mongodb.find('tickets', {
        'ticket_number': {'$regex': f'^{base_number}-[0-9]+$'}
    })
    
    max_number = 0
    for ticket in existing_tickets:
        if ticket.get('ticket_number'):
            try:
                # Extrahiere die Nummer nach dem Bindestrich
                number_part = ticket['ticket_number'].split('-')[1]
                ticket_num = int(number_part)
                max_number = max(max_number, ticket_num)
            except (ValueError, IndexError):
                continue
    
    # Nächste Nummer
    next_number = max_number + 1
    
    return f"{base_number}-{next_number:03d}" 