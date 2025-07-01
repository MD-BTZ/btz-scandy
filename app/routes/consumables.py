from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from app.models.mongodb_database import mongodb
from app.utils.decorators import admin_required, login_required, mitarbeiter_required
from app.utils.database_helpers import get_categories_from_settings, get_locations_from_settings
from datetime import datetime, timedelta
import logging

# Blueprint mit URL-Präfix definieren
bp = Blueprint('consumables', __name__, url_prefix='/consumables')
logger = logging.getLogger(__name__)

@bp.route('/')
@login_required
def index():
    """Zeigt alle Verbrauchsmaterialien an"""
    try:
        consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
        
        # Hole Kategorien und Standorte aus den Settings
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('consumables/index.html',
                           consumables=consumables,
                           categories=categories,
                           locations=locations,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Verbrauchsmaterialien: {str(e)}", exc_info=True)
        return render_template('consumables/index.html',
                           consumables=[],
                           categories=[],
                           locations=[],
                           is_admin=current_user.is_admin)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Fügt ein neues Verbrauchsmaterial hinzu"""
    if request.method == 'POST':
        try:
            # Formulardaten abrufen
            name = request.form.get('name')
            barcode = request.form.get('barcode')
            category = request.form.get('category')
            location = request.form.get('location')
            quantity = int(request.form.get('quantity', 0))
            min_quantity = int(request.form.get('min_quantity', 0))
            description = request.form.get('description', '')
            
            # Prüfe ob Barcode bereits existiert
            existing_tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
            existing_consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
            existing_worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
            
            if existing_tool or existing_consumable or existing_worker:
                flash('Barcode bereits vergeben', 'error')
                categories = get_categories_from_settings()
                locations = get_locations_from_settings()
                return render_template('consumables/add.html', 
                                   categories=categories, 
                                   locations=locations)
            
            # Neues Verbrauchsmaterial erstellen
            consumable_data = {
                'name': name,
                'barcode': barcode,
                'category': category,
                'location': location,
                'quantity': quantity,
                'min_quantity': min_quantity,
                'description': description,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'deleted': False
            }
            
            mongodb.insert_one('consumables', consumable_data)
            flash('Verbrauchsmaterial wurde erfolgreich hinzugefügt', 'success')
            return redirect(url_for('consumables.index'))
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Verbrauchsmaterials: {str(e)}", exc_info=True)
            flash('Fehler beim Hinzufügen des Verbrauchsmaterials', 'error')
    
    # GET-Anfrage: Formular anzeigen
    categories = get_categories_from_settings()
    locations = get_locations_from_settings()
    return render_template('consumables/add.html', 
                       categories=categories, 
                       locations=locations)

@bp.route('/<string:barcode>', methods=['GET', 'POST'])
@login_required
def detail(barcode):
    """Zeigt die Details eines Verbrauchsmaterials und verarbeitet Updates"""
    if request.method == 'POST':
        try:
            data = request.form
            new_barcode = data.get('barcode')
            
            # Prüfe ob das Verbrauchsmaterial existiert
            current = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
            
            if not current:
                return jsonify({
                    'success': False,
                    'message': 'Verbrauchsmaterial nicht gefunden'
                }), 404
            
            # Prüfe ob der neue Barcode bereits existiert (wenn er sich geändert hat)
            if new_barcode != barcode:
                existing_tool = mongodb.find_one('tools', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                existing_consumable = mongodb.find_one('consumables', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                existing_worker = mongodb.find_one('workers', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                
                if existing_tool or existing_consumable or existing_worker:
                    return jsonify({
                        'success': False,
                        'message': f'Der Barcode "{new_barcode}" existiert bereits'
                    }), 400
            
            # Update durchführen
            update_data = {
                'name': data.get('name'),
                'description': data.get('description'),
                'category': data.get('category'),
                'location': data.get('location'),
                'quantity': int(data.get('quantity', current['quantity'])),
                'min_quantity': int(data.get('min_quantity', current['min_quantity'])),
                'barcode': new_barcode,
                'modified_at': datetime.now()
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
            
            return jsonify({'success': True, 'redirect': url_for('consumables.detail', barcode=new_barcode)})
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Verbrauchsmaterials: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET-Methode: Details anzeigen
    consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
    
    if not consumable:
        flash('Verbrauchsmaterial nicht gefunden', 'error')
        return redirect(url_for('consumables.index'))
    
    # Hole vordefinierte Kategorien und Standorte
    categories = get_categories_from_settings()
    locations = get_locations_from_settings()
    
    # Hole Bestandsänderungen
    usages = mongodb.find('consumable_usages', {'consumable_barcode': barcode})
    usages = list(usages)
    
    # Sortiere nach Datum (neueste zuerst) - sicherer Vergleich
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
    
    # Erstelle Verlaufsliste
    history = []
    for usage in usages:
        worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
        worker_name = f"{worker['firstname']} {worker['lastname']}" if worker else "Admin"
        
        action = "Entnommen" if usage['quantity'] < 0 else "Hinzugefügt"
        quantity = abs(usage['quantity'])
        
        # Stelle sicher, dass das Datum korrekt formatiert wird
        action_date = usage['used_at']
        if isinstance(action_date, str):
            try:
                action_date = datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                action_date = datetime.now()
        
        history.append({
            'action_type': 'Bestandsänderung',
            'action_date': action_date,
            'worker': worker_name,
            'action': f"{action}: {quantity} Stück",
            'reason': None
        })
    
    return render_template('consumables/details.html',
                         consumable=consumable,
                         categories=categories,
                         locations=locations,
                         history=history)

@bp.route('/<barcode>/adjust-stock', methods=['POST'])
@login_required
def adjust_stock(barcode):
    """Passt den Bestand eines Verbrauchsmaterials an"""
    try:
        # Versuche zuerst JSON-Daten zu lesen, falls das fehlschlägt, verwende Form-Daten
        try:
            data = request.get_json()
        except:
            # Fallback auf Form-Daten
            data = request.form.to_dict()
        
        quantity_change = data.get('quantity')
        if quantity_change is not None:
            try:
                quantity_change = int(quantity_change)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': 'Ungültige Menge'}), 400
        else:
            return jsonify({'success': False, 'message': 'Menge ist erforderlich'}), 400
            
        reason = data.get('reason', '')
        
        # Hole aktuelles Verbrauchsmaterial
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404
        
        # Berechne neue Menge
        new_quantity = consumable.get('quantity', 0) + quantity_change
        if new_quantity < 0:
            return jsonify({'success': False, 'message': 'Bestand kann nicht negativ sein'}), 400
        
        # Aktualisiere Bestand
        mongodb.update_one('consumables', 
                          {'barcode': barcode}, 
                          {'$set': {'quantity': new_quantity, 'modified_at': datetime.now()}})
        
        # Protokolliere Bestandsänderung
        usage_data = {
            'consumable_barcode': barcode,
            'worker_barcode': getattr(current_user, 'username', 'admin'),
            'quantity': quantity_change,
            'used_at': datetime.now(),
            'reason': reason
        }
        mongodb.insert_one('consumable_usages', usage_data)
        
        return jsonify({
            'success': True, 
            'message': 'Bestand erfolgreich angepasst',
            'new_quantity': new_quantity
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Anpassen des Bestands: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Anpassen des Bestands'}), 500

@bp.route('/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_by_barcode(barcode):
    """Löscht ein Verbrauchsmaterial (Soft-Delete)"""
    try:
        # Prüfe ob das Verbrauchsmaterial existiert
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404
        
        # Führe Soft-Delete durch
        mongodb.update_one('consumables', 
                          {'barcode': barcode}, 
                          {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
        
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial erfolgreich gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Löschen'}), 500

@bp.route('/<barcode>/forecast')
@login_required
def forecast(barcode):
    """Zeigt eine Bestandsprognose für ein Verbrauchsmaterial"""
    try:
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404
        
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
        logger.error(f"Fehler bei der Bestandsprognose: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler bei der Berechnung'}), 500
