from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models.mongodb_database import mongodb
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('mobile', __name__, url_prefix='/mobile')

@bp.route('/quickscan')
def quickscan():
    """Mobile Quickscan-App"""
    return render_template('mobile/quickscan.html')

@bp.route('/login', methods=['POST'])
def login():
    """Mobile Login für Quickscan-App"""
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Benutzername und Passwort sind erforderlich', 'error')
            return redirect(url_for('mobile.quickscan'))
        
        # Benutzer in der Datenbank suchen
        user_data = mongodb.find_one('users', {'username': username})
        
        if not user_data:
            flash('Ungültige Anmeldedaten', 'error')
            return redirect(url_for('mobile.quickscan'))
        
        # Passwort überprüfen
        from werkzeug.security import check_password_hash
        if not check_password_hash(user_data.get('password_hash', ''), password):
            flash('Ungültige Anmeldedaten', 'error')
            return redirect(url_for('mobile.quickscan'))
        
        # User-Objekt erstellen und anmelden
        from app.models.user import User as AppUser
        user = AppUser(user_data)
        
        login_user(user, remember=True)
        
        flash('Erfolgreich angemeldet', 'success')
        return redirect(url_for('mobile.quickscan'))
        
    except Exception as e:
        logger.error(f"Mobile Login-Fehler: {str(e)}")
        flash('Anmeldung fehlgeschlagen', 'error')
        return redirect(url_for('mobile.quickscan'))

@bp.route('/logout')
@login_required
def logout():
    """Mobile Logout"""
    logout_user()
    flash('Erfolgreich abgemeldet', 'success')
    return redirect(url_for('mobile.quickscan'))

@bp.route('/scan', methods=['POST'])
@login_required
def scan_barcode():
    """Barcode-Scan API für mobile App"""
    try:
        barcode = request.json.get('barcode')
        
        if not barcode:
            return jsonify({'success': False, 'error': 'Kein Barcode übermittelt'}), 400
        
        # Suche nach dem Barcode in verschiedenen Sammlungen
        result = None
        item_type = None
        
        # Suche in Tools
        tool = mongodb.find_one('tools', {'barcode': barcode})
        if tool:
            result = tool
            item_type = 'tool'
        
        # Suche in Consumables
        if not result:
            consumable = mongodb.find_one('consumables', {'barcode': barcode})
            if consumable:
                result = consumable
                item_type = 'consumable'
        
        # Suche in Workers
        if not result:
            worker = mongodb.find_one('workers', {'barcode': barcode})
            if worker:
                result = worker
                item_type = 'worker'
        
        if not result:
            return jsonify({
                'success': False, 
                'error': 'Barcode nicht gefunden',
                'barcode': barcode
            }), 404
        
        # Aktuelle Ausleihe prüfen
        lending = mongodb.find_one('lendings', {
            'item_barcode': barcode,
            'return_date': None
        })
        
        # Ergebnis formatieren
        response_data = {
            'success': True,
            'item': {
                'id': str(result['_id']),
                'name': result.get('name', result.get('title', 'Unbekannt')),
                'barcode': barcode,
                'type': item_type,
                'description': result.get('description', ''),
                'status': result.get('status', 'verfügbar')
            },
            'lending': None
        }
        
        if lending:
            response_data['lending'] = {
                'id': str(lending['_id']),
                'worker_name': lending.get('worker_name', 'Unbekannt'),
                'action_date': lending.get('action_date', ''),
                'return_date': lending.get('return_date')
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Barcode-Scan-Fehler: {str(e)}")
        return jsonify({'success': False, 'error': 'Interner Server-Fehler'}), 500

@bp.route('/lend', methods=['POST'])
@login_required
def lend_item():
    """Item ausleihen/rückgeben"""
    try:
        data = request.json
        barcode = data.get('barcode')
        action = data.get('action')  # 'lend' oder 'return'
        worker_name = data.get('worker_name', current_user.username)
        
        if not barcode or not action:
            return jsonify({'success': False, 'error': 'Ungültige Parameter'}), 400
        
        if action == 'lend':
            # Prüfe ob Item bereits ausgeliehen ist
            existing_lending = mongodb.find_one('lendings', {
                'item_barcode': barcode,
                'return_date': None
            })
            
            if existing_lending:
                return jsonify({
                    'success': False, 
                    'error': 'Item ist bereits ausgeliehen',
                    'lending': {
                        'worker_name': existing_lending.get('worker_name'),
                        'action_date': existing_lending.get('action_date')
                    }
                }), 409
            
            # Neue Ausleihe erstellen
            from datetime import datetime
            lending_data = {
                'item_barcode': barcode,
                'worker_name': worker_name,
                'action_date': datetime.now(),
                'return_date': None,
                'created_by': current_user.username
            }
            
            mongodb.insert('lendings', lending_data)
            
            return jsonify({
                'success': True,
                'message': 'Item erfolgreich ausgeliehen',
                'lending': lending_data
            })
            
        elif action == 'return':
            # Ausleihe beenden
            lending = mongodb.find_one('lendings', {
                'item_barcode': barcode,
                'return_date': None
            })
            
            if not lending:
                return jsonify({
                    'success': False, 
                    'error': 'Keine aktive Ausleihe gefunden'
                }), 404
            
            # Rückgabe-Datum setzen
            from datetime import datetime
            mongodb.update('lendings', 
                         {'_id': lending['_id']}, 
                         {'return_date': datetime.now()})
            
            return jsonify({
                'success': True,
                'message': 'Item erfolgreich zurückgegeben'
            })
        
        else:
            return jsonify({'success': False, 'error': 'Ungültige Aktion'}), 400
            
    except Exception as e:
        logger.error(f"Lending-Fehler: {str(e)}")
        return jsonify({'success': False, 'error': 'Interner Server-Fehler'}), 500 