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
                'handlungsfelder': user_data.get('handlungsfelder', []),

                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Benutzer in Datenbank speichern
            user_id = mongodb.insert_one('users', new_user)
            
            logger.info(f"Neuer Benutzer erstellt: {user_data['username']} (ID: {user_id})")
            
            # Automatisch Mitarbeiter-Eintrag erstellen
            worker_created = AdminUserService._create_worker_from_user(new_user, user_id)
            if worker_created:
                logger.info(f"Automatischer Mitarbeiter-Eintrag erstellt für: {user_data['username']}")
            
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
                              'email', 'firstname', 'lastname', 'handlungsfelder']
            
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
            
            # Synchronisiere Mitarbeiter-Eintrag falls vorhanden
            AdminUserService._sync_worker_from_user(user_id, update_data)
            
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
            
            # Deaktiviere auch den zugehörigen Mitarbeiter-Eintrag
            AdminUserService._deactivate_worker_from_user(user_id)
            
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
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'role_stats': role_stats
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Benutzer-Statistiken: {str(e)}")
            return {
                'total_users': 0,
                'active_users': 0,
                'role_stats': [],
                'scheduled_for_deletion': 0,
                'scheduled_users': []
            }
    
    @staticmethod
    def _create_worker_from_user(user_data: Dict[str, Any], user_id: str) -> bool:
        """
        Erstellt automatisch einen Mitarbeiter-Eintrag aus Benutzerdaten
        
        Args:
            user_data: Benutzerdaten
            user_id: ID des erstellten Benutzers
            
        Returns:
            True wenn erfolgreich erstellt, False sonst
        """
        try:
            # Prüfe ob bereits ein Mitarbeiter mit diesem Benutzernamen existiert
            existing_worker = mongodb.find_one('workers', {
                'username': user_data['username'],
                'deleted': {'$ne': True}
            })
            
            if existing_worker:
                logger.info(f"Mitarbeiter-Eintrag existiert bereits für: {user_data['username']}")
                return True
            
            # Generiere einen eindeutigen Barcode basierend auf dem Benutzernamen
            barcode = f"USER_{user_data['username'].upper()}"
            
            # Prüfe ob der Barcode bereits existiert
            existing_barcode = mongodb.find_one('workers', {
                'barcode': barcode,
                'deleted': {'$ne': True}
            })
            
            if existing_barcode:
                # Falls Barcode existiert, füge eine Nummer hinzu
                counter = 1
                while True:
                    new_barcode = f"{barcode}_{counter}"
                    existing = mongodb.find_one('workers', {
                        'barcode': new_barcode,
                        'deleted': {'$ne': True}
                    })
                    if not existing:
                        barcode = new_barcode
                        break
                    counter += 1
            
            # Erstelle Mitarbeiter-Daten
            worker_data = {
                'barcode': barcode,
                'username': user_data['username'],  # Verknüpfung zum Benutzer
                'user_id': user_id,  # Verknüpfung zur Benutzer-ID
                'firstname': user_data.get('firstname', ''),
                'lastname': user_data.get('lastname', ''),
                'department': user_data.get('department', ''),
                'email': user_data.get('email', ''),
                'role': user_data.get('role', 'anwender'),
                'created_at': datetime.now(),
                'modified_at': datetime.now(),
                'deleted': False
            }
            
            # Mitarbeiter in Datenbank speichern
            mongodb.insert_one('workers', worker_data)
            
            logger.info(f"Automatischer Mitarbeiter-Eintrag erstellt: {barcode} für Benutzer {user_data['username']}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des automatischen Mitarbeiter-Eintrags: {str(e)}")
            return False
    
    @staticmethod
    def _sync_worker_from_user(user_id: str, user_update_data: Dict[str, Any]) -> bool:
        """
        Synchronisiert einen bestehenden Mitarbeiter-Eintrag mit Benutzerdaten
        
        Args:
            user_id: ID des Benutzers
            user_update_data: Aktualisierte Benutzerdaten
            
        Returns:
            True wenn erfolgreich synchronisiert, False sonst
        """
        try:
            # Finde den zugehörigen Mitarbeiter-Eintrag
            worker = mongodb.find_one('workers', {
                'user_id': user_id,
                'deleted': {'$ne': True}
            })
            
            if not worker:
                logger.info(f"Kein Mitarbeiter-Eintrag gefunden für Benutzer-ID: {user_id}")
                return False
            
            # Bereite Update-Daten vor
            worker_update_data = {
                'modified_at': datetime.now()
            }
            
            # Synchronisiere relevante Felder
            if 'firstname' in user_update_data:
                worker_update_data['firstname'] = user_update_data['firstname']
            if 'lastname' in user_update_data:
                worker_update_data['lastname'] = user_update_data['lastname']
            if 'email' in user_update_data:
                worker_update_data['email'] = user_update_data['email']
            if 'department' in user_update_data:
                worker_update_data['department'] = user_update_data['department']
            
            # Aktualisiere Mitarbeiter-Eintrag
            mongodb.update_one('workers', 
                             {'user_id': user_id}, 
                             {'$set': worker_update_data})
            
            logger.info(f"Mitarbeiter-Eintrag synchronisiert für Benutzer-ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Synchronisieren des Mitarbeiter-Eintrags: {str(e)}")
            return False
    
    @staticmethod
    def _deactivate_worker_from_user(user_id: str) -> bool:
        """
        Deaktiviert den zugehörigen Mitarbeiter-Eintrag
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            True wenn erfolgreich deaktiviert, False sonst
        """
        try:
            # Finde den zugehörigen Mitarbeiter-Eintrag
            worker = mongodb.find_one('workers', {
                'user_id': user_id,
                'deleted': {'$ne': True}
            })
            
            if not worker:
                logger.info(f"Kein Mitarbeiter-Eintrag gefunden für Benutzer-ID: {user_id}")
                return False
            
            # Deaktiviere den Mitarbeiter-Eintrag (Soft Delete)
            mongodb.update_one('workers', 
                             {'user_id': user_id}, 
                             {'$set': {
                                 'deleted': True,
                                 'deleted_at': datetime.now(),
                                 'modified_at': datetime.now()
                             }})
            
            logger.info(f"Mitarbeiter-Eintrag deaktiviert für Benutzer-ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Deaktivieren des Mitarbeiter-Eintrags: {str(e)}")
            return False
    

    
