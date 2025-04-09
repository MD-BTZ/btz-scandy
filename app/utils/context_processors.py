from flask import current_app
from app.models.database import Database
from app.utils.routes import Routes
import traceback

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

def register_context_processors(app):
    """Registriert alle Context Processors"""
    app.context_processor(inject_colors)
    app.context_processor(inject_routes)