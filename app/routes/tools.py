from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_login import current_user
from app.services.tool_service import ToolService
from app.utils.decorators import admin_required, login_required, mitarbeiter_required, not_teilnehmer_required
from app.utils.database_helpers import get_categories_from_settings, get_locations_from_settings
from datetime import datetime
import logging

# Blueprint mit URL-Präfix definieren
bp = Blueprint('tools', __name__, url_prefix='/tools')
logger = logging.getLogger(__name__) # Logger für dieses Modul

# ToolService wird bei Bedarf initialisiert
tool_service = None

def get_tool_service():
    """Lazy initialization des ToolService"""
    global tool_service
    if tool_service is None:
        tool_service = ToolService()
    return tool_service

@bp.route('/')
@login_required
@not_teilnehmer_required
def index():
    """Zeigt alle Werkzeuge an"""
    try:
        # Hole alle Werkzeuge über den Service
        tool_service = get_tool_service()
        tools = tool_service.get_all_tools()
        
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
@login_required
def add():
    """Fügt ein neues Werkzeug hinzu"""
    if request.method == 'POST':
        try:
            # Formulardaten sammeln
            tool_data = {
                'name': request.form.get('name'),
                'barcode': request.form.get('barcode'),
                'description': request.form.get('description'),
                'category': request.form.get('category'),
                'location': request.form.get('location'),
                'status': request.form.get('status', 'verfügbar')
            }
            
            # Werkzeug über Service erstellen
            tool_service = get_tool_service()
            success, message, barcode = tool_service.create_tool(tool_data)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('tools.index'))
            else:
                flash(message, 'error')
                # Hole Kategorien und Standorte für das Template
                categories = get_categories_from_settings()
                locations = get_locations_from_settings()
                
                # Gebe die Formulardaten zurück an das Template
                return render_template('tools/add.html',
                                   categories=categories,
                                   locations=locations,
                                   form_data=tool_data)
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Werkzeugs: {str(e)}", exc_info=True)
            flash('Fehler beim Hinzufügen des Werkzeugs', 'error')
            # Hole Kategorien und Standorte für das Template
            categories = get_categories_from_settings()
            locations = get_locations_from_settings()
            
            # Gebe die Formulardaten zurück an das Template
            return render_template('tools/add.html',
                               categories=categories,
                               locations=locations,
                               form_data=request.form.to_dict())
            
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
    try:
        # Hole detaillierte Werkzeug-Informationen über den Service
        tool_service = get_tool_service()
        tool = tool_service.get_tool_details(barcode)
        
        if not tool:
            flash('Werkzeug nicht gefunden', 'error')
            return redirect(url_for('tools.index'))
        
        # Hole Kategorien und Standorte
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('tools/detail.html',
                             tool=tool,
                             categories=categories,
                             locations=locations,
                             lending_history=tool.get('lending_history', []))
                             
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeug-Details: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeug-Details', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/<barcode>/edit', methods=['POST'])
@login_required
def edit(barcode):
    """Bearbeitet ein Werkzeug über Modal"""
    try:
        # Formulardaten sammeln
        tool_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'category': request.form.get('category'),
            'location': request.form.get('location')
        }
        
        # Status nur hinzufügen, wenn er explizit im Formular angegeben wurde
        form_status = request.form.get('status')
        if form_status and form_status.strip():
            tool_data['status'] = form_status
        
        # Barcode nur hinzufügen, wenn er explizit im Formular angegeben wurde
        form_barcode = request.form.get('barcode')
        if form_barcode and form_barcode.strip():
            tool_data['barcode'] = form_barcode
        
        # Werkzeug über Service aktualisieren
        tool_service = get_tool_service()
        success, message, new_barcode = tool_service.update_tool(barcode, tool_data)
        
        # Verwende den neuen Barcode oder den alten, falls new_barcode None ist
        redirect_barcode = new_barcode if new_barcode else barcode
        
        return jsonify({
            'success': success, 
            'message': message, 
            'redirect': url_for('tools.detail', barcode=redirect_barcode)
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': 'Fehler beim Bearbeiten des Werkzeugs'
        }), 500

@bp.route('/<string:barcode>/status', methods=['POST'])
@login_required
def change_status(barcode):
    """Ändert den Status eines Werkzeugs"""
    try:
        new_status = request.form.get('status')
        
        # Status über Service ändern
        tool_service = get_tool_service()
        success, message = tool_service.change_tool_status(barcode, new_status)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
        
    except Exception as e:
        logger.error(f"Fehler beim Ändern des Status: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Ändern des Status'}), 500

@bp.route('/<string:barcode>/delete', methods=['POST'])
@login_required
@admin_required
def delete(barcode):
    """Löscht ein Werkzeug"""
    try:
        permanent = request.form.get('permanent', 'false').lower() == 'true'
        
        # Werkzeug über Service löschen
        tool_service = get_tool_service()
        success, message = tool_service.delete_tool(barcode, permanent)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
            
        return redirect(url_for('tools.index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs: {str(e)}", exc_info=True)
        flash('Fehler beim Löschen des Werkzeugs', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/search')
@login_required
def search():
    """Sucht nach Werkzeugen"""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return redirect(url_for('tools.index'))
        
        # Suche über Service
        tool_service = get_tool_service()
        tools = tool_service.search_tools(query)
        
        # Hole Kategorien und Standorte
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           search_query=query,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler bei der Werkzeug-Suche: {str(e)}", exc_info=True)
        flash('Fehler bei der Suche', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/category/<category>')
@login_required
def by_category(category):
    """Zeigt Werkzeuge nach Kategorie"""
    try:
        # Werkzeuge nach Kategorie über Service
        tool_service = get_tool_service()
        tools = tool_service.get_tools_by_category(category)
        
        # Hole Kategorien und Standorte
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           selected_category=category,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge nach Kategorie: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/location/<location>')
@login_required
def by_location(location):
    """Zeigt Werkzeuge nach Standort"""
    try:
        # Werkzeuge nach Standort über Service
        tool_service = get_tool_service()
        tools = tool_service.get_tools_by_location(location)
        
        # Hole Kategorien und Standorte
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           selected_location=location,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge nach Standort: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/status/<status>')
@login_required
def by_status(status):
    """Zeigt Werkzeuge nach Status"""
    try:
        # Werkzeuge nach Status über Service
        tool_service = get_tool_service()
        tools = tool_service.get_tools_by_status(status)
        
        # Hole Kategorien und Standorte
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        
        return render_template('tools/index.html',
                           tools=tools,
                           categories=categories,
                           locations=locations,
                           selected_status=status,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge nach Status: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/statistics')
@login_required
@admin_required
def statistics():
    """Zeigt Werkzeug-Statistiken"""
    try:
        # Statistiken über Service
        tool_service = get_tool_service()
        stats = tool_service.get_tool_statistics()
        
        return render_template('tools/statistics.html',
                           stats=stats,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeug-Statistiken: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Statistiken', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/export')
@login_required
@admin_required
def export():
    """Exportiert Werkzeuge als CSV"""
    try:
        from flask import Response
        
        # CSV über Service exportieren
        tool_service = get_tool_service()
        csv_data = tool_service.export_tools()
        
        if not csv_data:
            flash('Fehler beim Export', 'error')
            return redirect(url_for('tools.index'))
        
        # CSV-Datei zum Download anbieten
        response = Response(csv_data, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=werkzeuge_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        logger.error(f"Fehler beim Export der Werkzeuge: {str(e)}", exc_info=True)
        flash('Fehler beim Export', 'error')
        return redirect(url_for('tools.index'))