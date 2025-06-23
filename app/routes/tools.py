from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import current_user
from app.models.mongodb_models import MongoDBTool
from app.models.mongodb_database import mongodb
from app.utils.decorators import admin_required, login_required, mitarbeiter_required
from app.utils.database_helpers import get_categories_from_settings, get_locations_from_settings
from datetime import datetime
import logging

# Blueprint mit URL-Präfix definieren
bp = Blueprint('tools', __name__, url_prefix='/tools')
logger = logging.getLogger(__name__) # Logger für dieses Modul

@bp.route('/')
@login_required
def index():
    """Zeigt alle Werkzeuge an"""
    try:
        # Hole alle aktiven Werkzeuge
        tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
        
        # Hole Kategorien und Standorte aus den Settings
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge: {str(e)}", exc_info=True)
        return render_template('tools/index.html',
                           tools=[],
                           categories=[],
                           locations=[],
                           is_admin=current_user.is_admin)

@bp.route('/add', methods=['GET', 'POST'])
@mitarbeiter_required
def add():
    """Fügt ein neues Werkzeug hinzu"""
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            barcode = request.form.get('barcode')
            description = request.form.get('description')
            category = request.form.get('category')
            location = request.form.get('location')
            status = request.form.get('status', 'verfügbar')
            
            if not name or not barcode:
                flash('Name und Barcode sind erforderlich', 'error')
                return redirect(url_for('tools.add'))
            
            # Prüfe ob der Barcode bereits existiert
            existing_tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
            
            if existing_tool:
                flash('Dieser Barcode existiert bereits', 'error')
                # Hole Kategorien und Standorte für das Template
                categories = get_categories_from_settings()
                locations = get_locations_from_settings()
                
                # Gebe die Formulardaten zurück an das Template
                return render_template('tools/add.html',
                                   categories=categories,
                                   locations=locations,
                                   form_data={
                                       'name': name,
                                       'barcode': barcode,
                                       'description': description,
                                       'category': category,
                                       'location': location,
                                       'status': status
                                   })
            
            # Wenn Barcode eindeutig ist, füge das Werkzeug hinzu
            tool_data = {
                'name': name,
                'barcode': barcode,
                'description': description,
                'category': category,
                'location': location,
                'status': status,
                'created_at': datetime.now(),
                'modified_at': datetime.now(),
                'deleted': False
            }
            
            mongodb.insert_one('tools', tool_data)
            
            flash('Werkzeug erfolgreich hinzugefügt', 'success')
            return redirect(url_for('tools.index'))
            
        except Exception as e:
            print(f"Fehler beim Hinzufügen des Werkzeugs: {str(e)}")
            flash('Fehler beim Hinzufügen des Werkzeugs', 'error')
            # Hole Kategorien und Standorte für das Template
            categories = get_categories_from_settings()
            locations = get_locations_from_settings()
            
            # Gebe die Formulardaten zurück an das Template
            return render_template('tools/add.html',
                               categories=categories,
                               locations=locations,
                               form_data={
                                   'name': name,
                                   'barcode': barcode,
                                   'description': description,
                                   'category': category,
                                   'location': location,
                                   'status': status
                               })
            
    else:
        # GET: Zeige Formular
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('tools/add.html',
                           categories=categories,
                           locations=locations)

@bp.route('/<barcode>')
@login_required
def detail(barcode):
    """Zeigt die Details eines Werkzeugs"""
    tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
    
    if not tool:
        flash('Werkzeug nicht gefunden', 'error')
        return redirect(url_for('tools.index'))
    
    # Hole aktuelle Ausleihe
    current_lending = mongodb.find_one('lendings', {
        'tool_barcode': barcode,
        'returned_at': None
    })
    
    if current_lending:
        worker = mongodb.find_one('workers', {'barcode': current_lending['worker_barcode']})
        if worker:
            tool['current_borrower'] = f"{worker['firstname']} {worker['lastname']}"
            # Stelle sicher, dass das Datum korrekt formatiert wird
            lending_date = current_lending['lent_at']
            if isinstance(lending_date, str):
                try:
                    lending_date = datetime.strptime(lending_date, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending_date = datetime.now()
            tool['lending_date'] = lending_date
    
    # Hole Kategorien und Standorte
    categories = get_categories_from_settings()
    locations = get_locations_from_settings()
    
    # Hole Verlauf aus Ausleihen
    lendings = mongodb.find('lendings', {'tool_barcode': barcode})
    lendings = list(lendings)
    
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
    
    return render_template('tools/detail.html',
                         tool=tool,
                         categories=categories,
                         locations=locations,
                         lending_history=history)

@bp.route('/<barcode>/edit', methods=['GET', 'POST'])
@mitarbeiter_required
def edit(barcode):
    """Bearbeitet ein Werkzeug"""
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            category = request.form.get('category')
            location = request.form.get('location')
            new_barcode = request.form.get('barcode')
            new_status = request.form.get('status')
            
            if not name:
                flash('Name ist erforderlich', 'error')
                return redirect(url_for('tools.edit', barcode=barcode))
            
            # Validiere den Status
            if new_status not in ['verfügbar', 'defekt']:
                flash('Ungültiger Status', 'error')
                return redirect(url_for('tools.edit', barcode=barcode))
            
            # Hole den aktuellen Status des Werkzeugs
            current_tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
            
            if not current_tool:
                flash('Werkzeug nicht gefunden', 'error')
                return redirect(url_for('tools.index'))
            
            # Prüfe ob das Werkzeug ausgeliehen ist
            current_lending = mongodb.find_one('lendings', {
                'tool_barcode': barcode,
                'returned_at': None
            })
            
            if current_lending and new_status == 'defekt':
                flash('Ein ausgeliehenes Werkzeug kann nicht als defekt markiert werden', 'error')
                return redirect(url_for('tools.edit', barcode=barcode))
            
            # Aktualisiere das Werkzeug
            update_data = {
                'name': name,
                'description': description,
                'category': category,
                'location': location,
                'status': new_status,
                'modified_at': datetime.now()
            }
            
            # Wenn der Barcode geändert wurde, prüfe ob der neue Barcode bereits existiert
            if new_barcode and new_barcode != barcode:
                existing_tool = mongodb.find_one('tools', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                if existing_tool:
                    flash('Dieser Barcode existiert bereits', 'error')
                    return redirect(url_for('tools.edit', barcode=barcode))
                update_data['barcode'] = new_barcode
            
            mongodb.update_one('tools', {'barcode': barcode}, {'$set': update_data})
            
            flash('Werkzeug erfolgreich aktualisiert', 'success')
            return redirect(url_for('tools.detail', barcode=new_barcode if new_barcode else barcode))
            
        else:
            # GET: Zeige Bearbeitungsformular
            tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
            
            if not tool:
                flash('Werkzeug nicht gefunden', 'error')
                return redirect(url_for('tools.index'))
            
            # Hole Kategorien und Standorte
            categories = get_categories_from_settings()
            locations = get_locations_from_settings()
            
            return render_template('tools/edit.html',
                               tool=tool,
                               categories=categories,
                               locations=locations)
                               
    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten des Werkzeugs: {str(e)}", exc_info=True)
        flash('Fehler beim Bearbeiten des Werkzeugs', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/<string:barcode>/status', methods=['POST'])
@login_required
def change_status(barcode):
    """Ändert den Status eines Werkzeugs"""
    try:
        new_status = request.form.get('status')
        
        if new_status not in ['verfügbar', 'defekt']:
            return jsonify({'success': False, 'message': 'Ungültiger Status'}), 400
        
        # Prüfe ob das Werkzeug ausgeliehen ist
        current_lending = mongodb.find_one('lendings', {
            'tool_barcode': barcode,
            'returned_at': None
        })
        
        if current_lending and new_status == 'defekt':
            return jsonify({
                'success': False, 
                'message': 'Ein ausgeliehenes Werkzeug kann nicht als defekt markiert werden'
            }), 400
        
        # Aktualisiere den Status
        mongodb.update_one('tools', 
                          {'barcode': barcode}, 
                          {'$set': {'status': new_status, 'modified_at': datetime.now()}})
        
        return jsonify({'success': True, 'message': 'Status erfolgreich geändert'})
        
    except Exception as e:
        logger.error(f"Fehler beim Ändern des Status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Ändern des Status'}), 500

# Weitere Tool-Routen...