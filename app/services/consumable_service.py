"""
Zentraler Consumable Service für Scandy
Alle Verbrauchsmaterial-Funktionen an einem Ort
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from app.models.mongodb_database import mongodb
from app.utils.database_helpers import get_categories_from_settings, get_locations_from_settings
import logging

logger = logging.getLogger(__name__)

class ConsumableService:
    """Zentraler Service für alle Verbrauchsmaterial-Operationen"""
    
    @staticmethod
    def get_all_consumables() -> List[Dict[str, Any]]:
        try:
            return list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterialien: {str(e)}")
            return []
    
    @staticmethod
    def add_consumable(data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            barcode = data.get('barcode')
            # Prüfe auf Barcode-Duplikate
            for collection in ['tools', 'consumables', 'workers']:
                if mongodb.find_one(collection, {'barcode': barcode, 'deleted': {'$ne': True}}):
                    return False, 'Barcode bereits vergeben'
            
            consumable_data = {
                'name': data.get('name'),
                'barcode': barcode,
                'category': data.get('category'),
                'location': data.get('location'),
                'quantity': int(data.get('quantity', 0)),
                'min_quantity': int(data.get('min_quantity', 0)),
                'description': data.get('description', ''),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'deleted': False
            }
            mongodb.insert_one('consumables', consumable_data)
            return True, 'Verbrauchsmaterial wurde erfolgreich hinzugefügt'
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Verbrauchsmaterials: {str(e)}")
            return False, 'Fehler beim Hinzufügen des Verbrauchsmaterials'
    
    @staticmethod
    def update_consumable(barcode: str, data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        try:
            new_barcode = data.get('barcode')
            current = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
            if not current:
                return False, 'Verbrauchsmaterial nicht gefunden', None
            if new_barcode != barcode:
                for collection in ['tools', 'consumables', 'workers']:
                    if mongodb.find_one(collection, {'barcode': new_barcode, 'deleted': {'$ne': True}}):
                        return False, f'Der Barcode "{new_barcode}" existiert bereits', None
            update_data = {
                'name': data.get('name'),
                'description': data.get('description'),
                'category': data.get('category'),
                'location': data.get('location'),
                'quantity': int(data.get('quantity', current['quantity'])),
                'min_quantity': int(data.get('min_quantity', current['min_quantity'])),
                'barcode': new_barcode,
                'updated_at': datetime.now()
            }
            mongodb.update_one('consumables', {'barcode': barcode}, {'$set': update_data})
            # Bestandsänderung protokollieren
            if int(data.get('quantity', current['quantity'])) != current['quantity']:
                usage_data = {
                    'consumable_barcode': new_barcode,
                    'worker_barcode': 'admin',
                    'quantity': int(data.get('quantity', current['quantity'])) - current['quantity'],
                    'used_at': datetime.now()
                }
                mongodb.insert_one('consumable_usages', usage_data)
            return True, 'Verbrauchsmaterial erfolgreich aktualisiert', new_barcode
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Verbrauchsmaterials: {str(e)}")
            return False, str(e), None
    
    @staticmethod
    def get_consumable_detail(barcode: str) -> Optional[Dict[str, Any]]:
        try:
            return mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        except Exception as e:
            logger.error(f"Fehler beim Laden des Verbrauchsmaterials: {str(e)}")
            return None
    
    @staticmethod
    def get_consumable_usages(barcode: str) -> List[Dict[str, Any]]:
        try:
            usages = list(mongodb.find('consumable_usages', {'consumable_barcode': barcode}))
            # Sortiere nach Datum (neueste zuerst)
            def safe_date_key(usage):
                used_at = usage.get('used_at')
                if isinstance(used_at, str):
                    try:
                        return datetime.strptime(used_at, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        return datetime.min
                elif isinstance(used_at, datetime):
                    return used_at
                else:
                    return datetime.min
            usages.sort(key=safe_date_key, reverse=True)
            return usages
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchshistorie: {str(e)}")
            return []
    
    @staticmethod
    def delete_consumable(barcode: str) -> Tuple[bool, str]:
        try:
            result = mongodb.update_one('consumables', {'barcode': barcode}, {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
            if result:
                return True, 'Verbrauchsmaterial erfolgreich gelöscht'
            else:
                return False, 'Fehler beim Löschen'
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {str(e)}")
            return False, 'Fehler beim Löschen' 