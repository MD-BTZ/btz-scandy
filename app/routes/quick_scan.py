from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.models.database import Database
import logging

bp = Blueprint('quick_scan', __name__, url_prefix='/quick_scan')
logger = logging.getLogger(__name__)

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
                'SELECT barcode, firstname, lastname FROM workers WHERE barcode = ? AND deleted = 0',
                (worker_barcode,)
            ).fetchone()
            
            if not worker:
                return jsonify({'error': 'Mitarbeiter nicht gefunden'}), 404
                
            # Prüfe ob es ein Tool oder Consumable ist
            tool = db.execute('''
                SELECT t.*, 
                       CASE 
                           WHEN EXISTS (
                               SELECT 1 FROM lendings l 
                               WHERE l.tool_barcode = t.barcode 
                               AND l.returned_at IS NULL
                           ) THEN 'ausgeliehen'
                           ELSE t.status
                       END as current_status,
                       (
                           SELECT w.firstname || ' ' || w.lastname
                           FROM lendings l
                           JOIN workers w ON l.worker_barcode = w.barcode
                           WHERE l.tool_barcode = t.barcode
                           AND l.returned_at IS NULL
                           LIMIT 1
                       ) as current_worker_name,
                       (
                           SELECT l.worker_barcode
                           FROM lendings l
                           WHERE l.tool_barcode = t.barcode
                           AND l.returned_at IS NULL
                           LIMIT 1
                       ) as current_worker_barcode
                FROM tools t
                WHERE t.barcode = ? AND t.deleted = 0
            ''', (item_barcode,)).fetchone()
            
            if tool:
                # Werkzeug-Logik
                if action == 'lend':
                    if tool['current_status'] == 'ausgeliehen':
                        return jsonify({'error': f'Dieses Werkzeug ist bereits an {tool["current_worker_name"]} ausgeliehen'}), 400
                        
                    if tool['current_status'] == 'defekt':
                        return jsonify({'error': 'Dieses Werkzeug ist als defekt markiert'}), 400
                        
                    # Neue Ausleihe erstellen
                    db.execute('''
                        INSERT INTO lendings 
                        (tool_barcode, worker_barcode, lent_at)
                        VALUES (?, ?, datetime('now'))
                    ''', (item_barcode, worker_barcode))
                    
                    # Status des Werkzeugs aktualisieren
                    db.execute('''
                        UPDATE tools 
                        SET status = 'ausgeliehen',
                            modified_at = datetime('now'),
                            sync_status = 'pending'
                        WHERE barcode = ?
                    ''', (item_barcode,))
                    
                    db.commit()
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
                    db.execute('''
                        UPDATE lendings 
                        SET returned_at = datetime('now')
                        WHERE tool_barcode = ? 
                        AND returned_at IS NULL
                    ''', (item_barcode,))
                    
                    # Status des Werkzeugs aktualisieren
                    db.execute('''
                        UPDATE tools 
                        SET status = 'verfügbar',
                            modified_at = datetime('now'),
                            sync_status = 'pending'
                        WHERE barcode = ?
                    ''', (item_barcode,))
                    
                    db.commit()
                    return jsonify({
                        'message': f'Werkzeug {tool["name"]} wurde von {worker["firstname"]} {worker["lastname"]} zurückgegeben'
                    })
                    
                else:
                    return jsonify({'error': 'Ungültige Aktion für Werkzeug'}), 400
                    
            else:
                # Prüfe ob es ein Verbrauchsmaterial ist
                consumable = db.execute('''
                    SELECT * FROM consumables 
                    WHERE barcode = ? AND deleted = 0
                ''', (item_barcode,)).fetchone()
                
                if consumable:
                    if action == 'use':
                        # Verbrauchsmaterial-Logik
                        if consumable['quantity'] <= 0:
                            return jsonify({'error': 'Kein Bestand verfügbar'}), 400
                            
                        # Verbrauchsmaterial-Ausgabe erstellen
                        db.execute('''
                            INSERT INTO consumable_usages 
                            (consumable_barcode, worker_barcode, quantity, used_at)
                            VALUES (?, ?, -1, datetime('now'))
                        ''', (item_barcode, worker_barcode))
                        
                        # Bestand aktualisieren
                        db.execute('''
                            UPDATE consumables
                            SET quantity = quantity - 1,
                                modified_at = datetime('now'),
                                sync_status = 'pending'
                            WHERE barcode = ?
                        ''', (item_barcode,))
                        
                        db.commit()
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