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
            colors[key] = doc['value']
        return colors
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Farben: {str(e)}")
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
        print("\n=== Color Injection Debug ===")
        color_docs = mongodb.find('settings', {'key': {'$regex': '^color_'}})
        print(f"MongoDB Query: settings, key ^color_")
        print(f"Raw colors from DB:", color_docs)
        if color_docs:
            color_dict = {}
            for doc in color_docs:
                key = doc['key'].replace('color_', '')
                value = doc['value']
                color_dict[key] = value
                print(f"Loaded color: {key} = {value}")
            print("Final color dict:", color_dict)
            print("========================\n")
            return {'colors': color_dict}
    except Exception as e:
        print(f"Fehler beim Laden der Farben: {e}")
        print(traceback.format_exc())
    print("Using fallback colors")
    print("========================\n")
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
        label_dict = {}
        for doc in label_docs:
            key = doc['key'].replace('label_', '')
            value = doc['value']
            label_dict[key] = value
        return {'app_labels': label_dict}
    except Exception as e:
        print(f"Fehler beim Laden der App-Labels: {str(e)}")
        return {'app_labels': {}}

def register_context_processors(app):
    """Registriert alle Context Processors"""
    app.context_processor(inject_colors)
    app.context_processor(inject_routes)
    app.context_processor(inject_version)
    app.context_processor(inject_app_labels)