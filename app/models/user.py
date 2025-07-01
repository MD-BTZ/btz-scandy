"""
User-Modell für Flask-Login Integration mit MongoDB
"""
from flask_login import UserMixin

class User(UserMixin):
    """User-Klasse für Flask-Login Integration"""
    
    def __init__(self, user_data=None):
        if user_data:
            # Verwende normale Attribut-Zuweisung
            self.id = str(user_data.get('_id'))
            self.username = user_data.get('username')
            self.role = user_data.get('role', 'anwender')
            self.is_admin = user_data.get('role', 'anwender') == 'admin'
            self.is_mitarbeiter = user_data.get('role', 'anwender') in ['admin', 'mitarbeiter']
            # Speichere is_active als normales Attribut
            self._active = user_data.get('is_active', True)
            
            # Wochenbericht-Feature: Prüfe ob Feld existiert, sonst setze Standard
            if 'timesheet_enabled' in user_data:
                # Feld existiert - verwende den gespeicherten Wert
                self.timesheet_enabled = user_data.get('timesheet_enabled', False)
            else:
                # Feld existiert nicht - setze Standard basierend auf Rolle
                if user_data.get('role') == 'anwender':
                    self.timesheet_enabled = True  # Anwender standardmäßig aktiviert
                else:
                    self.timesheet_enabled = False  # Andere Rollen standardmäßig deaktiviert
                
                # Speichere das Feld automatisch in der Datenbank
                self._save_timesheet_enabled(user_data['_id'], self.timesheet_enabled)
        else:
            self.id = None
            self.username = None
            self.role = 'anwender'
            self.is_admin = False
            self.is_mitarbeiter = False
            self._active = True
            self.timesheet_enabled = False
    
    def get_id(self):
        return str(self.id)
    
    def is_authenticated(self):
        return True
    
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        return getattr(self, '_active', True)
    
    def _save_timesheet_enabled(self, user_id, timesheet_enabled):
        """Speichert das timesheet_enabled Feld automatisch in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            from bson import ObjectId
            
            mongodb.update_one('users', 
                             {'_id': ObjectId(user_id)}, 
                             {'$set': {'timesheet_enabled': timesheet_enabled}})
        except Exception as e:
            # Logge den Fehler, aber lass das System weiterlaufen
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Konnte timesheet_enabled nicht automatisch speichern für Benutzer {user_id}: {e}") 