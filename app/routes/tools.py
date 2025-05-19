from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import current_user
from app.models.database import Database
from app.utils.decorators import admin_required, login_required, mitarbeiter_required
from datetime import datetime
import logging

# Blueprint mit URL-Präfix definieren
bp = Blueprint('tools', __name__, url_prefix='/tools')
logger = logging.getLogger(__name__) # Logger für dieses Modul

@bp.route('/')
@login_required
def index():
    """Zeigt alle aktiven Werkzeuge"""
    logger.debug(f"[ROUTE] tools.index: Entered route. User: {current_user.id}, Role: {current_user.role}")
    try:
        with Database.get_db() as conn:
            # Hole alle nicht-gelöschten Werkzeuge
            tools = conn.execute('''
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
                WHERE t.deleted = 0
                ORDER BY t.name
            ''').fetchall()
            
            # Hole vordefinierte Kategorien aus den Einstellungen
            categories = conn.execute('''
                SELECT name 
                FROM categories 
                WHERE deleted = 0 
                ORDER BY name
            ''').fetchall()
            
            # Hole vordefinierte Standorte aus den Einstellungen
            locations = conn.execute('''
                SELECT name 
                FROM locations 
                WHERE deleted = 0 
                ORDER BY name
            ''').fetchall()
            
            logger.debug(f"[ROUTE] tools.index: Tools: {tools}")
            
            print(f"[DEBUG] User Info in tools.index: ID={current_user.id}, Role={current_user.role}, IsAdmin={current_user.is_admin}, IsAuthenticated={current_user.is_authenticated}")
            
            return render_template('tools/index.html',
                               tools=tools,
                               categories=[c['name'] for c in categories],
                               locations=[l['name'] for l in locations],
                               is_admin=current_user.is_admin)
                               
    except Exception as e:
        logger.error(f"Fehler beim Laden der Werkzeuge: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('main.index'))

@bp.route('/add', methods=['GET', 'POST'])
@mitarbeiter_required
def add():
    """Fügt ein neues Werkzeug hinzu"""
    if request.method == 'POST':
        name = request.form.get('name')
        barcode = request.form.get('barcode')
        description = request.form.get('description')
        category = request.form.get('category')
        location = request.form.get('location')
        
        try:
            # Prüfe ob der Barcode bereits existiert
            exists_count = Database.query('''
                SELECT COUNT(*) as count FROM (
                    SELECT barcode FROM tools WHERE barcode = ? AND deleted = 0
                    UNION ALL 
                    SELECT barcode FROM consumables WHERE barcode = ? AND deleted = 0
                    UNION ALL
                    SELECT barcode FROM workers WHERE barcode = ? AND deleted = 0
                )
            ''', [barcode, barcode, barcode], one=True)['count']
            
            if exists_count > 0:
                flash('Dieser Barcode existiert bereits', 'error')
                # Hole Kategorien und Standorte für das Template
                categories = Database.query('''
                    SELECT name FROM categories 
                    WHERE deleted = 0 
                    ORDER BY name
                ''')
                
                locations = Database.query('''
                    SELECT name FROM locations 
                    WHERE deleted = 0 
                    ORDER BY name
                ''')
                
                # Gebe die Formulardaten zurück an das Template
                return render_template('tools/add.html',
                                   categories=[c['name'] for c in categories],
                                   locations=[l['name'] for l in locations],
                                   form_data={
                                       'name': name,
                                       'barcode': barcode,
                                       'description': description,
                                       'category': category,
                                       'location': location
                                   })
            
            # Wenn Barcode eindeutig ist, füge das Werkzeug hinzu
            Database.query('''
                INSERT INTO tools 
                (name, barcode, description, category, location, status)
                VALUES (?, ?, ?, ?, ?, 'verfügbar')
            ''', [name, barcode, description, category, location])
            
            flash('Werkzeug erfolgreich hinzugefügt', 'success')
            return redirect(url_for('tools.index'))
            
        except Exception as e:
            print(f"Fehler beim Hinzufügen des Werkzeugs: {str(e)}")
            flash('Fehler beim Hinzufügen des Werkzeugs', 'error')
            # Hole Kategorien und Standorte für das Template
            categories = Database.query('''
                SELECT name FROM categories 
                WHERE deleted = 0 
                ORDER BY name
            ''')
            
            locations = Database.query('''
                SELECT name FROM locations 
                WHERE deleted = 0 
                ORDER BY name
            ''')
            
            # Gebe die Formulardaten zurück an das Template
            return render_template('tools/add.html',
                               categories=[c['name'] for c in categories],
                               locations=[l['name'] for l in locations],
                               form_data={
                                   'name': name,
                                   'barcode': barcode,
                                   'description': description,
                                   'category': category,
                                   'location': location
                               })
            
    else:
        # GET: Zeige Formular
        categories = Database.query('''
            SELECT name FROM categories 
            WHERE deleted = 0 
            ORDER BY name
        ''')
        
        locations = Database.query('''
            SELECT name FROM locations 
            WHERE deleted = 0 
            ORDER BY name
        ''')
        
        return render_template('tools/add.html',
                           categories=[c['name'] for c in categories],
                           locations=[l['name'] for l in locations])

@bp.route('/<barcode>')
@login_required
def detail(barcode):
    """Zeigt die Details eines Werkzeugs"""
    tool = Database.query('''
        SELECT t.*, 
               l.worker_barcode as lent_to,
               l.lent_at as lending_date,
               w.firstname || ' ' || w.lastname as current_borrower
        FROM tools t
        LEFT JOIN (
            SELECT * FROM lendings 
            WHERE returned_at IS NULL
        ) l ON t.barcode = l.tool_barcode
        LEFT JOIN workers w ON l.worker_barcode = w.barcode
        WHERE t.barcode = ? AND t.deleted = 0
    ''', [barcode], one=True)
    
    if not tool:
        flash('Werkzeug nicht gefunden', 'error')
        return redirect(url_for('tools.index'))
    
    # Hole Kategorien und Standorte
    categories = Database.get_categories()
    locations = Database.get_locations()
    
    # Hole kombinierten Verlauf aus Ausleihen und Statusänderungen
    history = Database.query('''
        SELECT 
            'Ausleihe/Rückgabe' as action_type,
            datetime(l.lent_at) as action_date,
            w.firstname || ' ' || w.lastname as worker,
            CASE 
                WHEN l.returned_at IS NULL THEN 'Ausgeliehen'
                ELSE 'Zurückgegeben'
            END as action,
            NULL as reason
        FROM lendings l
        LEFT JOIN workers w ON l.worker_barcode = w.barcode
        WHERE l.tool_barcode = ?
        UNION ALL
        SELECT 
            'Statusänderung' as action_type,
            datetime(modified_at) as action_date,
            NULL as worker,
            status as action,
            NULL as reason
        FROM tools
        WHERE barcode = ? AND status != 'verfügbar'
        ORDER BY action_date DESC
    ''', [barcode, barcode])
    
    return render_template('tools/details.html',
                         tool=tool,
                         categories=[c['name'] for c in categories],
                         locations=[l['name'] for l in locations],
                         history=history)

@bp.route('/<int:id>/update', methods=['GET', 'POST'])
@mitarbeiter_required
def update(id):
    """Aktualisiert ein Werkzeug"""
    try:
        if request.method == 'GET':
            # Hole Werkzeug für das Formular
            tool = Database.query('''
                SELECT * FROM tools 
                WHERE id = ? AND deleted = 0
            ''', [id], one=True)
            
            if tool is None:
                flash('Werkzeug nicht gefunden', 'error')
                return redirect(url_for('tools.index'))
                
            return render_template('tools/edit.html', tool=tool)
            
        # POST-Anfrage
        data = request.form
        
        Database.query('''
            UPDATE tools 
            SET name = ?,
                barcode = ?,
                category = ?,
                location = ?,
                description = ?,
                modified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', [
            data.get('name'),
            data.get('barcode'),
            data.get('category'),
            data.get('location'),
            data.get('description'),
            id
        ])
        
        flash('Werkzeug erfolgreich aktualisiert', 'success')
        return redirect(url_for('tools.detail', barcode=data.get('barcode')))
        
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Werkzeugs: {str(e)}")
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/<string:barcode>/status', methods=['POST'])
@login_required
def change_status(barcode):
    """Ändert den Status eines Werkzeugs"""
    try:
        new_status = request.form.get('status')
        if not new_status:
            flash('Kein Status angegeben', 'error')
            return redirect(url_for('tools.detail', barcode=barcode))
            
        with Database.get_db() as conn:
            # Prüfe ob das Werkzeug existiert
            tool = conn.execute('''
                SELECT * FROM tools 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode]).fetchone()
            
            if not tool:
                flash('Werkzeug nicht gefunden', 'error')
                return redirect(url_for('tools.index'))
                
            # Aktualisiere den Status
            conn.execute('''
                UPDATE tools 
                SET status = ?,
                    sync_status = 'pending'
                WHERE barcode = ?
            ''', [new_status, barcode])
            
            # Protokolliere die Änderung
            conn.execute('''
                INSERT INTO tool_status_changes 
                (tool_barcode, old_status, new_status, changed_by, changed_at)
                VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            ''', [barcode, tool['status'], new_status, session.get('username', 'unknown')])
            
            conn.commit()
            
            flash('Status erfolgreich aktualisiert', 'success')
            return redirect(url_for('tools.detail', barcode=barcode))
            
    except Exception as e:
        print(f"Fehler beim Status-Update: {str(e)}")
        flash('Fehler beim Aktualisieren des Status', 'error')
        return redirect(url_for('tools.detail', barcode=barcode))

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
            new_barcode = request.form.get('barcode')  # Neuer Barcode aus dem Formular
            
            if not name:
                flash('Name ist erforderlich', 'error')
                return redirect(url_for('tools.edit', barcode=barcode))
                
            with Database.get_db() as conn:
                # Aktualisiere das Werkzeug
                conn.execute('''
                    UPDATE tools 
                    SET name = ?,
                        description = ?,
                        category = ?,
                        location = ?,
                        barcode = ?,
                        sync_status = 'pending'
                    WHERE barcode = ?
                ''', [name, description, category, location, new_barcode, barcode])
                
                conn.commit()
                
                flash('Werkzeug erfolgreich aktualisiert', 'success')
                return redirect(url_for('tools.detail', barcode=new_barcode))  # Weiterleitung mit neuem Barcode
                
        else:
            # GET: Zeige Bearbeitungsformular
            tool = Database.query('''
                SELECT * FROM tools 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode], one=True)
            
            if not tool:
                flash('Werkzeug nicht gefunden', 'error')
                return redirect(url_for('tools.index'))
                
            # Hole vordefinierte Kategorien und Standorte
            categories = Database.query('''
                SELECT name FROM categories 
                WHERE deleted = 0 
                ORDER BY name
            ''')
            
            locations = Database.query('''
                SELECT name FROM locations 
                WHERE deleted = 0 
                ORDER BY name
            ''')
            
            return render_template('tools/edit.html',
                               tool=tool,
                               categories=[c['name'] for c in categories],
                               locations=[l['name'] for l in locations])
                               
    except Exception as e:
        print(f"Fehler beim Bearbeiten des Werkzeugs: {str(e)}")
        flash('Fehler beim Bearbeiten des Werkzeugs', 'error')
        return redirect(url_for('tools.detail', barcode=barcode))

# Weitere Tool-Routen...