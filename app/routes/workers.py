from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.models.database import Database
from app.models.worker import Worker
from app.utils.decorators import login_required, admin_required
from datetime import datetime

bp = Blueprint('workers', __name__, url_prefix='/workers')

@bp.route('/')
def index():
    """Mitarbeiter-Übersicht"""
    try:
        # Debug-Ausgabe
        print("\n=== WORKERS INDEX ===")
        
        # Hole alle aktiven Mitarbeiter mit Ausleihzähler
        with Database.get_db() as conn:
            workers = conn.execute('''
                SELECT w.*,
                       (SELECT COUNT(*) 
                        FROM lendings l 
                        WHERE l.worker_barcode = w.barcode 
                        AND l.returned_at IS NULL) as active_lendings
                FROM workers w
                WHERE w.deleted = 0
                ORDER BY w.lastname, w.firstname
            ''').fetchall()
        
        print(f"Gefundene Mitarbeiter: {len(workers)}")
        if workers:
            print("Erster Datensatz:", dict(workers[0]))
        
        # Hole alle Abteilungen aus den Settings
        departments = Database.query('''
            SELECT value as name
            FROM settings 
            WHERE key LIKE 'department_%'
            AND value IS NOT NULL
            AND value != ''
            ORDER BY value
        ''')
        
        print(f"Gefundene Abteilungen: {[d['name'] for d in departments]}")
        
        return render_template('workers/index.html',
                             workers=workers,
                             departments=[d['name'] for d in departments],
                             is_admin=session.get('is_admin', False))
                             
    except Exception as e:
        print(f"Fehler beim Laden der Mitarbeiter: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('Fehler beim Laden der Mitarbeiter', 'error')
        return redirect(url_for('index'))

@bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add():
    # Lade Abteilungen aus Settings
    departments = Database.query('''
        SELECT value as name
        FROM settings 
        WHERE key LIKE 'department_%'
        AND value IS NOT NULL
        AND value != ''
        ORDER BY value
    ''')
    departments = [d['name'] for d in departments]
    
    if request.method == 'POST':
        barcode = request.form['barcode']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        department = request.form.get('department', '')
        email = request.form.get('email', '')
        
        try:
            Database.query(
                '''INSERT INTO workers 
                   (barcode, firstname, lastname, department, email) 
                   VALUES (?, ?, ?, ?, ?)''',
                [barcode, firstname, lastname, department, email]
            )
            flash('Mitarbeiter erfolgreich hinzugefügt', 'success')
            return redirect(url_for('workers.index'))
        except Exception as e:
            flash(f'Fehler beim Hinzufügen: {str(e)}', 'error')
            
    return render_template('workers/add.html', departments=departments)

@bp.route('/<barcode>', methods=['GET', 'POST'])
@login_required
def details(barcode):
    """Details eines Mitarbeiters anzeigen und bearbeiten"""
    try:
        # Lade Abteilungen aus Settings
        departments = Database.query('''
            SELECT value as name
            FROM settings 
            WHERE key LIKE 'department_%'
            AND value IS NOT NULL
            AND value != ''
            ORDER BY value
        ''')
        departments = [d['name'] for d in departments]
        
        if request.method == 'POST':
            data = request.form
            
            with Database.get_db() as conn:
                conn.execute('''
                    UPDATE workers 
                    SET firstname = ?,
                        lastname = ?,
                        department = ?,
                        modified_at = CURRENT_TIMESTAMP
                    WHERE barcode = ? AND deleted = 0
                ''', [
                    data.get('firstname'),
                    data.get('lastname'),
                    data.get('department'),
                    barcode
                ])
                conn.commit()
            
            return jsonify({'success': True})
        
        # GET-Anfrage: Details anzeigen
        with Database.get_db() as conn:
            # Mitarbeiter-Details laden
            worker = conn.execute('''
                SELECT * FROM workers 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode]).fetchone()
            
            if not worker:
                return jsonify({'success': False, 'message': 'Mitarbeiter nicht gefunden'}), 404
            
            # Aktuelle Ausleihen laden
            current_lendings = conn.execute('''
                SELECT l.*, t.name as tool_name
                FROM lendings l
                JOIN tools t ON l.tool_barcode = t.barcode AND t.deleted = 0
                WHERE l.worker_barcode = ?
                AND l.returned_at IS NULL
                ORDER BY l.lent_at DESC
            ''', [barcode]).fetchall()
            
            # Ausleihhistorie laden (alle Ausleihen)
            lending_history = conn.execute('''
                SELECT 
                    l.*, 
                    t.name as tool_name,
                    CASE 
                        WHEN l.returned_at IS NULL THEN 'Ausgeliehen'
                        ELSE 'Zurückgegeben am ' || datetime(l.returned_at)
                    END as status
                FROM lendings l
                JOIN tools t ON l.tool_barcode = t.barcode AND t.deleted = 0
                WHERE l.worker_barcode = ?
                ORDER BY l.lent_at DESC
            ''', [barcode]).fetchall()
            
            # Verbrauchsmaterial-Historie laden
            usage_history = conn.execute('''
                SELECT u.*, c.name as consumable_name
                FROM consumable_usages u
                JOIN consumables c ON u.consumable_barcode = c.barcode AND c.deleted = 0
                WHERE u.worker_barcode = ?
                ORDER BY u.used_at DESC
            ''', [barcode]).fetchall()
            
            return render_template('workers/details.html',
                               worker=worker,
                               departments=departments,
                               current_lendings=current_lendings,
                               lending_history=lending_history,
                               usage_history=usage_history)
                               
    except Exception as e:
        print(f"Fehler in worker details: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<barcode>/edit', methods=['POST'])
@admin_required
def edit(barcode):
    try:
        Database.query('''
            UPDATE workers 
            SET firstname = ?,
                lastname = ?,
                email = ?,
                department = ?
            WHERE barcode = ?
        ''', [
            request.form['firstname'],
            request.form['lastname'],
            request.form.get('email', ''),
            request.form.get('department', ''),
            barcode
        ])
        flash('Mitarbeiter erfolgreich aktualisiert', 'success')
    except Exception as e:
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'error')
    
    return redirect(url_for('workers.details', barcode=barcode))

@bp.route('/<barcode>/delete', methods=['POST'])
@admin_required
def delete_by_barcode(barcode):
    """Löscht einen Mitarbeiter anhand des Barcodes (Soft Delete)"""
    try:
        with Database.get_db() as conn:
            # Prüfe ob der Mitarbeiter existiert
            worker = conn.execute(
                'SELECT * FROM workers WHERE barcode = ? AND deleted = 0',
                [barcode]
            ).fetchone()
            
            if not worker:
                return jsonify({
                    'success': False, 
                    'message': 'Mitarbeiter nicht gefunden'
                }), 404
            
            # Prüfe ob der Mitarbeiter aktive Ausleihen hat
            lending = conn.execute('''
                SELECT * FROM lendings 
                WHERE worker_barcode = ? 
                AND returned_at IS NULL
            ''', [barcode]).fetchone()
            
            if lending:
                return jsonify({
                    'success': False,
                    'message': 'Mitarbeiter hat noch aktive Ausleihen'
                }), 400
            
            # In den Papierkorb verschieben (soft delete)
            conn.execute('''
                UPDATE workers 
                SET deleted = 1,
                    deleted_at = datetime('now'),
                    modified_at = datetime('now')
                WHERE barcode = ?
            ''', [barcode])
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Mitarbeiter wurde in den Papierkorb verschoben'
            })
            
    except Exception as e:
        print(f"Fehler beim Löschen des Mitarbeiters: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/workers/search')
def search():
    query = request.args.get('q', '')
    try:
        workers = Database.query('''
            SELECT * FROM workers 
            WHERE (firstname LIKE ? OR lastname LIKE ? OR barcode LIKE ?) 
            AND deleted = 0
        ''', [f'%{query}%', f'%{query}%', f'%{query}%'])
        return jsonify([dict(worker) for worker in workers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500