"""
Admin User Service

Dieser Service enthält alle Funktionen für die Benutzerverwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime, timedelta
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
                
                # Konvertiere expires_at zu String falls vorhanden
                if 'expires_at' in user and user['expires_at']:
                    if isinstance(user['expires_at'], datetime):
                        user['expires_at'] = user['expires_at'].isoformat()
            
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
                
                # Konvertiere expires_at zu String falls vorhanden
                if 'expires_at' in user and user['expires_at']:
                    if isinstance(user['expires_at'], datetime):
                        user['expires_at'] = user['expires_at'].isoformat()
                        
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
            
            # Ablaufdatum verarbeiten
            expires_at = None
            if user_data.get('expires_at'):
                try:
                    if isinstance(user_data['expires_at'], str):
                        expires_at = datetime.fromisoformat(user_data['expires_at'].replace('Z', '+00:00'))
                    else:
                        expires_at = user_data['expires_at']
                except Exception as e:
                    logger.warning(f"Ungültiges Ablaufdatum für {user_data['username']}: {e}")
            
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
                'expires_at': expires_at,
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
            
            # Ablaufdatum verarbeiten
            if 'expires_at' in user_data:
                expires_at = None
                if user_data['expires_at']:
                    try:
                        if isinstance(user_data['expires_at'], str):
                            expires_at = datetime.fromisoformat(user_data['expires_at'].replace('Z', '+00:00'))
                        else:
                            expires_at = user_data['expires_at']
                    except Exception as e:
                        logger.warning(f"Ungültiges Ablaufdatum für User {user_id}: {e}")
                update_data['expires_at'] = expires_at
            
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
        Löscht einen Benutzer (soft delete)
        
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
            
            # Admin-Benutzer können nicht gelöscht werden
            if user.get('role') == 'admin':
                return False, "Admin-Benutzer können nicht gelöscht werden"
            
            # Benutzer deaktivieren statt löschen
            mongodb.update_one('users', {'_id': user_id}, {
                '$set': {
                    'is_active': False,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Benutzer deaktiviert: {user.get('username', 'Unknown')} (ID: {user_id})")
            return True, f"Benutzer '{user.get('username', 'Unknown')}' erfolgreich deaktiviert"
            
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
            
            logger.info(f"Passwort zurückgesetzt für: {user.get('username', 'Unknown')} (ID: {user_id})")
            return True, f"Passwort für '{user.get('username', 'Unknown')}' erfolgreich zurückgesetzt"
            
        except Exception as e:
            logger.error(f"Fehler beim Zurücksetzen des Passworts für {user_id}: {str(e)}")
            return False, f"Fehler beim Zurücksetzen des Passworts: {str(e)}"

    @staticmethod
    def get_user_statistics() -> Dict[str, Any]:
        """Hole Benutzer-Statistiken"""
        try:
            # Gesamtanzahl Benutzer
            total_users = mongodb.count_documents('users', {})
            
            # Aktive Benutzer
            active_users = mongodb.count_documents('users', {'is_active': True})
            
            # Benutzer nach Rollen
            role_stats = list(mongodb.aggregate('users', [
                {'$group': {'_id': '$role', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]))
            
            # Abgelaufene Benutzer
            now = datetime.now()
            expired_users = mongodb.count_documents('users', {
                'expires_at': {'$exists': True, '$ne': None, '$lt': now}
            })
            
            # Benutzer die bald ablaufen (in den nächsten 30 Tagen)
            soon_expiring = mongodb.count_documents('users', {
                'expires_at': {
                    '$exists': True,
                    '$ne': None,
                    '$gt': now,
                    '$lt': now + timedelta(days=30)
                }
            })
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'role_stats': role_stats,
                'expired_users': expired_users,
                'soon_expiring': soon_expiring
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Benutzer-Statistiken: {str(e)}")
            return {
                'total_users': 0,
                'active_users': 0,
                'role_stats': [],
                'expired_users': 0,
                'soon_expiring': 0
            }

    @staticmethod
    def cleanup_expired_users() -> Tuple[int, str]:
        """
        Bereinigt abgelaufene Benutzerkonten
        
        Returns:
            (anzahl_gelöscht, message)
        """
        try:
            now = datetime.now()
            
            # Finde abgelaufene Benutzer
            expired_users = list(mongodb.find('users', {
                'expires_at': {
                    '$exists': True,
                    '$ne': None,
                    '$lt': now
                },
                'role': {'$ne': 'admin'}  # Admin-Accounts nicht löschen
            }))
            
            if not expired_users:
                return 0, "Keine abgelaufenen Benutzer gefunden"
            
            # Lösche abgelaufene Benutzer
            deleted_count = 0
            for user in expired_users:
                try:
                    mongodb.delete_one('users', {'_id': user['_id']})
                    deleted_count += 1
                    logger.info(f"Abgelaufener Benutzer gelöscht: {user.get('username', 'Unknown')} (ID: {user['_id']})")
                except Exception as e:
                    logger.error(f"Fehler beim Löschen des abgelaufenen Benutzers {user['_id']}: {e}")
            
            message = f"{deleted_count} abgelaufene Benutzerkonten wurden gelöscht"
            logger.info(message)
            return deleted_count, message
            
        except Exception as e:
            logger.error(f"Fehler bei der Bereinigung abgelaufener Benutzer: {str(e)}")
            return 0, f"Fehler bei der Bereinigung: {str(e)}" 