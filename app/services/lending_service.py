"""
Zentraler Lending Service für Scandy
Alle Ausleihe/Rückgabe-Logik an einem Ort
"""
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from app.models.mongodb_database import mongodb
import logging

logger = logging.getLogger(__name__)

class LendingService:
    """Zentraler Service für alle Ausleihe/Rückgabe-Operationen"""
    
    @staticmethod
    def process_lending_request(data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verarbeitet eine Ausleihe/Rückgabe-Anfrage
        
        Args:
            data: Request-Daten mit item_barcode, worker_barcode, action, item_type, quantity
            
        Returns:
            (success, message, result_data)
        """
        try:
            item_barcode = data.get('item_barcode')
            worker_barcode = data.get('worker_barcode')
            action = data.get('action')  # 'lend', 'return', 'consume'
            item_type = data.get('item_type')  # 'tool', 'consumable'
            quantity = data.get('quantity', 1)
            
            # Validierung
            if not all([item_barcode, worker_barcode, action, item_type]):
                return False, 'Fehlende Parameter', {}
            
            # Prüfe ob Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': worker_barcode, 'deleted': {'$ne': True}})
            if not worker:
                return False, 'Mitarbeiter nicht gefunden', {}
            
            # Verarbeite basierend auf Item-Typ
            if item_type == 'tool':
                return LendingService._process_tool_lending(item_barcode, worker_barcode, action, worker)
            elif item_type == 'consumable':
                return LendingService._process_consumable_lending(item_barcode, worker_barcode, action, quantity, worker)
            else:
                return False, 'Ungültiger Item-Typ', {}
                
        except Exception as e:
            logger.error(f"Fehler bei der Ausleihe-Verarbeitung: {str(e)}")
            return False, f'Fehler bei der Verarbeitung: {str(e)}', {}
    
    @staticmethod
    def _process_tool_lending(item_barcode: str, worker_barcode: str, action: str, worker: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Verarbeitet Werkzeug-Ausleihe/Rückgabe"""
        try:
            # Prüfe ob Werkzeug existiert
            tool = mongodb.find_one('tools', {'barcode': item_barcode, 'deleted': {'$ne': True}})
            if not tool:
                return False, 'Werkzeug nicht gefunden', {}
            
            if action == 'lend':
                # Prüfe ob bereits ausgeliehen
                active_lending = mongodb.find_one('lendings', {
                    'tool_barcode': item_barcode,
                    'returned_at': None
                })
                
                if active_lending:
                    current_worker = mongodb.find_one('workers', {'barcode': active_lending['worker_barcode']})
                    worker_name = f"{current_worker['firstname']} {current_worker['lastname']}" if current_worker else "Unbekannt"
                    return False, f'Dieses Werkzeug ist bereits an {worker_name} ausgeliehen', {}
                
                if tool.get('status') == 'defekt':
                    return False, 'Dieses Werkzeug ist als defekt markiert', {}
                
                # Neue Ausleihe erstellen
                lending_data = {
                    'tool_barcode': item_barcode,
                    'worker_barcode': worker_barcode,
                    'lent_at': datetime.now()
                }
                mongodb.insert_one('lendings', lending_data)
                
                # Status des Werkzeugs aktualisieren
                mongodb.update_one('tools', 
                                 {'barcode': item_barcode}, 
                                 {'$set': {'status': 'ausgeliehen', 'modified_at': datetime.now()}})
                
                return True, f'Werkzeug {tool["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgeliehen', {
                    'tool_name': tool['name'],
                    'worker_name': f"{worker['firstname']} {worker['lastname']}"
                }
                
            elif action == 'return':
                # Prüfe ob ausgeliehen
                active_lending = mongodb.find_one('lendings', {
                    'tool_barcode': item_barcode,
                    'returned_at': None
                })
                
                if not active_lending:
                    return False, 'Dieses Werkzeug ist nicht ausgeliehen', {}
                
                # Rückgabe markieren
                mongodb.update_one('lendings', 
                                 {'_id': active_lending['_id']}, 
                                 {'$set': {'returned_at': datetime.now()}})
                
                # Status des Werkzeugs aktualisieren
                mongodb.update_one('tools', 
                                 {'barcode': item_barcode}, 
                                 {'$set': {'status': 'verfügbar', 'modified_at': datetime.now()}})
                
                return True, f'Werkzeug {tool["name"]} wurde erfolgreich zurückgegeben', {
                    'tool_name': tool['name']
                }
            
            else:
                return False, 'Ungültige Aktion für Werkzeug', {}
                
        except Exception as e:
            logger.error(f"Fehler bei Werkzeug-Ausleihe: {str(e)}")
            return False, f'Fehler bei der Werkzeug-Verarbeitung: {str(e)}', {}
    
    @staticmethod
    def _process_consumable_lending(item_barcode: str, worker_barcode: str, action: str, quantity: int, worker: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Verarbeitet Verbrauchsmaterial-Entnahme"""
        try:
            if action != 'consume':
                return False, 'Ungültige Aktion für Verbrauchsmaterial', {}
            
            # Prüfe ob Verbrauchsmaterial existiert
            consumable = mongodb.find_one('consumables', {'barcode': item_barcode, 'deleted': {'$ne': True}})
            if not consumable:
                return False, 'Verbrauchsmaterial nicht gefunden', {}
            
            # Prüfe verfügbare Menge
            current_quantity = consumable.get('quantity', 0)
            if current_quantity < quantity:
                return False, f'Nicht genügend {consumable.get("name", "")} verfügbar (verfügbar: {current_quantity}, benötigt: {quantity})', {}
            
            # Erstelle Verbrauchseintrag
            usage_data = {
                'consumable_barcode': item_barcode,
                'worker_barcode': worker_barcode,
                'quantity': -abs(quantity),  # Negativ für Entnahme
                'used_at': datetime.now(),
                'consumable_name': consumable.get('name', ''),
                'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip(),
                'direction': 'out'
            }
            mongodb.insert_one('consumable_usages', usage_data)
            
            # Reduziere verfügbare Menge
            new_quantity = current_quantity - quantity
            mongodb.update_one('consumables', 
                              {'barcode': item_barcode}, 
                              {'$set': {'quantity': new_quantity}})
            
            return True, f'{quantity}x {consumable.get("name", "")} erfolgreich an {worker.get("firstname", "")} {worker.get("lastname", "")} ausgegeben', {
                'consumable_name': consumable.get('name', ''),
                'quantity': quantity,
                'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip()
            }
            
        except Exception as e:
            logger.error(f"Fehler bei Verbrauchsmaterial-Entnahme: {str(e)}")
            return False, f'Fehler bei der Verbrauchsmaterial-Verarbeitung: {str(e)}', {}
    
    @staticmethod
    def get_active_lendings() -> list:
        """Holt alle aktiven Ausleihen"""
        try:
            active_lendings = mongodb.find('lendings', {'returned_at': None})
            
            # Erweitere mit Tool- und Worker-Informationen
            enriched_lendings = []
            for lending in active_lendings:
                tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
                worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
                
                if tool and worker:
                    enriched_lendings.append({
                        **lending,
                        'tool_name': tool['name'],
                        'worker_name': f"{worker['firstname']} {worker['lastname']}",
                        'lent_at': lending['lent_at']
                    })
            
            # Sortiere nach Datum (neueste zuerst)
            enriched_lendings.sort(key=lambda x: x.get('lent_at', datetime.min), reverse=True)
            return enriched_lendings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aktiver Ausleihen: {str(e)}")
            return []
    
    @staticmethod
    def get_recent_consumable_usage(limit: int = 10) -> list:
        """Holt die letzten Verbrauchsmaterial-Entnahmen"""
        try:
            recent_usages = mongodb.find('consumable_usages')
            # Sortiere und limitiere
            recent_usages.sort(key=lambda x: x.get('used_at', datetime.min), reverse=True)
            recent_usages = recent_usages[:limit]
            
            # Erweitere mit Consumable- und Worker-Informationen
            enriched_usages = []
            for usage in recent_usages:
                consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
                worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
                
                if consumable and worker:
                    enriched_usages.append({
                        'consumable_name': consumable['name'],
                        'quantity': usage['quantity'],
                        'worker_name': f"{worker['firstname']} {worker['lastname']}",
                        'used_at': usage['used_at']
                    })
            
            return enriched_usages
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Entnahmen: {str(e)}")
            return []
    
    def get_current_lending(self, tool_barcode: str) -> Optional[Dict[str, Any]]:
        """
        Holt die aktuelle Ausleihe für ein Werkzeug
        
        Args:
            tool_barcode: Barcode des Werkzeugs
            
        Returns:
            Optional[Dict]: Aktuelle Ausleihe oder None
        """
        try:
            current_lending = mongodb.find_one('lendings', {
                'tool_barcode': tool_barcode,
                'returned_at': None
            })
            
            if current_lending:
                # Worker-Informationen hinzufügen
                worker = mongodb.find_one('workers', {'barcode': current_lending['worker_barcode']})
                if worker:
                    current_lending['worker_name'] = f"{worker['firstname']} {worker['lastname']}"
                
                # Datetime-Felder konvertieren
                if isinstance(current_lending.get('lent_at'), str):
                    try:
                        current_lending['lent_at'] = datetime.strptime(current_lending['lent_at'], '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        current_lending['lent_at'] = datetime.now()
            
            return current_lending
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der aktuellen Ausleihe für {tool_barcode}: {str(e)}")
            return None
    
    def get_tool_lending_history(self, tool_barcode: str) -> List[Dict[str, Any]]:
        """
        Holt die Ausleihhistorie für ein Werkzeug
        
        Args:
            tool_barcode: Barcode des Werkzeugs
            
        Returns:
            List: Liste der Ausleihen
        """
        try:
            lendings = list(mongodb.find('lendings', {'tool_barcode': tool_barcode}))
            
            # Sortiere nach Datum (neueste zuerst) - sicherer Vergleich
            def safe_date_key(lending):
                lent_at = lending.get('lent_at')
                if isinstance(lent_at, str):
                    try:
                        return datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        return datetime.min
                elif isinstance(lent_at, datetime):
                    return lent_at
                else:
                    return datetime.min
            
            lendings.sort(key=safe_date_key, reverse=True)
            
            # Erstelle Verlaufsliste
            history = []
            for lending in lendings:
                worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
                worker_name = f"{worker['firstname']} {worker['lastname']}" if worker else "Unbekannt"
                
                # Stelle sicher, dass das Datum korrekt formatiert wird
                action_date = lending['lent_at']
                if isinstance(action_date, str):
                    try:
                        action_date = datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        action_date = datetime.now()
                
                history.append({
                    'lent_at': action_date,
                    'worker_name': worker_name,
                    'worker_barcode': lending['worker_barcode'],
                    'returned_at': lending.get('returned_at'),
                    'status': 'Zurückgegeben' if lending.get('returned_at') else 'Ausgeliehen'
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ausleihhistorie für {tool_barcode}: {str(e)}")
            return [] 