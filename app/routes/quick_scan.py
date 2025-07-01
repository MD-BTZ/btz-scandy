from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models.mongodb_models import MongoDBTool, MongoDBWorker
from app.models.mongodb_database import mongodb
from datetime import datetime
from app.utils.decorators import not_teilnehmer_required
import logging

bp = Blueprint('quick_scan', __name__, url_prefix='/quick_scan')
logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
@not_teilnehmer_required
def quick_scan():
    return render_template('quick_scan.html')

@bp.route('/process', methods=['POST'])
@login_required
@not_teilnehmer_required
def process():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Keine Daten erhalten'}), 400
            
        item_barcode = data.get('item_barcode')
        worker_barcode = data.get('worker_barcode')
        action = data.get('action')
        
        if not all([item_barcode, worker_barcode, action]):
            return jsonify({'error': 'Fehlende Parameter'}), 400
            
        # Prüfe ob Worker existiert
        worker = mongodb.find_one('workers', {'barcode': worker_barcode, 'deleted': {'$ne': True}})
        
        if not worker:
            return jsonify({'error': 'Mitarbeiter nicht gefunden'}), 404
            
        # Prüfe ob es ein Tool ist
        tool = mongodb.find_one('tools', {'barcode': item_barcode, 'deleted': {'$ne': True}})
        
        if tool:
            # Prüfe aktuelle Ausleihe
            current_lending = mongodb.find_one('lendings', {
                'tool_barcode': item_barcode,
                'returned_at': None
            })
            
            if current_lending:
                tool['current_status'] = 'ausgeliehen'
                current_worker = mongodb.find_one('workers', {'barcode': current_lending['worker_barcode']})
                tool['current_worker_name'] = f"{current_worker['firstname']} {current_worker['lastname']}" if current_worker else "Unbekannt"
                tool['current_worker_barcode'] = current_lending['worker_barcode']
            else:
                tool['current_status'] = tool.get('status', 'verfügbar')
                tool['current_worker_name'] = None
                tool['current_worker_barcode'] = None
            
            # Werkzeug-Logik
            if action == 'lend':
                if tool['current_status'] == 'ausgeliehen':
                    return jsonify({'error': f'Dieses Werkzeug ist bereits an {tool["current_worker_name"]} ausgeliehen'}), 400
                    
                if tool['current_status'] == 'defekt':
                    return jsonify({'error': 'Dieses Werkzeug ist als defekt markiert'}), 400
                    
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
                
                return jsonify({
                    'message': f'Werkzeug {tool["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgeliehen'
                })
                
            elif action == 'return':
                if tool['current_status'] != 'ausgeliehen':
                    return jsonify({'error': 'Dieses Werkzeug ist nicht ausgeliehen'}), 400
                
                # Wenn ein Mitarbeiter angegeben wurde, prüfe ob er berechtigt ist
                if worker_barcode and tool['current_worker_barcode'] != worker_barcode:
                    return jsonify({'error': f'Dieses Werkzeug wurde von {tool["current_worker_name"]} ausgeliehen'}), 403
                
                # Rückgabe verarbeiten
                mongodb.update_one('lendings', 
                                 {'tool_barcode': item_barcode, 'returned_at': None}, 
                                 {'$set': {'returned_at': datetime.now()}})
                
                # Status des Werkzeugs aktualisieren
                mongodb.update_one('tools', 
                                 {'barcode': item_barcode}, 
                                 {'$set': {'status': 'verfügbar', 'modified_at': datetime.now()}})
                
                return jsonify({
                    'message': f'Werkzeug {tool["name"]} wurde von {worker["firstname"]} {worker["lastname"]} zurückgegeben'
                })
                
            else:
                return jsonify({'error': 'Ungültige Aktion für Werkzeug'}), 400
                
        else:
            # Prüfe ob es ein Verbrauchsmaterial ist
            consumable = mongodb.find_one('consumables', {'barcode': item_barcode, 'deleted': {'$ne': True}})
            
            if consumable:
                if action == 'use':
                    # Verbrauchsmaterial-Logik
                    if consumable['quantity'] <= 0:
                        return jsonify({'error': 'Kein Bestand verfügbar'}), 400
                        
                    # Verbrauchsmaterial-Ausgabe erstellen
                    usage_data = {
                        'consumable_barcode': item_barcode,
                        'worker_barcode': worker_barcode,
                        'quantity': -1,
                        'used_at': datetime.now()
                    }
                    mongodb.insert_one('consumable_usages', usage_data)
                    
                    # Bestand aktualisieren
                    mongodb.update_one('consumables', 
                                     {'barcode': item_barcode}, 
                                     {'$inc': {'quantity': -1}, '$set': {'modified_at': datetime.now()}})
                    
                    return jsonify({
                        'message': f'Verbrauchsmaterial {consumable["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgegeben'
                    })
                else:
                    return jsonify({'error': 'Ungültige Aktion für Verbrauchsmaterial'}), 400
            else:
                return jsonify({'error': 'Artikel nicht gefunden'}), 404
                
    except Exception as e:
        logger.error(f"Fehler bei QuickScan-Verarbeitung: {str(e)}", exc_info=True)
        return jsonify({'error': f'Interner Fehler: {str(e)}'}), 500 