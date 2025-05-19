from flask import current_app, g
from app.models.database import Database
from app.constants import Routes
from app.config.version import VERSION
import traceback
import logging
from datetime import datetime, timedelta
from app.models.settings import Settings
from flask import url_for, session, current_app
import os

logger = logging.getLogger(__name__)

def get_colors():
    """Holt die Farbeinstellungen aus der Datenbank"""
    try:
        db = Database.get_db()
        cursor = db.cursor()
        cursor.execute('SELECT key, value FROM settings WHERE key LIKE "color_%"')
        colors = {}
        for row in cursor.fetchall():
            key = row['key'].replace('color_', '')
            colors[key] = row['value']
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
    """Injiziert die Farbeinstellungen aus der Datenbank in alle Templates"""
    try:
        print("\n=== Color Injection Debug ===")
        
        # Direkte DB-Abfrage mit Fehlerprüfung
        with Database.get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT key, value FROM settings WHERE key LIKE 'color_%'")
            colors = cursor.fetchall()
            
            print(f"SQL: SELECT key, value FROM settings WHERE key LIKE 'color_%'")
            print(f"Raw colors from DB:", colors)
            
            if colors:
                color_dict = {}
                for row in colors:
                    key = row['key'].replace('color_', '')
                    value = row['value']
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

def register_context_processors(app):
    """Registriert alle Context Processors für die App"""
    
    @app.context_processor
    def inject_now():
        """Inject current datetime into all templates"""
        return {'now': datetime.now()}
        
    @app.context_processor
    def inject_debug():
        """Inject debug flag into all templates"""
        return {'debug': app.debug}
        
    @app.context_processor
    def inject_app_settings():
        """Inject app settings into all templates"""
        try:
            server_mode = Settings.get('server_mode')
            return {
                'app_settings': {
                    'server_mode': server_mode == '1' if server_mode is not None else False
                }
            }
        except Exception as e:
            app.logger.error(f"Fehler beim Laden der App-Einstellungen: {e}")
            return {'app_settings': {'server_mode': False}}
            
    @app.context_processor
    def inject_links():
        """Inject all route links into templates"""
        return {
            'links': {
                'index': url_for('main.index'),
                'dashboard': url_for('dashboard.index'),
                'tools': url_for('tools.index'),
                'consumables': url_for('consumables.index'),
                'workers': url_for('workers.index'),
                'login': url_for('auth.login'),
                'logout': url_for('auth.logout')
            }
        }
    
    @app.context_processor
    def inject_manifest():
        """Inject manifest into templates for assets"""
        manifest_path = os.path.join(app.static_folder, 'manifest.json')
        try:
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    import json
                    return {'manifest': json.load(f)}
        except Exception as e:
            app.logger.error(f"Fehler beim Laden des Manifests: {e}")
        return {'manifest': {}}
        
    # Hinweis: Wir fügen keinen inject_app_labels Context Processor hier hinzu,
    # da dieser bereits in __init__.py als inject_system_names definiert ist