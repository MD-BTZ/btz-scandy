from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from app.utils.decorators import admin_required, login_required, mitarbeiter_required
from app.models.mongodb_database import mongodb
import logging
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from datetime import datetime, timedelta

bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@bp.before_request
def log_request_info():
    """Loggt alle API-Requests"""
    logger.info(f"Request: {request.method} {request.url} - IP: {request.remote_addr}")

@bp.route('/workers', methods=['GET'])
@mitarbeiter_required
def get_workers():
    """Gibt alle aktiven Mitarbeiter zurück"""
    try:
        workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}).sort([('lastname', 1), ('firstname', 1)]))
        return jsonify({
            'success': True,
            'workers': workers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Laden der Mitarbeiter: {str(e)}'
        }), 500

@bp.route('/inventory/tools/<barcode>', methods=['GET'])
def get_tool(barcode):
    """Gibt Details zu einem Werkzeug zurück"""
    try:
        tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
        
        # Hole Ausleihhistorie
        lendings = mongodb.find('lendings', {'tool_barcode': barcode}, sort=[('lent_at', -1)])
        
        tool['lending_history'] = lendings
        tool['type'] = 'tool'  # Typ hinzufügen für Quickscan
        
        return jsonify({
            'success': True,
            'tool': tool
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Laden des Werkzeugs: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden des Werkzeugs'
        }), 500

@bp.route('/inventory/workers/<barcode>', methods=['GET'])
def get_worker(barcode):
    """Gibt Details zu einem Mitarbeiter zurück"""
    try:
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404
        
        # Hole aktive Ausleihen
        active_lendings = mongodb.find('lendings', {
            'worker_barcode': barcode,
            'returned_at': None
        }, sort=[('lent_at', -1)])
        
        # Hole Ausleihhistorie
        all_lendings = mongodb.find('lendings', {'worker_barcode': barcode}, sort=[('lent_at', -1)])
        
        worker['active_lendings'] = active_lendings
        worker['lending_history'] = all_lendings
        
        return jsonify({
            'success': True,
            'worker': worker
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Laden des Mitarbeiters: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden des Mitarbeiters'
        }), 500

@bp.route('/settings/colors', methods=['POST'])
@admin_required
def update_colors():
    """Aktualisiert die Farbeinstellungen"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Keine Daten empfangen'}), 400
        
        # Speichere die Farben in MongoDB
        for color_key, color_value in data.items():
            mongodb.update_one('settings', 
                             {'key': color_key}, 
                             {'$set': {'value': color_value}}, 
                             upsert=True)
        
        return jsonify({
            'success': True,
            'message': 'Farben erfolgreich aktualisiert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Farben: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Aktualisieren der Farben'
        }), 500

@bp.after_request
def after_request(response):
    """Loggt alle API-Responses"""
    logger.info(f"Response: {response.status_code} {response.status} {response.status_code} - Size: {len(response.get_data())} bytes")
    return response

@bp.route('/lending/return', methods=['POST'])
@login_required
def return_tool():
    """Gibt ein Werkzeug zurück"""
    try:
        data = request.get_json()
        tool_barcode = data.get('tool_barcode')
        worker_barcode = data.get('worker_barcode')
        
        logger.info(f"Return request: tool_barcode={tool_barcode}, worker_barcode={worker_barcode}")
        
        if not tool_barcode:
            logger.warning("Missing tool_barcode in return request")
            return jsonify({
                'success': False,
                'message': 'Fehlender tool_barcode Parameter'
            }), 400
        
        # Wenn kein worker_barcode angegeben ist, finde die aktuelle Ausleihe
        if not worker_barcode:
            lending = mongodb.find_one('lendings', {
                'tool_barcode': tool_barcode,
                'returned_at': None
            })
            
            if not lending:
                logger.warning(f"No active lending found for tool_barcode={tool_barcode}")
                return jsonify({
                    'success': False,
                    'message': 'Keine aktive Ausleihe für dieses Werkzeug gefunden'
                }), 404
                
            worker_barcode = lending.get('worker_barcode')
            logger.info(f"Found active lending with worker_barcode={worker_barcode}")
        else:
            # Finde aktuelle Ausleihe mit worker_barcode
            lending = mongodb.find_one('lendings', {
                'tool_barcode': tool_barcode,
                'worker_barcode': worker_barcode,
                'returned_at': None
            })
        
        logger.info(f"Found lending: {lending}")
        
        if not lending:
            logger.warning(f"No active lending found for tool_barcode={tool_barcode}, worker_barcode={worker_barcode}")
            return jsonify({
                'success': False,
                'message': 'Keine aktive Ausleihe gefunden'
            }), 404
        
        # Markiere als zurückgegeben
        success = mongodb.update_one('lendings', 
                          {
                              'tool_barcode': tool_barcode,
                              'worker_barcode': worker_barcode,
                              'returned_at': None
                          }, 
                          {'$set': {'returned_at': datetime.now()}})
        
        logger.info(f"Update lending result: {success}")
        
        # Aktualisiere Werkzeug-Status
        tool_success = mongodb.update_one('tools', 
                          {'barcode': tool_barcode}, 
                          {'$set': {'status': 'verfügbar'}})
        
        logger.info(f"Update tool result: {tool_success}")
        
        return jsonify({
            'success': True,
            'message': 'Werkzeug erfolgreich zurückgegeben'
        })
        
    except Exception as e:
        logger.error(f"Error in return_tool: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Rückgabe: {str(e)}'
        }), 500

@bp.route('/inventory/consumables/<barcode>', methods=['GET'])
def get_consumable(barcode):
    """Gibt Details zu einem Verbrauchsmaterial zurück"""
    try:
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not consumable:
            return jsonify({
                'success': False,
                'message': 'Verbrauchsmaterial nicht gefunden'
            }), 404
        
        # Hole Verbrauchshistorie
        usages = mongodb.find('consumable_usages', {'consumable_barcode': barcode}, sort=[('used_at', -1)])
        
        consumable['usage_history'] = usages
        consumable['type'] = 'consumable'  # Typ hinzufügen für Quickscan
        
        return jsonify({
            'success': True,
            'consumable': consumable
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Laden des Verbrauchsmaterials: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden des Verbrauchsmaterials'
        }), 500

@bp.route('/update_barcode', methods=['POST'])
@mitarbeiter_required
def update_barcode():
    """Aktualisiert einen Barcode"""
    try:
        data = request.get_json()
        old_barcode = data.get('old_barcode')
        new_barcode = data.get('new_barcode')
        item_type = data.get('type')
        
        if not all([old_barcode, new_barcode, item_type]):
            return jsonify({'success': False, 'message': 'Fehlende Parameter'})
        
        if item_type not in ['tool', 'consumable', 'worker']:
            return jsonify({'success': False, 'message': 'Ungültiger Typ'})
        
        # Prüfe ob neuer Barcode bereits existiert
        existing = mongodb.find_one(item_type + 's', {'barcode': new_barcode, 'deleted': {'$ne': True}})
        if existing:
            return jsonify({
                'success': False,
                'message': f'Barcode {new_barcode} existiert bereits'
            }), 400
        
        # Aktualisiere Barcode
        mongodb.update_one(item_type + 's', 
                          {'barcode': old_barcode}, 
                          {'$set': {'barcode': new_barcode}})
        
        # Aktualisiere auch in Ausleihen falls es ein Werkzeug ist
        if item_type == 'tool':
            mongodb.update_many('lendings', 
                              {'tool_barcode': old_barcode}, 
                              {'$set': {'tool_barcode': new_barcode}})
        
        # Aktualisiere auch in Verbrauchsmaterial-Entnahmen falls es ein Verbrauchsmaterial ist
        if item_type == 'consumable':
            mongodb.update_many('consumable_usages', 
                              {'consumable_barcode': old_barcode}, 
                              {'$set': {'consumable_barcode': new_barcode}})
        
        return jsonify({
            'success': True,
            'message': 'Barcode erfolgreich aktualisiert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Barcodes: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Aktualisieren des Barcodes'
        }), 500

@bp.route('/consumables/<barcode>/forecast', methods=['GET'])
@login_required
def get_consumable_forecast(barcode):
    """Berechnet eine Bestandsprognose für ein Verbrauchsmaterial"""
    try:
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not consumable:
            return jsonify({
                'success': False,
                'message': 'Verbrauchsmaterial nicht gefunden'
            }), 404
        
        # Hole Verbrauch der letzten 30 Tage
        thirty_days_ago = datetime.now() - timedelta(days=30)
        usages = list(mongodb.find('consumable_usages', {
            'consumable_barcode': barcode,
            'used_at': {'$gte': thirty_days_ago},
            'quantity': {'$lt': 0}  # Nur Entnahmen
        }))
        
        # Berechne durchschnittlichen täglichen Verbrauch
        total_usage = abs(sum(usage['quantity'] for usage in usages))
        avg_daily_usage = total_usage / 30 if usages else 0
        
        # Berechne Tage bis zur Neubestellung
        current_quantity = consumable.get('quantity', 0)
        days_until_reorder = int(current_quantity / avg_daily_usage) if avg_daily_usage > 0 else 999
        
        return jsonify({
            'success': True,
            'data': {
                'current_quantity': current_quantity,
                'avg_daily_usage': round(avg_daily_usage, 2),
                'days_until_reorder': days_until_reorder,
                'min_quantity': consumable.get('min_quantity', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Fehler bei der Bestandsprognose: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler bei der Berechnung'
        }), 500

@bp.route('/notices', methods=['GET'])
def get_notices():
    """Gibt alle aktiven Hinweise zurück"""
    try:
        notices = list(mongodb.find('homepage_notices', {'is_active': True}).sort([('priority', -1), ('created_at', -1)]))
        return jsonify({'success': True, 'notices': notices})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/notices/<int:id>', methods=['GET'])
@admin_required
def get_notice(id):
    """Gibt einen spezifischen Hinweis zurück"""
    try:
        notice = mongodb.find_one('homepage_notices', {'_id': id})
        if not notice:
            return jsonify({'error': 'Hinweis nicht gefunden'}), 404
        return jsonify({'success': True, 'notice': notice})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/notices', methods=['POST'])
@admin_required
def create_notice():
    """Erstellt einen neuen Hinweis"""
    try:
        data = request.get_json()
        notice_data = {
            'title': data.get('title'),
            'content': data.get('content'),
            'is_active': data.get('is_active', True),
            'priority': data.get('priority', 1),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        result = mongodb.insert_one('homepage_notices', notice_data)
        return jsonify({'success': True, 'id': str(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/notices/<int:id>', methods=['PUT'])
@admin_required
def update_notice(id):
    """Aktualisiert einen Hinweis"""
    try:
        data = request.get_json()
        update_data = {
            'title': data.get('title'),
            'content': data.get('content'),
            'is_active': data.get('is_active', True),
            'priority': data.get('priority', 1),
            'updated_at': datetime.now()
        }
        mongodb.update_one('homepage_notices', {'_id': id}, {'$set': update_data})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/notices/<int:id>', methods=['DELETE'])
@admin_required
def delete_notice(id):
    """Löscht einen Hinweis"""
    try:
        mongodb.delete_one('homepage_notices', {'_id': id})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/quickscan/process_lending', methods=['POST'])
@login_required
def process_lending():
    """Verarbeitet Ausleihe/Rückgabe über Quickscan"""
    try:
        import logging
        logger = logging.getLogger("quickscan")
        data = request.get_json()
        logger.info(f"QuickScan-Request: {data}")
        item_barcode = data.get('item_barcode')
        worker_barcode = data.get('worker_barcode')
        action = data.get('action')  # 'lend', 'return', 'consume'
        item_type = data.get('item_type')  # 'tool', 'consumable'
        quantity = data.get('quantity', 1)
        
        if not all([item_barcode, worker_barcode, action, item_type]):
            logger.error(f"Fehlende Parameter: {data}")
            return jsonify({
                'success': False,
                'message': 'Fehlende Parameter'
            }), 400
        
        # Prüfe ob Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': worker_barcode, 'deleted': {'$ne': True}})
        if not worker:
            logger.error(f"Mitarbeiter nicht gefunden: {worker_barcode}")
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404
        
        if item_type == 'tool':
            # Werkzeug-Verarbeitung
            tool = mongodb.find_one('tools', {'barcode': item_barcode, 'deleted': {'$ne': True}})
            if not tool:
                logger.error(f"Werkzeug nicht gefunden: {item_barcode}")
                return jsonify({
                    'success': False,
                    'message': 'Werkzeug nicht gefunden'
                }), 404
            
            if action == 'lend':
                # Prüfe ob Werkzeug verfügbar ist
                if tool.get('status') != 'verfügbar':
                    logger.error(f"Werkzeug nicht verfügbar: {item_barcode}")
                    return jsonify({
                        'success': False,
                        'message': 'Werkzeug ist nicht verfügbar'
                    }), 400
                
                # Erstelle Ausleihe
                lending_data = {
                    'tool_barcode': item_barcode,
                    'worker_barcode': worker_barcode,
                    'lent_at': datetime.now(),
                    'returned_at': None,
                    'tool_name': tool.get('name', ''),
                    'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip()
                }
                logger.info(f"Lege Ausleihe an: {lending_data}")
                mongodb.insert_one('lendings', lending_data)
                
                # Aktualisiere Werkzeug-Status
                mongodb.update_one('tools', 
                                  {'barcode': item_barcode}, 
                                  {'$set': {'status': 'ausgeliehen'}})
                logger.info(f"Werkzeug-Status auf 'ausgeliehen' gesetzt: {item_barcode}")
                
                return jsonify({
                    'success': True,
                    'message': f'Werkzeug "{tool.get("name", "")}" erfolgreich an {worker.get("firstname", "")} {worker.get("lastname", "")} ausgeliehen'
                })
                
            elif action == 'return':
                # Finde aktuelle Ausleihe
                lending = mongodb.find_one('lendings', {
                    'tool_barcode': item_barcode,
                    'worker_barcode': worker_barcode,
                    'returned_at': None
                })
                
                if not lending:
                    logger.error(f"Keine aktive Ausleihe gefunden: {item_barcode}, {worker_barcode}")
                    return jsonify({
                        'success': False,
                        'message': 'Keine aktive Ausleihe gefunden'
                    }), 404
                
                # Markiere als zurückgegeben
                mongodb.update_one('lendings', 
                                  {'_id': lending['_id']}, 
                                  {'$set': {'returned_at': datetime.now()}})
                logger.info(f"Ausleihe als zurückgegeben markiert: {lending['_id']}")
                
                # Aktualisiere Werkzeug-Status
                mongodb.update_one('tools', 
                                  {'barcode': item_barcode}, 
                                  {'$set': {'status': 'verfügbar'}})
                logger.info(f"Werkzeug-Status auf 'verfügbar' gesetzt: {item_barcode}")
                
                return jsonify({
                    'success': True,
                    'message': f'Werkzeug "{tool.get("name", "")}" erfolgreich zurückgegeben'
                })
        
        elif item_type == 'consumable':
            # Verbrauchsmaterial-Verarbeitung
            consumable = mongodb.find_one('consumables', {'barcode': item_barcode, 'deleted': {'$ne': True}})
            if not consumable:
                logger.error(f"Verbrauchsmaterial nicht gefunden: {item_barcode}")
                return jsonify({
                    'success': False,
                    'message': 'Verbrauchsmaterial nicht gefunden'
                }), 404
            
            if action == 'consume':
                # Prüfe verfügbare Menge
                current_quantity = consumable.get('quantity', 0)
                logger.info(f"Aktuelle Menge: {current_quantity}, Gewünschte Menge: {quantity}")
                if current_quantity < quantity:
                    logger.error(f"Nicht genügend verfügbar: {consumable.get('name', '')}, verfügbar: {current_quantity}, benötigt: {quantity}")
                    return jsonify({
                        'success': False,
                        'message': f'Nicht genügend {consumable.get("name", "")} verfügbar (verfügbar: {current_quantity}, benötigt: {quantity})'
                    }), 400
                
                # Erstelle Verbrauchseintrag (immer negativ für Entnahme)
                usage_data = {
                    'consumable_barcode': item_barcode,
                    'worker_barcode': worker_barcode,
                    'quantity': -abs(quantity),  # Negativ für Entnahme
                    'used_at': datetime.now(),
                    'consumable_name': consumable.get('name', ''),
                    'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip(),
                    'direction': 'out'
                }
                logger.info(f"Lege Verbrauchseintrag an: {usage_data}")
                mongodb.insert_one('consumable_usages', usage_data)
                
                # Reduziere verfügbare Menge
                new_quantity = current_quantity - quantity
                logger.info(f"Setze neue Menge: {new_quantity}")
                mongodb.update_one('consumables', 
                                  {'barcode': item_barcode}, 
                                  {'$set': {'quantity': new_quantity}})
                
                return jsonify({
                    'success': True,
                    'message': f'{quantity}x {consumable.get("name", "")} erfolgreich an {worker.get("firstname", "")} {worker.get("lastname", "")} ausgegeben'
                })
        
        logger.error(f"Ungültige Aktion: {action}, {item_type}")
        return jsonify({
            'success': False,
            'message': 'Ungültige Aktion'
        }), 400
        
    except Exception as e:
        import traceback
        logger.error(f"Fehler bei der Quickscan-Verarbeitung: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': 'Fehler bei der Verarbeitung'
        }), 500