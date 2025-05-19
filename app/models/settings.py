from app.models.database import Database
from typing import Optional, List, Dict, Any
import logging
from flask import current_app

logger = logging.getLogger(__name__)

class Settings:
    """Klasse zur Verwaltung von Einstellungen"""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Holt einen Einstellungswert"""
        try:
            result = Database.query(
                "SELECT value FROM settings WHERE key = ?",
                [key],
                one=True
            )
            return result['value'] if result else default
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Einstellung {key}: {e}")
            return default

    @staticmethod
    def set(key: str, value: Any) -> bool:
        """Setzt einen Einstellungswert"""
        try:
            return Database.set_setting(key, value)
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Einstellung {key}: {e}")
            return False

    @staticmethod
    def get_all() -> Dict[str, Any]:
        """Holt alle Einstellungen"""
        try:
            settings = Database.query("SELECT key, value FROM settings")
            return {row['key']: row['value'] for row in settings}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen aller Einstellungen: {e}")
            return {}

    @staticmethod
    def get_departments() -> List[str]:
        """Holt alle Abteilungen"""
        try:
            departments = Database.query(
                """
                SELECT value 
                FROM settings 
                WHERE key LIKE 'department_%'
                AND value IS NOT NULL 
                AND value != ''
                ORDER BY value
                """
            )
            return [dept['value'] for dept in departments]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Abteilungen: {e}")
            return []

    @staticmethod
    def add_department(name: str) -> bool:
        """Fügt eine neue Abteilung hinzu"""
        try:
            # Nächste freie ID finden
            result = Database.query(
                """
                SELECT MAX(CAST(SUBSTR(key, 12) AS INTEGER)) as max_id 
                FROM settings 
                WHERE key LIKE 'department_%'
                """,
                one=True
            )
            next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
            
            # Neue Abteilung einfügen
            return Settings.set(f'department_{next_id}', name)
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Abteilung {name}: {e}")
            return False

    @staticmethod
    def delete_department(name: str) -> bool:
        """Löscht eine Abteilung"""
        try:
            Database.query(
                "DELETE FROM settings WHERE key LIKE 'department_%' AND value = ?",
                [name]
            )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Abteilung {name}: {e}")
            return False

    @staticmethod
    def get_locations() -> List[Dict[str, str]]:
        """Holt alle Standorte mit ihrer Verwendung"""
        try:
            locations = Database.query(
                """
                SELECT value as name, description as usage
                FROM settings
                WHERE key LIKE 'location_%'
                AND value IS NOT NULL
                AND value != ''
                ORDER BY value
                """
            )
            return [dict(loc) for loc in locations]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Standorte: {e}")
            return []

    @staticmethod
    def add_location(name: str, usage: str = 'both') -> bool:
        """Fügt einen neuen Standort hinzu"""
        try:
            # Nächste freie ID finden
            result = Database.query(
                """
                SELECT MAX(CAST(SUBSTR(key, 10) AS INTEGER)) as max_id 
                FROM settings 
                WHERE key LIKE 'location_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                """,
                one=True
            )
            next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
            
            # Neuen Standort einfügen
            return Settings.set(f'location_{next_id}', name, description=usage)
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Standorts {name}: {e}")
            return False

    @staticmethod
    def delete_location(name: str) -> bool:
        """Löscht einen Standort"""
        try:
            Database.query(
                "DELETE FROM settings WHERE key LIKE 'location_%' AND value = ?",
                [name]
            )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Standorts {name}: {e}")
            return False

    @staticmethod
    def get_categories() -> List[Dict[str, str]]:
        """Holt alle Kategorien mit ihrer Verwendung"""
        try:
            categories = Database.query(
                """
                SELECT value as name, description as usage
                FROM settings
                WHERE key LIKE 'category_%'
                AND value IS NOT NULL
                AND value != ''
                ORDER BY value
                """
            )
            return [dict(cat) for cat in categories]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Kategorien: {e}")
            return []

    @staticmethod
    def add_category(name: str, usage: str = 'both') -> bool:
        """Fügt eine neue Kategorie hinzu"""
        try:
            # Nächste freie ID finden
            result = Database.query(
                """
                SELECT MAX(CAST(SUBSTR(key, 10) AS INTEGER)) as max_id 
                FROM settings 
                WHERE key LIKE 'category_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                """,
                one=True
            )
            next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
            
            # Neue Kategorie einfügen
            return Settings.set(f'category_{next_id}', name, description=usage)
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Kategorie {name}: {e}")
            return False

    @staticmethod
    def delete_category(name: str) -> bool:
        """Löscht eine Kategorie"""
        try:
            Database.query(
                "DELETE FROM settings WHERE key LIKE 'category_%' AND value = ?",
                [name]
            )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Kategorie {name}: {e}")
            return False

    @staticmethod
    def update_category_usage(name: str, usage: str) -> bool:
        """Aktualisiert die Verwendung einer Kategorie"""
        try:
            category_key = Database.query(
                """
                SELECT key FROM settings 
                WHERE key LIKE 'category_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                AND value = ?
                """,
                [name],
                one=True
            )
            
            if not category_key:
                return False
                
            base_key = category_key['key']
            
            # Aktualisiere die Kategorie und ihre Eigenschaften
            Database.query(
                """
                UPDATE settings 
                SET description = ?,
                    updated_at = datetime('now')
                WHERE key = ?
                """,
                [usage, base_key]
            )
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Kategorie {name}: {e}")
            return False

    @staticmethod
    def update_location_usage(name: str, usage: str) -> bool:
        """Aktualisiert die Verwendung eines Standorts"""
        try:
            location_key = Database.query(
                """
                SELECT key FROM settings 
                WHERE key LIKE 'location_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                AND value = ?
                """,
                [name],
                one=True
            )
            
            if not location_key:
                return False
                
            base_key = location_key['key']
            
            # Aktualisiere den Standort und seine Eigenschaften
            Database.query(
                """
                UPDATE settings 
                SET description = ?,
                    updated_at = datetime('now')
                WHERE key = ?
                """,
                [usage, base_key]
            )
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Standorts {name}: {e}")
            return False 