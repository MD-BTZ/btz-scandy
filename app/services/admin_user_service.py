"""
Admin User Service

Dieser Service enthält alle Funktionen für die Benutzerverwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.mongodb_database import mongodb
from app.utils.id_helpers import find_user_by_id
import random
import string

logger = logging.getLogger(__name__)

class AdminUserService:
    """Service für Admin-Benutzerverwaltungs-Funktionen"""
    
    @staticmethod
    def get_all_users() -> List[Dict[str, Any]]:
        """Hole alle Benutzer"""
        try:
            users = list(mongodb.find('users', {}))
            
            # Konvertiere ObjectIds zu Strings für JSON-Serialisierung
            for user in users:
                if '_id' in user:
                    user['_id'] = str(user['_id'])
            
            return users
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aller Benutzer: {str(e)}")
            return []

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Hole einen Benutzer anhand der ID"""
        try:
            user = find_user_by_id(user_id)
            if user and '_id' in user:
                user['_id'] = str(user['_id'])
            return user
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Benutzers {user_id}: {str(e)}")
            return None

    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt einen neuen Benutzer
        
        Args:
            user_data: Benutzerdaten
            
        Returns:
            (success, message, user_id)
        """
        try:
            # Validierung
            required_fields = ['username', 'role']
            for field in required_fields:
                if field not in user_data or not user_data[field]:
                    return False, f"Feld '{field}' ist erforderlich", None
            
            # Prüfe ob Benutzername bereits existiert
            existing_user = mongodb.find_one('users', {'username': user_data['username']})
            if existing_user:
                return False, "Benutzername existiert bereits", None
            
            # Passwort generieren falls nicht angegeben
            password = user_data.get('password', '')
            if not password:
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                logger.info(f"Automatisches Passwort generiert für {user_data['username']}")
            
            # Passwort hashen
            password_hash = generate_password_hash(password)
            
            # Benutzer erstellen
            new_user = {
                'username': user_data['username'],
                'password_hash': password_hash,
                'role': user_data['role'],
                'is_active': user_data.get('is_active', True),
                'timesheet_enabled': user_data.get('timesheet_enabled', False),
                'email': user_data.get('email', ''),
                'firstname': user_data.get('firstname', ''),
                'lastname': user_data.get('lastname', ''),
                'department': user_data.get('department', ''),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Benutzer in Datenbank speichern
            user_id = mongodb.insert_one('users', new_user)
            
            logger.info(f"Neuer Benutzer erstellt: {user_data['username']} (ID: {user_id})")
            
            # Passwort in der Nachricht zurückgeben falls generiert
            if not user_data.get('password'):
                return True, f"Benutzer '{user_data['username']}' erfolgreich erstellt. Generiertes Passwort: {password}", user_id
            else:
                return True, f"Benutzer '{user_data['username']}' erfolgreich erstellt", user_id
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Benutzers: {str(e)}")
            return False, f"Fehler beim Erstellen des Benutzers: {str(e)}", None

    @staticmethod
    def update_user(user_id: str, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert einen bestehenden Benutzer
        
        Args:
            user_id: ID des zu aktualisierenden Benutzers
            user_data: Neue Benutzerdaten
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benutzer existiert
            user = find_user_by_id(user_id)
            if not user:
                return False, "Benutzer nicht gefunden"
            
            # Update-Daten vorbereiten
            update_data = {
                'updated_at': datetime.now()
            }
            
            # Aktualisierbare Felder (ohne Abteilung)
            updatable_fields = ['username', 'role', 'is_active', 'timesheet_enabled', 
                              'email', 'firstname', 'lastname']
            
            for field in updatable_fields:
                if field in user_data:
                    update_data[field] = user_data[field]
            
            # Passwort aktualisieren falls angegeben
            if 'password' in user_data and user_data['password']:
                update_data['password_hash'] = generate_password_hash(user_data['password'])
            
            # Prüfe ob neuer Benutzername bereits existiert (außer bei diesem Benutzer)
            if 'username' in update_data:
                # Konvertiere user_id zu ObjectId für korrekte Datenbankabfrage
                from bson import ObjectId
                try:
                    object_id = ObjectId(user_id)
                except:
                    # Falls user_id bereits ein ObjectId ist oder ungültig
                    object_id = user_id
                
                existing_user = mongodb.find_one('users', {
                    'username': update_data['username'],
                    '_id': {'$ne': object_id}
                })
                if existing_user:
                    return False, "Benutzername existiert bereits"
            
            # Benutzer aktualisieren
            mongodb.update_one('users', {'_id': user_id}, {'$set': update_data})
            
            logger.info(f"Benutzer aktualisiert: {user.get('username', 'Unknown')} (ID: {user_id})")
            return True, f"Benutzer erfolgreich aktualisiert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Benutzers {user_id}: {str(e)}")
            return False, f"Fehler beim Aktualisieren des Benutzers: {str(e)}"

    @staticmethod
    def delete_user(user_id: str) -> Tuple[bool, str]:
        """
        Löscht einen Benutzer
        
        Args:
            user_id: ID des zu löschenden Benutzers
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benutzer existiert
            user = find_user_by_id(user_id)
            if not user:
                return False, "Benutzer nicht gefunden"
            
            # Prüfe ob es der letzte Admin ist
            if user.get('role') == 'admin':
                admin_count = mongodb.count_documents('users', {'role': 'admin', 'is_active': True})
                if admin_count <= 1:
                    return False, "Der letzte Admin kann nicht gelöscht werden"
            
            # Benutzer löschen
            mongodb.delete_one('users', {'_id': user_id})
            
            logger.info(f"Benutzer gelöscht: {user.get('username', 'Unknown')} (ID: {user_id})")
            return True, f"Benutzer '{user.get('username', 'Unknown')}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Benutzers {user_id}: {str(e)}")
            return False, f"Fehler beim Löschen des Benutzers: {str(e)}"

    @staticmethod
    def reset_user_password(user_id: str, new_password: str) -> Tuple[bool, str]:
        """
        Setzt das Passwort eines Benutzers zurück
        
        Args:
            user_id: ID des Benutzers
            new_password: Neues Passwort
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benutzer existiert
            user = find_user_by_id(user_id)
            if not user:
                return False, "Benutzer nicht gefunden"
            
            # Passwort hashen
            password_hash = generate_password_hash(new_password)
            
            # Passwort aktualisieren
            mongodb.update_one('users', {'_id': user_id}, {
                '$set': {
                    'password_hash': password_hash,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Passwort zurückgesetzt für Benutzer: {user.get('username', 'Unknown')} (ID: {user_id})")
            return True, f"Passwort für '{user.get('username', 'Unknown')}' erfolgreich zurückgesetzt"
            
        except Exception as e:
            logger.error(f"Fehler beim Zurücksetzen des Passworts für Benutzer {user_id}: {str(e)}")
            return False, f"Fehler beim Zurücksetzen des Passworts: {str(e)}"

    @staticmethod
    def get_user_statistics() -> Dict[str, Any]:
        """Hole Benutzer-Statistiken"""
        try:
            # Gesamtanzahl Benutzer
            total_users = mongodb.count_documents('users', {})
            
            # Benutzer nach Rollen
            role_stats = {}
            roles = ['admin', 'mitarbeiter', 'teilnehmer', 'anwender']
            
            for role in roles:
                count = mongodb.count_documents('users', {'role': role})
                role_stats[role] = count
            
            # Aktive vs. inaktive Benutzer
            active_users = mongodb.count_documents('users', {'is_active': True})
            inactive_users = mongodb.count_documents('users', {'is_active': False})
            
            # Benutzer mit aktiviertem Wochenbericht
            timesheet_enabled = mongodb.count_documents('users', {'timesheet_enabled': True})
            
            return {
                'total_users': total_users,
                'role_stats': role_stats,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'timesheet_enabled': timesheet_enabled
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benutzer-Statistiken: {str(e)}")
            return {
                'total_users': 0,
                'role_stats': {},
                'active_users': 0,
                'inactive_users': 0,
                'timesheet_enabled': 0
            } 