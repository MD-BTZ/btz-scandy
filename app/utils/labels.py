from typing import Dict
from app.models.database import Database
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def inject_app_labels(app_labels: Dict[str, Dict[str, str]]) -> None:
    """Fügt die Labels in die Datenbank ein"""
    try:
        for key, value in app_labels.items():
            # Speichere den Namen
            Database.set_setting(f'label_{key}', value['name'])
            
            # Speichere das Icon
            if 'icon' in value:
                Database.set_setting(f'label_{key}_icon', value['icon'])
            
            # Speichere die Beschreibung
            if 'description' in value:
                Database.set_setting(f'label_{key}_description', value['description'])
    except Exception as e:
        logger.error(f"Fehler beim Einfügen der Labels: {e}")

def get_app_labels():
    """Holt die Anwendungs-Labels und Icons aus der Datenbank"""
    try:
        # Hole die Labels direkt aus der Datenbank
        tools_name = Database.query('''
            SELECT value FROM settings 
            WHERE key = 'label_tools_name'
        ''', one=True)
        
        tools_icon = Database.query('''
            SELECT value FROM settings 
            WHERE key = 'label_tools_icon'
        ''', one=True)
        
        consumables_name = Database.query('''
            SELECT value FROM settings 
            WHERE key = 'label_consumables_name'
        ''', one=True)
        
        consumables_icon = Database.query('''
            SELECT value FROM settings 
            WHERE key = 'label_consumables_icon'
        ''', one=True)
        
        custom_logo = Database.query('''
            SELECT value FROM settings 
            WHERE key = 'custom_logo'
        ''', one=True)
        
        return {
            'tools': {
                'name': tools_name['value'] if tools_name else 'Werkzeuge',
                'icon': tools_icon['value'] if tools_icon else 'fas fa-tools'
            },
            'consumables': {
                'name': consumables_name['value'] if consumables_name else 'Verbrauchsmaterial',
                'icon': consumables_icon['value'] if consumables_icon else 'fas fa-box-open'
            },
            'custom_logo': custom_logo['value'] if custom_logo else None
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden der Labels: {e}")
        return {
            'tools': {'name': 'Werkzeuge', 'icon': 'fas fa-tools'},
            'consumables': {'name': 'Verbrauchsmaterial', 'icon': 'fas fa-box-open'},
            'custom_logo': None
        } 