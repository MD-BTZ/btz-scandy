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
            
            # Benutzerdefinierte Felder hinzufügen, falls vorhanden
            if 'custom_fields' in data and data['custom_fields']:
                consumable_data['custom_fields'] = data['custom_fields']
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
            
            # Benutzerdefinierte Felder hinzufügen, falls vorhanden
            if 'custom_fields' in data and data['custom_fields']:
                update_data['custom_fields'] = data['custom_fields']
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
    
    @staticmethod
    def adjust_stock(barcode: str, quantity_change: int, reason: str) -> Tuple[bool, str]:
        """Passt den Bestand eines Verbrauchsmaterials an"""
        try:
            # Verbrauchsmaterial finden
            consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
            if not consumable:
                return False, 'Verbrauchsmaterial nicht gefunden'
            
            # Neuen Bestand berechnen
            current_quantity = consumable.get('quantity', 0)
            new_quantity = current_quantity + quantity_change
            
            # Negativen Bestand verhindern
            if new_quantity < 0:
                return False, f'Bestand kann nicht unter 0 fallen. Aktueller Bestand: {current_quantity}'
            
            # Bestand aktualisieren
            mongodb.update_one('consumables', 
                             {'barcode': barcode}, 
                             {'$set': {'quantity': new_quantity, 'updated_at': datetime.now()}})
            
            # Verwendung protokollieren
            usage_data = {
                'consumable_barcode': barcode,
                'worker_barcode': 'admin',  # TODO: Aktuellen Benutzer verwenden
                'quantity': quantity_change,  # Positiv für Hinzufügung, negativ für Entnahme
                'reason': reason,
                'used_at': datetime.now()
            }
            mongodb.insert_one('consumable_usages', usage_data)
            
            action = "hinzugefügt" if quantity_change > 0 else "entnommen"
            return True, f'{abs(quantity_change)} Stück {action}. Neuer Bestand: {new_quantity}'
            
        except Exception as e:
            logger.error(f"Fehler beim Anpassen des Bestands: {str(e)}")
            return False, f'Fehler beim Anpassen des Bestands: {str(e)}'
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """Holt Statistiken für Verbrauchsmaterialien"""
        try:
            all_consumables = ConsumableService.get_all_consumables()
            
            stats = {
                'total_consumables': len(all_consumables),
                'categories': {},
                'locations': {},
                'stock_levels': {
                    'sufficient': 0,
                    'warning': 0,
                    'critical': 0
                }
            }
            
            # Kategorie- und Standort-Statistiken
            for consumable in all_consumables:
                category = consumable.get('category', 'Keine Kategorie')
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
                
                location = consumable.get('location', 'Kein Standort')
                stats['locations'][location] = stats['locations'].get(location, 0) + 1
                
                # Bestandslevel
                quantity = consumable.get('quantity', 0)
                min_quantity = consumable.get('min_quantity', 0)
                
                if quantity >= min_quantity:
                    stats['stock_levels']['sufficient'] += 1
                elif quantity > 0:
                    stats['stock_levels']['warning'] += 1
                else:
                    stats['stock_levels']['critical'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Statistiken: {str(e)}")
            return {
                'total_consumables': 0,
                'categories': {},
                'locations': {},
                'stock_levels': {
                    'sufficient': 0,
                    'warning': 0,
                    'critical': 0
                }
            } 