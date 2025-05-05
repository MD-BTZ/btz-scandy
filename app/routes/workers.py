from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.models.database import Database
from app.models.worker import Worker
from app.utils.decorators import login_required, admin_required, mitarbeiter_required
from datetime import datetime

bp = Blueprint('workers', __name__, url_prefix='/workers')

@bp.route('/')
@mitarbeiter_required
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
@mitarbeiter_required
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
@mitarbeiter_required
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
                        department = ?
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
@mitarbeiter_required
def edit(barcode):
    """Bearbeitet einen Mitarbeiter"""
    try:
        with Database.get_db() as conn:
            # Prüfe ob der Mitarbeiter existiert
            worker = conn.execute('''
                SELECT * FROM workers 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode]).fetchone()
            
            if not worker:
                flash('Mitarbeiter nicht gefunden', 'error')
                return redirect(url_for('workers.index'))
                
            # Aktualisiere die Daten
            conn.execute('''
                UPDATE workers 
                SET firstname = ?,
                    lastname = ?,
                    department = ?,
                    email = ?,
                    sync_status = 'pending'
                WHERE barcode = ?
            ''', [
                request.form['firstname'],
                request.form['lastname'],
                request.form.get('department', ''),
                request.form.get('email', ''),
                barcode
            ])
            
            conn.commit()
            
            flash('Mitarbeiter erfolgreich aktualisiert', 'success')
            return redirect(url_for('workers.details', barcode=barcode))
            
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Mitarbeiters: {str(e)}")
        flash('Fehler beim Aktualisieren des Mitarbeiters', 'error')
        return redirect(url_for('workers.details', barcode=barcode))

@bp.route('/<barcode>/delete', methods=['POST'])
@mitarbeiter_required
def delete_by_barcode(barcode):
    """Löscht einen Mitarbeiter (Soft Delete)"""
    try:
        with Database.get_db() as conn:
            # Prüfe ob der Mitarbeiter existiert
            worker = conn.execute('''
                SELECT * FROM workers 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode]).fetchone()
            
            if not worker:
                flash('Mitarbeiter nicht gefunden', 'error')
                return redirect(url_for('workers.index'))
                
            # Prüfe ob der Mitarbeiter noch Werkzeuge ausgeliehen hat
            lending = conn.execute('''
                SELECT * FROM lendings
                WHERE worker_barcode = ? AND returned_at IS NULL
            ''', [barcode]).fetchone()
            
            if lending:
                flash('Mitarbeiter muss zuerst alle Werkzeuge zurückgeben', 'error')
                return redirect(url_for('workers.details', barcode=barcode))
                
            # Führe Soft Delete durch
            conn.execute('''
                UPDATE workers 
                SET deleted = 1,
                    deleted_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'),
                    sync_status = 'pending'
                WHERE barcode = ?
            ''', [barcode])
            
            conn.commit()
            
            flash('Mitarbeiter erfolgreich gelöscht', 'success')
            return redirect(url_for('workers.index'))
            
    except Exception as e:
        print(f"Fehler beim Löschen des Mitarbeiters: {str(e)}")
        flash('Fehler beim Löschen des Mitarbeiters', 'error')
        return redirect(url_for('workers.details', barcode=barcode))

@bp.route('/workers/search')
@mitarbeiter_required
def search():
    """Sucht nach Mitarbeitern"""
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