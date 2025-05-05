from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models.database import Database

bp = Blueprint('quick_scan', __name__, url_prefix='/quick_scan')

@bp.route('/')
@login_required
def quick_scan():
    return render_template('quick_scan.html')

@bp.route('/process', methods=['POST'])
@login_required
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
            
        with Database.get_db() as db:
            # Prüfe ob Worker existiert
            worker = db.execute(
                'SELECT id, firstname, lastname FROM workers WHERE barcode = ?',
                (worker_barcode,)
            ).fetchone()
            
            if not worker:
                return jsonify({'error': 'Mitarbeiter nicht gefunden'}), 404
                
            # Prüfe ob es ein Tool oder Consumable ist
            tool = db.execute(
                'SELECT id, name, status FROM tools WHERE barcode = ?',
                (item_barcode,)
            ).fetchone()
            
            if tool:
                # Werkzeug-Logik
                if action == 'lend':
                    if tool['status'] != 'verfügbar':
                        return jsonify({'error': 'Werkzeug ist nicht verfügbar'}), 400
                        
                    # Werkzeug ausleihen
                    db.execute('''
                        INSERT INTO lendings (tool_barcode, worker_barcode, lent_at)
                        VALUES (?, ?, datetime('now'))
                    ''', (item_barcode, worker_barcode))
                    
                    # Status aktualisieren
                    db.execute('''
                        UPDATE tools 
                        SET status = 'ausgeliehen'
                        WHERE id = ?
                    ''', (tool['id'],))
                    
                    db.commit()
                    return jsonify({
                        'message': f'Werkzeug {tool["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgeliehen'
                    })
                    
                elif action == 'return':
                    if tool['status'] != 'ausgeliehen':
                        return jsonify({'error': 'Werkzeug ist nicht ausgeliehen'}), 400
                        
                    # Ausleihe beenden
                    db.execute('''
                        UPDATE lendings
                        SET returned_at = datetime('now')
                        WHERE tool_barcode = ? AND returned_at IS NULL
                    ''', (item_barcode,))
                    
                    # Status aktualisieren
                    db.execute('''
                        UPDATE tools 
                        SET status = 'verfügbar'
                        WHERE id = ?
                    ''', (tool['id'],))
                    
                    db.commit()
                    return jsonify({
                        'message': f'Werkzeug {tool["name"]} wurde von {worker["firstname"]} {worker["lastname"]} zurückgegeben'
                    })
                    
                else:
                    return jsonify({'error': 'Ungültige Aktion für Werkzeug'}), 400
                    
            else:
                # Prüfe ob es ein Consumable ist
                consumable = db.execute(
                    'SELECT id, name, quantity FROM consumables WHERE barcode = ?',
                    (item_barcode,)
                ).fetchone()
                
                if not consumable:
                    return jsonify({'error': 'Artikel nicht gefunden'}), 404
                    
                if action != 'consume':
                    return jsonify({'error': 'Ungültige Aktion für Verbrauchsmaterial'}), 400
                    
                # Prüfe ob genug Material verfügbar
                if consumable['quantity'] <= 0:
                    return jsonify({'error': 'Verbrauchsmaterial nicht verfügbar'}), 400
                    
                # Verbrauch eintragen
                db.execute('''
                    INSERT INTO consumable_usages (consumable_barcode, worker_barcode, quantity, used_at)
                    VALUES (?, ?, 1, datetime('now'))
                ''', (item_barcode, worker_barcode))
                
                # Bestand reduzieren
                db.execute('''
                    UPDATE consumables
                    SET quantity = quantity - 1
                    WHERE id = ?
                ''', (consumable['id'],))
                
                db.commit()
                return jsonify({
                    'message': f'Verbrauchsmaterial {consumable["name"]} wurde von {worker["firstname"]} {worker["lastname"]} entnommen'
                })
                
    except Exception as e:
        print('Fehler bei QuickScan:', str(e))
        return jsonify({'error': 'Interner Serverfehler'}), 500 