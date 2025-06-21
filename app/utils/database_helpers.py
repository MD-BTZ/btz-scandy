"""
Datenbank-Hilfsfunktionen für Scandy
"""

from app.models.mongodb_database import mongodb
import logging

logger = logging.getLogger(__name__)

def get_categories_from_settings():
    """Lädt Kategorien aus der settings Collection"""
    try:
        settings_doc = mongodb.find_one('settings', {'key': 'categories'})
        if settings_doc and 'value' in settings_doc:
            return settings_doc['value']
        return []
    except Exception as e:
        logger.error(f"Fehler beim Laden der Kategorien: {e}")
        return []

def get_locations_from_settings():
    """Lädt Standorte aus der settings Collection"""
    try:
        settings_doc = mongodb.find_one('settings', {'key': 'locations'})
        if settings_doc and 'value' in settings_doc:
            return settings_doc['value']
        return []
    except Exception as e:
        logger.error(f"Fehler beim Laden der Standorte: {e}")
        return []

def get_departments_from_settings():
    """Lädt Abteilungen aus der settings Collection"""
    try:
        settings_doc = mongodb.find_one('settings', {'key': 'departments'})
        if settings_doc and 'value' in settings_doc:
            return settings_doc['value']
        return []
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
                
    except Exception as e:
        logger.error(f"Fehler bei der Datenmigration: {e}") 