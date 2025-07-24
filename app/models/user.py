"""
User-Modell für Flask-Login Integration mit MongoDB
"""
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin):
    """User-Klasse für Flask-Login Integration"""
    
    def __init__(self, user_data=None):
        if user_data:
            # Verwende normale Attribut-Zuweisung
            # WICHTIG: Speichere die ID immer als String für Konsistenz
            self.id = str(user_data.get('_id'))
            self.username = user_data.get('username')
            self.role = user_data.get('role', 'anwender')
            self.is_admin = user_data.get('role', 'anwender') == 'admin'
            self.is_mitarbeiter = user_data.get('role', 'anwender') in ['admin', 'mitarbeiter']
            self.is_teilnehmer = user_data.get('role', 'anwender') == 'teilnehmer'
            # Speichere is_active als normales Attribut
            self._active = user_data.get('is_active', True)
            
            # Ablaufdatum-Funktionalität
            self.expires_at = user_data.get('expires_at')
            if self.expires_at and isinstance(self.expires_at, str):
                try:
                    self.expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
                except:
                    self.expires_at = None
            
            # Wochenbericht-Feature: Prüfe ob Feld existiert, sonst setze Standard
            if 'timesheet_enabled' in user_data:
                # Feld existiert - verwende den gespeicherten Wert
                self.timesheet_enabled = user_data.get('timesheet_enabled', False)
            else:
                # Feld existiert nicht - setze Standard basierend auf Rolle
                if user_data.get('role') in ['anwender', 'teilnehmer']:
                    self.timesheet_enabled = True  # Anwender und Teilnehmer standardmäßig aktiviert
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
            self.is_teilnehmer = False
            self._active = True
            self.expires_at = None
            self.timesheet_enabled = False
    
    def get_id(self):
        return str(self.id)
    
    def is_authenticated(self):
        return True
    
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        # Prüfe Ablaufdatum
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return self._active
    
    @property
    def is_expired(self):
        """Prüft ob der Account abgelaufen ist"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def days_until_expiry(self):
        """Gibt die Anzahl der Tage bis zum Ablauf zurück"""
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now()
        return delta.days
    
    def _save_timesheet_enabled(self, user_id, enabled):
        """Speichert das timesheet_enabled Feld in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            mongodb.db.users.update_one(
                {'_id': user_id},
                {'$set': {'timesheet_enabled': enabled}}
            )
        except Exception as e:
            # Logge den Fehler, aber falle nicht aus
            import logging
            logging.error(f"Fehler beim Speichern von timesheet_enabled für User {user_id}: {e}") 