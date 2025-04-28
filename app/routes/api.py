from flask import Blueprint, jsonify, request, current_app
from ..models.worker import Worker
from ..models.tool import Tool
from ..models.database import Database
from ..utils.decorators import login_required, admin_required
import traceback
from app.config import Config
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from datetime import datetime, timedelta

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.before_request
def log_request_info():
    """Loggt Details über eingehende Requests"""
    print('\n=== API Request Debug Info ===')
    print(f'Endpoint: {request.endpoint}')
    print(f'Method: {request.method}')
    print(f'URL: {request.url}')
    print(f'Headers: {dict(request.headers)}')
    print(f'Data: {request.get_data(as_text=True)}')
    print('===========================\n')

@bp.route('/workers', methods=['GET'])
def get_workers():
    workers = Worker.get_all_with_lendings()
    return jsonify([{
        'id': w['id'],
        'barcode': w['barcode'],
        'name': f"{w['firstname']} {w['lastname']}",
        'department': w['department']
    } for w in workers])

@bp.route('/inventory/tools/<barcode>', methods=['GET'])
def get_tool(barcode):
    """Sucht ein Werkzeug anhand des Barcodes"""
    try:
        print(f"Suche Werkzeug mit Barcode: {barcode}")
        
        tool = Database.query('''
            SELECT t.*,
                   CASE 
                       WHEN EXISTS (
                           SELECT 1 FROM lendings l 
                           WHERE l.tool_barcode = t.barcode 
                           AND l.returned_at IS NULL
                       ) THEN 'ausgeliehen'
                       WHEN t.status = 'defekt' THEN 'defekt'
                       ELSE 'verfügbar'
                   END as current_status,
                   CASE 
                       WHEN EXISTS (
                           SELECT 1 FROM lendings l 
                           WHERE l.tool_barcode = t.barcode 
                           AND l.returned_at IS NULL
                       ) THEN 'Ausgeliehen'
                       WHEN t.status = 'defekt' THEN 'Defekt'
                       ELSE 'Verfügbar'
                   END as status_text
            FROM tools t
            WHERE t.barcode = ? AND t.deleted = 0
        ''', [barcode], one=True)
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
            
        tool_dict = dict(tool)
        tool_dict['type'] = 'tool'
        print(f"Gefundenes Werkzeug: {tool_dict}")
            
        return jsonify({
            'success': True,
            'data': tool_dict
        })
        
    except Exception as e:
        print(f"Fehler bei Werkzeugsuche: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Suche: {str(e)}'
        }), 500

@bp.route('/inventory/workers/<barcode>', methods=['GET'])
def get_worker_by_barcode(barcode):
    try:
        # Debug-Logging
        print(f"Suche Mitarbeiter mit Barcode: {barcode}")
        
        worker = Database.query('''
            SELECT 
                id,
                barcode,
                firstname,
                lastname,
                department,
                email
            FROM workers 
            WHERE barcode = ? 
            AND deleted = 0
        ''', [barcode], one=True)
        
        # Debug-Logging
        print(f"Gefundener Mitarbeiter: {worker}")
        
        if not worker:
            print(f"Kein Mitarbeiter gefunden für Barcode: {barcode}")
            return jsonify({'error': 'Mitarbeiter nicht gefunden'}), 404
            
        # Konvertiere Row-Objekt in Dictionary
        worker_dict = dict(worker)
        print(f"Konvertierter Mitarbeiter: {worker_dict}")
            
        return jsonify(worker_dict)
        
    except Exception as e:
        print(f"Fehler bei Mitarbeitersuche: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/settings/colors', methods=['POST'])
@admin_required
def update_colors():
    try:
        data = request.json
        print("\n=== Color Settings Debug Info ===")
        print(f"Empfangene Farbdaten: {data}")
        print(f"Request Method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Alle registrierten Routen:")
        for rule in current_app.url_map.iter_rules():
            print(f"  {rule.endpoint}: {rule}")
        
        if not data:
            print("Keine JSON-Daten empfangen!")
            return jsonify({'error': 'Keine Daten empfangen'}), 400
            
        with Database.get_db() as conn:
            # Primärfarbe aktualisieren
            conn.execute('''
                INSERT OR REPLACE INTO settings (key, value) 
                VALUES (?, ?)
            ''', ('primary_color', data.get('primary_color')))
            
            # Akzentfarbe aktualisieren
            conn.execute('''
                INSERT OR REPLACE INTO settings (key, value) 
                VALUES (?, ?)
            ''', ('accent_color', data.get('accent_color')))
            
            conn.commit()
            print("Farben erfolgreich in Datenbank gespeichert")
            
        return jsonify({
            'status': 'success', 
            'message': 'Farben erfolgreich aktualisiert',
            'data': {
                'primary_color': data.get('primary_color'),
                'accent_color': data.get('accent_color')
            }
        })
        
    except Exception as e:
        error_details = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'request_data': {
                'method': request.method,
                'url': request.url,
                'headers': dict(request.headers),
                'data': request.get_data(as_text=True)
            }
        }
        print("\n=== Error Debug Info ===")
        print(f"Fehler beim Speichern der Farben:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}")
        print("========================\n")
        
        return jsonify(error_details), 500

@bp.after_request
def after_request(response):
    """Loggt Details über ausgehende Responses"""
    print('\n=== API Response Debug Info ===')
    print(f'Status: {response.status}')
    print(f'Headers: {dict(response.headers)}')
    print(f'Data: {response.get_data(as_text=True)}')
    print('============================\n')
    return response

@bp.route('/lending/return', methods=['POST'])
@admin_required
def return_tool():
    try:
        data = request.json
        tool_barcode = data.get('tool_barcode')
        worker_barcode = data.get('worker_barcode')  # Optional für Validierung
        
        if not tool_barcode:
            return jsonify({
                'success': False, 
                'message': 'Werkzeug-Barcode fehlt'
            }), 400
            
        with Database.get_db() as conn:
            # Prüfe aktuellen Ausleihstatus
            current_lending = conn.execute("""
                SELECT l.*, w.firstname || ' ' || w.lastname as worker_name
                FROM lendings l
                JOIN workers w ON l.worker_barcode = w.barcode
                WHERE l.tool_barcode = ? 
                AND l.returned_at IS NULL
            """, [tool_barcode]).fetchone()
            
            if not current_lending:
                return jsonify({
                    'success': False,
                    'message': 'Keine aktive Ausleihe für dieses Werkzeug gefunden'
                }), 400
            
            # Wenn ein Mitarbeiter-Barcode angegeben wurde, prüfe ob er berechtigt ist
            if worker_barcode and current_lending['worker_barcode'] != worker_barcode:
                return jsonify({
                    'success': False,
                    'message': f'Dieses Werkzeug wurde von {current_lending["worker_name"]} ausgeliehen'
                }), 403
            
            # Aktualisiere Ausleihe
            conn.execute("""
                UPDATE lendings 
                SET returned_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'),
                    sync_status = 'pending'
                WHERE tool_barcode = ? 
                AND returned_at IS NULL
            """, [tool_barcode])
            
            # Setze Tool-Status zurück
            conn.execute("""
                UPDATE tools 
                SET status = 'verfügbar',
                    sync_status = 'pending'
                WHERE barcode = ?
            """, [tool_barcode])
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Werkzeug erfolgreich zurückgegeben'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Rückgabe: {str(e)}'
        }), 500

@bp.route('/tools/<barcode>/delete', methods=['POST'])
@admin_required
def delete_tool(barcode):
    db = Database()
    result = db.soft_delete_tool(barcode)
    return jsonify(result)

# Sync-Routen temporär deaktiviert
"""
@bp.route('/sync/start', methods=['POST'])
def start_sync():
    sync_manager = current_app.extensions.get('sync_manager')
    if sync_manager:
        sync_manager.start_sync_scheduler()
        return jsonify({'success': True, 'message': 'Sync-Scheduler gestartet'})
    return jsonify({'success': False, 'message': 'Sync-Manager nicht verfügbar'})

@bp.route('/sync/stop', methods=['POST'])
def stop_sync():
    sync_manager = current_app.extensions.get('sync_manager')
    if sync_manager:
        sync_manager.stop_sync_scheduler()
        return jsonify({'success': True, 'message': 'Sync-Scheduler gestoppt'})
    return jsonify({'success': False, 'message': 'Sync-Manager nicht verfügbar'})
"""

@bp.route('/sync/auto', methods=['POST'])
@admin_required
def toggle_auto_sync():
    """Aktiviert/Deaktiviert automatische Synchronisation"""
    try:
        data = request.get_json()
        enabled = data.get('enabled', False)
        
        sync_manager = current_app.extensions['sync_manager']
        
        if enabled:
            sync_manager.start_sync_scheduler()
            message = 'Automatische Synchronisation aktiviert'
        else:
            sync_manager.stop_sync_scheduler()
            message = 'Automatische Synchronisation deaktiviert'
            
        # Speichere Einstellung in der Datenbank
        Database.query('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', ['auto_sync', str(int(enabled))])
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler: {str(e)}'
        }), 500

@bp.route('/sync/now', methods=['POST'])
@admin_required
def trigger_sync():
    """Löst manuelle Synchronisation aus"""
    try:
        result = Database.sync_with_server()
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Sync-Fehler: {str(e)}'
        }), 500

@bp.route('/sync/status')
@admin_required
def get_sync_status():
    """Gibt den aktuellen Sync-Status zurück"""
    try:
        status = Database.query('''
            SELECT last_sync, last_attempt, status, error
            FROM sync_status
            ORDER BY id DESC LIMIT 1
        ''', one=True)
        
        auto_sync = Database.query('''
            SELECT value FROM settings
            WHERE key = 'auto_sync'
        ''', one=True)
        
        return jsonify({
            'success': True,
            'last_sync': status['last_sync'] if status else None,
            'last_attempt': status['last_attempt'] if status else None,
            'status': status['status'] if status else 'never',
            'error': status['error'] if status else None,
            'auto_sync': bool(int(auto_sync['value'])) if auto_sync else False
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler: {str(e)}'
        }), 500

@bp.route('/barcode/<code>')
def generate_barcode(code):
    """Generiert einen Barcode als Bild"""
    try:
        code128 = barcode.get('code128', code, writer=ImageWriter())
        buffer = BytesIO()
        code128.write(buffer)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        return jsonify({
            'barcode': f'data:image/png;base64,{image_base64}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/lending/process', methods=['POST'])
@admin_required
def admin_process_lending():
    """Verarbeitet eine Ausleihe oder Rückgabe (Admin-Version)"""
    try:
        data = request.json
        item_type = data.get('type')
        item_id = data.get('item_id')
        worker_id = data.get('worker_id')
        action = data.get('action')
        
        with Database.get_db() as conn:
            if item_type == 'tool':
                if action == 'lend':
                    conn.execute(
                        '''INSERT INTO lendings 
                           (tool_id, worker_id, lent_at) 
                           VALUES (?, ?, CURRENT_TIMESTAMP)''',
                        [item_id, worker_id]
                    )
                    conn.execute(
                        'UPDATE tools SET status = "ausgeliehen" WHERE id = ?',
                        [item_id]
                    )
                else:
                    conn.execute(
                        '''UPDATE lendings 
                           SET returned_at = CURRENT_TIMESTAMP 
                           WHERE tool_id = ? AND returned_at IS NULL''',
                        [item_id]
                    )
                    conn.execute(
                        'UPDATE tools SET status = "verfügbar" WHERE id = ?',
                        [item_id]
                    )
            
            elif item_type == 'consumable':
                conn.execute(
                    '''INSERT INTO consumable_usage 
                       (consumable_id, worker_id, quantity, used_at) 
                       VALUES (?, ?, 1, CURRENT_TIMESTAMP)''',
                    [item_id, worker_id]
                )
                conn.execute(
                    'UPDATE consumables SET quantity = quantity - 1 WHERE id = ?',
                    [item_id]
                )
            
            conn.commit()
            return jsonify({'success': True})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/inventory/item/<barcode>')
@login_required
def get_item(barcode):
    """Gibt Details zu einem Artikel (Tool oder Consumable) zurück"""
    try:
        with Database.get_db() as db:
            # Prüfe zuerst ob es ein Werkzeug ist
            tool = db.execute('''
                SELECT id, barcode, name, status, current_worker_id
                FROM tools 
                WHERE barcode = ?
            ''', (barcode,)).fetchone()
            
            if tool:
                # Hole aktuelle Ausleihe falls vorhanden
                lending = None
                if tool['current_worker_id']:
                    lending = db.execute('''
                        SELECT w.firstname, w.lastname, w.department,
                               l.lent_at
                        FROM lendings l
                        JOIN workers w ON w.id = l.worker_id
                        WHERE l.tool_id = ? AND l.returned_at IS NULL
                    ''', (tool['id'],)).fetchone()
                
                return jsonify({
                    'id': tool['id'],
                    'barcode': tool['barcode'],
                    'name': tool['name'],
                    'type': 'tool',
                    'status': tool['status'],
                    'lending': lending
                })
            
            # Wenn kein Werkzeug, prüfe ob es ein Verbrauchsmaterial ist
            consumable = db.execute('''
                SELECT id, barcode, name, quantity, min_quantity
                FROM consumables 
                WHERE barcode = ?
            ''', (barcode,)).fetchone()
            
            if consumable:
                return jsonify({
                    'id': consumable['id'],
                    'barcode': consumable['barcode'],
                    'name': consumable['name'],
                    'type': 'consumable',
                    'quantity': consumable['quantity'],
                    'min_quantity': consumable['min_quantity']
                })
            
            return jsonify({'error': 'Artikel nicht gefunden'}), 404
            
    except Exception as e:
        print('Fehler beim Abrufen des Artikels:', str(e))
        return jsonify({'error': 'Interner Serverfehler'}), 500

@bp.route('/inventory/workers/<barcode>')
@login_required
def get_worker(barcode):
    """Gibt Details zu einem Mitarbeiter zurück"""
    try:
        with Database.get_db() as db:
            worker = db.execute('''
                SELECT id, barcode, firstname, lastname, department
                FROM workers 
                WHERE barcode = ?
            ''', (barcode,)).fetchone()
            
            if not worker:
                return jsonify({'error': 'Mitarbeiter nicht gefunden'}), 404
            
            # Hole aktuelle Ausleihen
            lendings = db.execute('''
                SELECT t.name as tool_name, 
                       l.lent_at,
                       CASE 
                           WHEN julianday('now') - julianday(l.lent_at) > 7 
                           THEN 1 ELSE 0 
                       END as is_overdue
                FROM lendings l
                JOIN tools t ON t.id = l.tool_id
                WHERE l.worker_id = ? AND l.returned_at IS NULL
                ORDER BY l.lent_at DESC
            ''', (worker['id'],)).fetchall()
            
            return jsonify({
                'id': worker['id'],
                'barcode': worker['barcode'],
                'firstname': worker['firstname'],
                'lastname': worker['lastname'],
                'department': worker['department'],
                'current_lendings': [dict(l) for l in lendings]
            })
            
    except Exception as e:
        print('Fehler beim Abrufen des Mitarbeiters:', str(e))
        return jsonify({'error': 'Interner Serverfehler'}), 500

@bp.route('/scan', methods=['POST'])
@login_required
def scan():
    """Verarbeitet einen Barcode-Scan"""
    try:
        data = request.get_json()
        barcode = data.get('barcode')
        
        if not barcode:
            return jsonify({
                'success': False,
                'message': 'Kein Barcode angegeben'
            }), 400
            
        with Database.get_db() as db:
            # Prüfe zuerst ob es ein Verbrauchsmaterial ist (C-Prefix)
            if barcode.startswith('C'):
                item = db.execute('''
                    SELECT c.*,
                           CASE 
                               WHEN quantity <= 0 THEN 'nicht_verfügbar'
                               WHEN quantity <= min_quantity THEN 'kritisch'
                               WHEN quantity <= min_quantity * 2 THEN 'niedrig'
                               ELSE 'verfügbar'
                           END as status,
                           CASE 
                               WHEN quantity <= 0 THEN 'Nicht verfügbar'
                               WHEN quantity <= min_quantity THEN 'Kritisch'
                               WHEN quantity <= min_quantity * 2 THEN 'Niedrig'
                               ELSE 'Verfügbar'
                           END as status_text
                    FROM consumables c
                    WHERE c.barcode = ? AND c.deleted = 0
                ''', [barcode]).fetchone()
                
                if item:
                    item_dict = dict(item)
                    item_dict['type'] = 'consumable'
                    return jsonify({
                        'success': True,
                        'data': {
                            'type': 'consumable',
                            'name': item['name'],
                            'barcode': item['barcode'],
                            'description': item['description'],
                            'category': item['category'],
                            'location': item['location'],
                            'quantity': item['quantity'],
                            'min_quantity': item['min_quantity'],
                            'status': item['status'],
                            'status_text': item['status_text']
                        }
                    })
            
            # Wenn kein Verbrauchsmaterial, dann prüfe ob es ein Werkzeug ist (T-Prefix)
            elif barcode.startswith('T'):
                item = db.execute('''
                    SELECT t.*, 
                           CASE 
                               WHEN EXISTS (
                                   SELECT 1 FROM lendings l 
                                   WHERE l.tool_barcode = t.barcode 
                                   AND l.returned_at IS NULL
                               ) THEN 'ausgeliehen'
                               WHEN t.status = 'defekt' THEN 'defekt'
                               ELSE 'verfügbar'
                           END as current_status,
                           CASE 
                               WHEN EXISTS (
                                   SELECT 1 FROM lendings l 
                                   WHERE l.tool_barcode = t.barcode 
                                   AND l.returned_at IS NULL
                               ) THEN 'Ausgeliehen'
                               WHEN t.status = 'defekt' THEN 'Defekt'
                               ELSE 'Verfügbar'
                           END as status_text,
                           (
                               SELECT w.firstname || ' ' || w.lastname
                               FROM lendings l
                               JOIN workers w ON l.worker_barcode = w.barcode
                               WHERE l.tool_barcode = t.barcode
                               AND l.returned_at IS NULL
                               LIMIT 1
                           ) as current_worker
                    FROM tools t
                    WHERE t.barcode = ? AND t.deleted = 0
                ''', [barcode]).fetchone()
                
                if item:
                    item_dict = dict(item)
                    item_dict['type'] = 'tool'
                    return jsonify({
                        'success': True,
                        'data': {
                            'type': 'tool',
                            'name': item['name'],
                            'barcode': item['barcode'],
                            'description': item['description'],
                            'category': item['category'],
                            'location': item['location'],
                            'status': item['current_status'],
                            'status_text': item['status_text'],
                            'current_worker': item['current_worker']
                        }
                    })
            
            # Wenn kein Werkzeug, dann prüfe ob es ein Mitarbeiter ist (W-Prefix)
            elif barcode.startswith('W'):
                worker = db.execute('''
                    SELECT w.*,
                           COUNT(DISTINCT l.id) as active_lendings
                    FROM workers w
                    LEFT JOIN lendings l ON w.barcode = l.worker_barcode 
                                      AND l.returned_at IS NULL
                    WHERE w.barcode = ? AND w.deleted = 0
                    GROUP BY w.id
                ''', [barcode]).fetchone()
                
                if worker:
                    return jsonify({
                        'success': True,
                        'data': {
                            'type': 'worker',
                            'name': f"{worker['firstname']} {worker['lastname']}",
                            'barcode': worker['barcode'],
                            'department': worker['department'],
                            'active_lendings': worker['active_lendings']
                        }
                    })
            
            return jsonify({
                'success': False,
                'message': 'Artikel oder Mitarbeiter nicht gefunden'
            }), 404
            
    except Exception as e:
        print(f"Scan-Fehler: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Scannen: {str(e)}'
        }), 500

@bp.route('/quickscan/process_lending', methods=['POST'])
@login_required
def quickscan_process_lending():
    try:
        data = request.json
        item_barcode = data.get('item_barcode')
        worker_barcode = data.get('worker_barcode')
        action = data.get('action')
        item_type = data.get('item_type')
        
        if not all([item_barcode, worker_barcode, action, item_type]):
            return jsonify({
                'success': False,
                'message': 'Fehlende Parameter'
            }), 400
            
        with Database.get_db() as conn:
            if item_type == 'tool':
                if action == 'lend':
                    # Prüfe ob Werkzeug verfügbar ist
                    tool = conn.execute('''
                        SELECT id, name, status FROM tools 
                        WHERE barcode = ? AND deleted = 0
                    ''', [item_barcode]).fetchone()
                    
                    if not tool:
                        return jsonify({
                            'success': False,
                            'message': 'Werkzeug nicht gefunden'
                        }), 404
                        
                    if tool['status'] != 'verfügbar':
                        return jsonify({
                            'success': False,
                            'message': 'Werkzeug ist nicht verfügbar'
                        }), 400
                        
                    # Werkzeug ausleihen
                    conn.execute('''
                        INSERT INTO lendings (tool_barcode, worker_barcode, lent_at)
                        VALUES (?, ?, datetime('now'))
                    ''', [item_barcode, worker_barcode])
                    
                    # Status aktualisieren
                    conn.execute('''
                        UPDATE tools 
                        SET status = 'ausgeliehen'
                        WHERE id = ?
                    ''', [tool['id']])
                    
                    conn.commit()
                    return jsonify({
                        'success': True,
                        'message': f'Werkzeug {tool["name"]} wurde ausgeliehen'
                    })
                    
                elif action == 'return':
                    # Prüfe ob Werkzeug ausgeliehen ist
                    tool = conn.execute('''
                        SELECT id, name, status FROM tools 
                        WHERE barcode = ? AND deleted = 0
                    ''', [item_barcode]).fetchone()
                    
                    if not tool:
                        return jsonify({
                            'success': False,
                            'message': 'Werkzeug nicht gefunden'
                        }), 404
                        
                    if tool['status'] != 'ausgeliehen':
                        return jsonify({
                            'success': False,
                            'message': 'Werkzeug ist nicht ausgeliehen'
                        }), 400
                        
                    # Ausleihe beenden
                    conn.execute('''
                        UPDATE lendings 
                        SET returned_at = datetime('now')
                        WHERE tool_barcode = ? AND returned_at IS NULL
                    ''', [item_barcode])
                    
                    # Status aktualisieren
                    conn.execute('''
                        UPDATE tools 
                        SET status = 'verfügbar'
                        WHERE id = ?
                    ''', [tool['id']])
                    
                    conn.commit()
                    return jsonify({
                        'success': True,
                        'message': f'Werkzeug {tool["name"]} wurde zurückgegeben'
                    })
                    
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Ungültige Aktion'
                    }), 400
                    
            elif item_type == 'consumable':
                if action != 'consume':
                    return jsonify({
                        'success': False,
                        'message': 'Ungültige Aktion für Verbrauchsmaterial'
                    }), 400
                    
                # Prüfe ob Verbrauchsmaterial verfügbar ist
                consumable = conn.execute('''
                    SELECT id, name, quantity FROM consumables 
                    WHERE barcode = ? AND deleted = 0
                ''', [item_barcode]).fetchone()
                
                if not consumable:
                    return jsonify({
                        'success': False,
                        'message': 'Verbrauchsmaterial nicht gefunden'
                    }), 404
                    
                if consumable['quantity'] <= 0:
                    return jsonify({
                        'success': False,
                        'message': 'Verbrauchsmaterial nicht verfügbar'
                    }), 400
                    
                # Verbrauch eintragen
                conn.execute('''
                    INSERT INTO consumable_usages (consumable_barcode, worker_barcode, quantity, used_at)
                    VALUES (?, ?, 1, datetime('now'))
                ''', [item_barcode, worker_barcode])
                
                # Bestand reduzieren
                conn.execute('''
                    UPDATE consumables 
                    SET quantity = quantity - 1
                    WHERE id = ?
                ''', [consumable['id']])
                
                conn.commit()
                return jsonify({
                    'success': True,
                    'message': f'Verbrauchsmaterial {consumable["name"]} wurde entnommen'
                })
                
            else:
                return jsonify({
                    'success': False,
                    'message': 'Ungültiger Artikeltyp'
                }), 400
                
    except Exception as e:
        print(f"Fehler bei der Ausleihe/Rückgabe: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler: {str(e)}'
        }), 500

@bp.route('/inventory/consumables/<barcode>', methods=['GET'])
def get_consumable(barcode):
    """Sucht ein Verbrauchsmaterial anhand des Barcodes"""
    try:
        print(f"Suche Verbrauchsmaterial mit Barcode: {barcode}")
        
        consumable = Database.query('''
            SELECT 
                id,
                barcode,
                name,
                description,
                category,
                location,
                quantity,
                min_quantity,
                CASE 
                    WHEN quantity <= 0 THEN 'nicht_verfügbar'
                    WHEN quantity <= min_quantity THEN 'kritisch'
                    WHEN quantity <= min_quantity * 2 THEN 'niedrig'
                    ELSE 'verfügbar'
                END as status,
                CASE 
                    WHEN quantity <= 0 THEN 'Nicht verfügbar'
                    WHEN quantity <= min_quantity THEN 'Kritisch'
                    WHEN quantity <= min_quantity * 2 THEN 'Niedrig'
                    ELSE 'Verfügbar'
                END as status_text
            FROM consumables 
            WHERE barcode = ? 
            AND deleted = 0
        ''', [barcode], one=True)
        
        if not consumable:
            return jsonify({
                'success': False,
                'message': 'Verbrauchsmaterial nicht gefunden'
            }), 404
            
        consumable_dict = dict(consumable)
        consumable_dict['type'] = 'consumable'
        print(f"Gefundenes Verbrauchsmaterial: {consumable_dict}")
            
        return jsonify({
            'success': True,
            'data': consumable_dict
        })
        
    except Exception as e:
        print(f"Fehler bei Verbrauchsmaterialsuche: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Suche: {str(e)}'
        }), 500

@bp.route('/update_barcode', methods=['POST'])
def update_barcode():
    """Aktualisiert den Barcode eines Werkzeugs, Verbrauchsmaterials oder Mitarbeiters"""
    data = request.get_json()
    old_barcode = data.get('old_barcode')
    new_barcode = data.get('new_barcode')
    item_type = data.get('type')  # 'tool', 'consumable' oder 'worker'
    
    if not all([old_barcode, new_barcode, item_type]):
        return jsonify({'success': False, 'message': 'Fehlende Parameter'})
        
    if item_type not in ['tool', 'consumable', 'worker']:
        return jsonify({'success': False, 'message': 'Ungültiger Typ'})
    
    try:
        db = Database.get_db()
        
        # Prüfen ob der neue Barcode bereits existiert
        exists_count = db.execute("""
            SELECT COUNT(*) as count FROM (
                SELECT barcode FROM tools WHERE barcode = ? AND deleted = 0
                UNION ALL 
                SELECT barcode FROM consumables WHERE barcode = ? AND deleted = 0
                UNION ALL
                SELECT barcode FROM workers WHERE barcode = ? AND deleted = 0
            )
        """, [new_barcode, new_barcode, new_barcode]).fetchone()['count']
        
        if exists_count > 0:
            return jsonify({
                'success': False, 
                'message': 'Der neue Barcode existiert bereits'
            })
        
        try:
            if item_type == 'tool':
                # Werkzeug-Barcode in allen relevanten Tabellen aktualisieren
                
                # 1. Haupttabelle
                db.execute("""
                    UPDATE tools SET barcode = ? WHERE barcode = ? AND deleted = 0
                """, [new_barcode, old_barcode])
                
                # 2. Ausleihhistorie (inkl. aktive Ausleihen)
                db.execute("""
                    UPDATE lendings SET tool_barcode = ? 
                    WHERE tool_barcode = ?
                """, [new_barcode, old_barcode])
                
                # 3. Statusänderungen
                db.execute("""
                    UPDATE tool_status_changes SET tool_barcode = ? 
                    WHERE tool_barcode = ?
                """, [new_barcode, old_barcode])
                
            elif item_type == 'consumable':
                # Verbrauchsmaterial-Barcode in allen relevanten Tabellen aktualisieren
                
                # 1. Haupttabelle
                db.execute("""
                    UPDATE consumables SET barcode = ? WHERE barcode = ? AND deleted = 0
                """, [new_barcode, old_barcode])
                
                # 2. Nutzungshistorie
                db.execute("""
                    UPDATE consumable_usages SET consumable_barcode = ? 
                    WHERE consumable_barcode = ?
                """, [new_barcode, old_barcode])

            else:  # worker
                # Mitarbeiter-Barcode in allen relevanten Tabellen aktualisieren
                
                # 1. Haupttabelle
                db.execute("""
                    UPDATE workers SET barcode = ? WHERE barcode = ? AND deleted = 0
                """, [new_barcode, old_barcode])
                
                # 2. Ausleihhistorie
                db.execute("""
                    UPDATE lendings SET worker_barcode = ? 
                    WHERE worker_barcode = ?
                """, [new_barcode, old_barcode])
                
                # 3. Verbrauchshistorie
                db.execute("""
                    UPDATE consumable_usages SET worker_barcode = ? 
                    WHERE worker_barcode = ?
                """, [new_barcode, old_barcode])
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': 'Barcode erfolgreich aktualisiert'
            })
            
        except Exception as e:
            db.rollback()
            raise e
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Aktualisieren: {str(e)}'
        })

@bp.route('/consumables/<barcode>/forecast', methods=['GET'])
def get_consumable_forecast(barcode):
    """Berechnet eine Bestandsprognose für ein Verbrauchsmaterial"""
    try:
        # Hole die letzten 30 Tage Verbrauchsdaten
        usage_data = Database.query("""
            SELECT 
                DATE(used_at) as date,
                SUM(CASE WHEN worker_barcode != 'admin' THEN ABS(quantity) ELSE 0 END) as daily_usage
            FROM consumable_usages 
            WHERE consumable_barcode = ?
            AND used_at >= DATE('now', '-30 days')
            GROUP BY DATE(used_at)
            ORDER BY date DESC
        """, [barcode])

        if not usage_data:
            return jsonify({
                'success': True,
                'data': {
                    'avg_daily_usage': 0,
                    'max_daily_usage': 0,
                    'days_until_empty': None,
                    'days_until_min': None
                }
            })

        # Berechne durchschnittlichen und maximalen Tagesverbrauch
        total_usage = sum(day['daily_usage'] for day in usage_data)
        max_daily = max(day['daily_usage'] for day in usage_data)
        avg_daily = round(total_usage / 30, 1)  # Durchschnitt über 30 Tage

        # Hole aktuellen Bestand und Mindestbestand
        consumable = Database.query("""
            SELECT quantity, min_quantity 
            FROM consumables 
            WHERE barcode = ? AND deleted = 0
        """, [barcode], one=True)

        if not consumable:
            return jsonify({
                'success': False,
                'message': 'Verbrauchsmaterial nicht gefunden'
            }), 404

        current_stock = consumable['quantity']
        min_stock = consumable['min_quantity']

        # Berechne Prognosen
        days_until_empty = None
        days_until_min = None

        if avg_daily > 0:
            days_until_empty = round(current_stock / avg_daily)
            days_until_min = round((current_stock - min_stock) / avg_daily)

        return jsonify({
            'success': True,
            'data': {
                'avg_daily_usage': avg_daily,
                'max_daily_usage': max_daily,
                'days_until_empty': days_until_empty,
                'days_until_min': days_until_min
            }
        })

    except Exception as e:
        print(f"Fehler bei Bestandsprognose: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Berechnung: {str(e)}'
        }), 500

@bp.route('/notices', methods=['GET'])
def get_notices():
    """Hole alle aktiven Hinweise"""
    notices = Database.query('''
        SELECT * FROM homepage_notices 
        WHERE is_active = 1 
        ORDER BY priority DESC, created_at DESC
    ''')
    return jsonify(notices)

@bp.route('/notices/<int:id>', methods=['GET'])
@admin_required
def get_notice(id):
    """Hole einen bestimmten Hinweis"""
    notice = Database.query('''
        SELECT * FROM homepage_notices 
        WHERE id = ?
    ''', [id], one=True)
    
    if not notice:
        return jsonify({'error': 'Hinweis nicht gefunden'}), 404
    
    return jsonify(notice)

@bp.route('/notices', methods=['POST'])
@admin_required
def create_notice():
    """Erstelle einen neuen Hinweis"""
    data = request.get_json()
    
    try:
        with Database.get_db() as db:
            db.execute('''
                INSERT INTO homepage_notices (title, content, priority, is_active)
                VALUES (?, ?, ?, 1)
            ''', [data.get('title', ''), data['content'], data.get('priority', 50)])
            db.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/notices/<int:id>', methods=['PUT'])
@admin_required
def update_notice(id):
    """Aktualisiere einen Hinweis"""
    data = request.get_json()
    
    try:
        with Database.get_db() as db:
            db.execute('''
                UPDATE homepage_notices 
                SET content = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', [data['content'], data.get('priority', 50), id])
            db.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/notices/<int:id>', methods=['DELETE'])
@admin_required
def delete_notice(id):
    """Lösche einen Hinweis"""
    try:
        with Database.get_db() as db:
            db.execute('DELETE FROM homepage_notices WHERE id = ?', [id])
            db.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500