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
        else:
            self.id = None
            self.username = None
            self.role = 'anwender'
            self.is_admin = False
            self.is_mitarbeiter = False
            self._active = True
    
    def get_id(self):
        return str(self.id)
    
    def is_authenticated(self):
        return True
    
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        return getattr(self, '_active', True) 