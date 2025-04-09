from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.models.database import Database
from app.utils.decorators import admin_required, login_required
from datetime import datetime
import logging

# Explizit URL-Präfix setzen
bp = Blueprint('tools', __name__, url_prefix='/tools')

@bp.route('/')
def index():
    """Zeigt alle aktiven Werkzeuge"""
    try:
        with Database.get_db() as conn:
            # Debug: Prüfe aktive Ausleihen
            active_lendings = conn.execute('''
                SELECT tool_barcode, worker_barcode, lent_at 
                FROM lendings 
                WHERE returned_at IS NULL
            ''').fetchall()
            print("Aktive Ausleihen:", [dict(l) for l in active_lendings])

            tools = conn.execute('''
                SELECT t.*,
                       CASE 
                           WHEN l.tool_barcode IS NOT NULL THEN 'ausgeliehen'
                           WHEN t.status = 'defekt' THEN 'defekt'
                           ELSE 'verfügbar'
                       END as current_status,
                       w.firstname || ' ' || w.lastname as lent_to,
                       l.lent_at as lending_date,
                       t.location,
                       t.category
                FROM tools t
                LEFT JOIN (
                    SELECT tool_barcode, worker_barcode, lent_at
                    FROM lendings
                    WHERE returned_at IS NULL
                ) l ON t.barcode = l.tool_barcode
                LEFT JOIN workers w ON l.worker_barcode = w.barcode
                WHERE t.deleted = 0
                GROUP BY t.barcode
                ORDER BY t.name
            ''').fetchall()
            
            # Debug-Ausgabe
            if tools:
                print("Beispiel-Tool:", dict(tools[0]))
                for tool in tools:
                    tool_dict = dict(tool)
                    print(f"Tool {tool_dict['barcode']}: Status = {tool_dict['current_status']}, Ausgeliehen an = {tool_dict.get('lent_to', 'niemanden')}")
            
            categories = conn.execute('''
                SELECT DISTINCT category FROM tools
                WHERE deleted = 0 AND category IS NOT NULL
                ORDER BY category
            ''').fetchall()
            
            locations = conn.execute('''
                SELECT DISTINCT location FROM tools
                WHERE deleted = 0 AND location IS NOT NULL
                ORDER BY location
            ''').fetchall()
            
            return render_template('tools/index.html',
                               tools=tools,
                               categories=[c['category'] for c in categories],
                               locations=[l['location'] for l in locations],
                               is_admin=session.get('is_admin', False))
                               
    except Exception as e:
        print(f"Fehler beim Laden der Werkzeuge: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('Fehler beim Laden der Werkzeuge', 'error')
        return redirect(url_for('main.index'))

@bp.route('/<barcode>')
@admin_required
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
    
    # Hole vordefinierte Kategorien und Standorte aus den Einstellungen
    categories = Database.get_categories('tools')
    locations = Database.get_locations('tools')
    
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
@admin_required
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

@bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add():
    """Fügt ein neues Werkzeug hinzu"""
    if request.method == 'POST':
        barcode = request.form.get('barcode')
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        location = request.form.get('location')
        
        if not all([barcode, name, category, location]):
            flash('Bitte alle Pflichtfelder ausfüllen', 'error')
            return redirect(url_for('tools.add'))
            
        try:
            # Prüfe ob Barcode bereits existiert
            existing = Database.query('SELECT 1 FROM tools WHERE barcode = ?', [barcode], one=True)
            if existing:
                flash('Ein Werkzeug mit diesem Barcode existiert bereits', 'error')
                return redirect(url_for('tools.add'))
            
            Database.query('''
                INSERT INTO tools (barcode, name, description, category, location, status)
                VALUES (?, ?, ?, ?, ?, 'verfügbar')
            ''', [barcode, name, description, category, location])
            
            flash('Werkzeug erfolgreich hinzugefügt', 'success')
            return redirect(url_for('tools.index'))
            
        except Exception as e:
            print(f"Fehler beim Hinzufügen des Werkzeugs: {str(e)}")
            flash('Fehler beim Hinzufügen des Werkzeugs', 'error')
            return redirect(url_for('tools.add'))
    
    try:
        # Lade Kategorien und Standorte aus der settings-Tabelle
        with Database.get_db() as db:
            cursor = db.execute(
                "SELECT value FROM settings WHERE key LIKE 'category_%' AND value IS NOT NULL AND value != '' ORDER BY value"
            )
            categories = [row['value'] for row in cursor.fetchall()]
            
            cursor = db.execute(
                "SELECT value FROM settings WHERE key LIKE 'location_%' AND value IS NOT NULL AND value != '' ORDER BY value"
            )
            locations = [row['value'] for row in cursor.fetchall()]
            
        return render_template('tools/add.html', categories=categories, locations=locations)
        
    except Exception as e:
        print(f"Fehler beim Laden der Auswahloptionen: {str(e)}")
        flash('Fehler beim Laden der Auswahloptionen', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/<string:barcode>/status', methods=['POST'])
@login_required
def change_status(barcode):
    """Ändert den Status eines Werkzeugs"""
    try:
        status = request.form.get('status')
        reason = request.form.get('reason', '')  # Optional, leerer String wenn nicht angegeben
        
        if not status:
            return jsonify({
                'success': False,
                'message': 'Status muss angegeben werden'
            }), 400
            
        # Prüfe ob das Werkzeug existiert und hole aktuellen Status
        tool = Database.query('''
            SELECT * FROM tools 
            WHERE barcode = ? AND deleted = 0
        ''', [barcode], one=True)
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
            
        # Prüfe ob das Werkzeug ausgeliehen ist
        if status == 'defekt':
            lending = Database.query('''
                SELECT * FROM lendings
                WHERE tool_barcode = ? AND returned_at IS NULL
            ''', [barcode], one=True)
            
            if lending:
                return jsonify({
                    'success': False,
                    'message': 'Werkzeug muss zuerst zurückgegeben werden'
                }), 400
        
        # Statusänderung protokollieren
        Database.query('''
            INSERT INTO tool_status_changes 
            (tool_barcode, old_status, new_status, reason)
            VALUES (?, ?, ?, ?)
        ''', [barcode, tool['status'], status, reason])

        # Status des Werkzeugs aktualisieren
        Database.query('''
            UPDATE tools 
            SET status = ?,
                modified_at = CURRENT_TIMESTAMP
            WHERE barcode = ?
        ''', [status, barcode])

        return jsonify({
            'success': True,
            'message': 'Status erfolgreich aktualisiert'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Statusänderung: {str(e)}'
        }), 500

@bp.route('/<barcode>/edit', methods=['GET', 'POST'])
@admin_required
def edit(barcode):
    """Bearbeitet ein bestehendes Werkzeug"""
    try:
        with Database.get_db() as db:
            # Lade das Werkzeug
            tool = db.execute('''
                SELECT * FROM tools 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode]).fetchone()
            
            if not tool:
                flash('Werkzeug nicht gefunden', 'error')
                return redirect(url_for('tools.index'))

            if request.method == 'POST':
                name = request.form.get('name')
                description = request.form.get('description')
                category = request.form.get('category')
                location = request.form.get('location')
                
                if not all([name, category, location]):
                    flash('Bitte alle Pflichtfelder ausfüllen', 'error')
                    return redirect(url_for('tools.edit', barcode=barcode))
                
                # Aktualisiere das Werkzeug
                db.execute('''
                    UPDATE tools 
                    SET name = ?, description = ?, category = ?, location = ?
                    WHERE barcode = ?
                ''', [name, description, category, location, barcode])
                db.commit()
                
                flash('Werkzeug erfolgreich aktualisiert', 'success')
                return redirect(url_for('tools.detail', barcode=barcode))
            
            # Lade Kategorien und Standorte aus der settings-Tabelle
            cursor = db.execute(
                "SELECT value FROM settings WHERE key LIKE 'category_%' AND value IS NOT NULL AND value != '' ORDER BY value"
            )
            categories = [row['value'] for row in cursor.fetchall()]
            
            cursor = db.execute(
                "SELECT value FROM settings WHERE key LIKE 'location_%' AND value IS NOT NULL AND value != '' ORDER BY value"
            )
            locations = [row['value'] for row in cursor.fetchall()]
            
            return render_template('tools/edit.html', 
                                tool=tool,
                                categories=categories,
                                locations=locations)
            
    except Exception as e:
        print(f"Fehler beim Bearbeiten des Werkzeugs: {str(e)}")
        flash('Fehler beim Bearbeiten des Werkzeugs', 'error')
        return redirect(url_for('tools.index'))

@bp.route('/<barcode>/delete', methods=['POST'])
@admin_required
def delete_by_barcode(barcode):
    """Löscht ein Werkzeug anhand des Barcodes (Soft Delete)"""
    try:
        with Database.get_db() as conn:
            # Prüfe ob das Werkzeug existiert
            tool = conn.execute(
                'SELECT * FROM tools WHERE barcode = ? AND deleted = 0',
                [barcode]
            ).fetchone()
            
            if not tool:
                return jsonify({
                    'success': False, 
                    'message': 'Werkzeug nicht gefunden'
                }), 404
            
            # Prüfe ob das Werkzeug ausgeliehen ist
            lending = conn.execute('''
                SELECT * FROM lendings 
                WHERE tool_barcode = ? 
                AND returned_at IS NULL
            ''', [barcode]).fetchone()
            
            if lending:
                return jsonify({
                    'success': False,
                    'message': 'Ausgeliehene Werkzeuge können nicht gelöscht werden'
                }), 400
            
            # In den Papierkorb verschieben (soft delete)
            conn.execute('''
                UPDATE tools 
                SET deleted = 1,
                    deleted_at = datetime('now'),
                    modified_at = datetime('now')
                WHERE barcode = ?
            ''', [barcode])
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Werkzeug wurde in den Papierkorb verschoben'
            })
            
    except Exception as e:
        print(f"Fehler beim Löschen des Werkzeugs: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

# Weitere Tool-Routen...