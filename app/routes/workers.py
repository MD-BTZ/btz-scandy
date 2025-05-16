from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app.models.database import Database
from app.models.worker import Worker
from app.utils.decorators import login_required, admin_required, mitarbeiter_required
from datetime import datetime
from flask_login import current_user

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
                             is_admin=current_user.is_admin)
                             
    except Exception as e:
        print(f"Fehler beim Laden der Mitarbeiter: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('Fehler beim Laden der Mitarbeiter', 'error')
        return redirect(url_for('main.index'))

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
                # Gebe die Formulardaten zurück an das Template
                return render_template('workers/add.html',
                                   departments=departments,
                                   form_data={
                                       'barcode': barcode,
                                       'firstname': firstname,
                                       'lastname': lastname,
                                       'department': department,
                                       'email': email
                                   })
            
            # Wenn Barcode eindeutig ist, füge den Mitarbeiter hinzu
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
            # Gebe die Formulardaten zurück an das Template
            return render_template('workers/add.html',
                               departments=departments,
                               form_data={
                                   'barcode': barcode,
                                   'firstname': firstname,
                                   'lastname': lastname,
                                   'department': department,
                                   'email': email
                               })
            
    return render_template('workers/add.html', departments=departments)

@bp.route('/<string:original_barcode>', methods=['GET', 'POST'])
@mitarbeiter_required
def details(original_barcode):
    """Details eines Mitarbeiters anzeigen und bearbeiten"""
    try:
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
            new_barcode = data.get('barcode').strip()
            firstname = data.get('firstname').strip()
            lastname = data.get('lastname').strip()
            department = data.get('department', '')
            email = data.get('email', '').strip()

            if not all([new_barcode, firstname, lastname]):
                flash('Barcode, Vorname und Nachname sind Pflichtfelder.', 'error')
                # Umleitung zurück zur Detailseite mit dem *originalen* Barcode, falls die Validierung fehlschlägt
                return redirect(url_for('workers.details', original_barcode=original_barcode))

            with Database.get_db() as conn:
                # Prüfen, ob der Mitarbeiter existiert
                worker = conn.execute("SELECT * FROM workers WHERE barcode = ? AND deleted = 0", [original_barcode]).fetchone()
                if not worker:
                    flash('Mitarbeiter nicht gefunden.', 'error')
                    return redirect(url_for('workers.index'))

                barcode_changed = (new_barcode != original_barcode)

                if barcode_changed:
                    # Prüfen, ob der neue Barcode bereits existiert (für Tools, Consumables oder andere Worker)
                    exists_count = conn.execute("""
                        SELECT COUNT(*) as count FROM (
                            SELECT barcode FROM tools WHERE barcode = ? AND deleted = 0
                            UNION ALL 
                            SELECT barcode FROM consumables WHERE barcode = ? AND deleted = 0
                            UNION ALL
                            SELECT barcode FROM workers WHERE barcode = ? AND barcode != ? AND deleted = 0
                        )
                    """, [new_barcode, new_barcode, new_barcode, original_barcode]).fetchone()['count']
                    
                    if exists_count > 0:
                        flash(f'Der Barcode "{new_barcode}" existiert bereits. Bitte wählen Sie einen anderen.', 'error')
                        return redirect(url_for('workers.details', original_barcode=original_barcode))
                    
                    # Update Barcode in referenzierenden Tabellen
                    conn.execute("UPDATE lendings SET worker_barcode = ? WHERE worker_barcode = ?", [new_barcode, original_barcode])
                    conn.execute("UPDATE consumable_usages SET worker_barcode = ? WHERE worker_barcode = ?", [new_barcode, original_barcode])
                    # Ggf. weitere Tabellen hier hinzufügen, die worker_barcode referenzieren

                # Update der Mitarbeiterdaten (inkl. ggf. neuem Barcode)
                conn.execute('''
                    UPDATE workers 
                    SET barcode = ?,
                        firstname = ?,
                        lastname = ?,
                        department = ?,
                        email = ?,
                        sync_status = 'pending' 
                    WHERE barcode = ? AND deleted = 0 
                ''', [
                    new_barcode, 
                    firstname,
                    lastname,
                    department,
                    email,
                    original_barcode # Wichtig: WHERE-Klausel nutzt den originalen Barcode
                ])
                conn.commit()
            
            flash('Mitarbeiter erfolgreich aktualisiert', 'success')
            # Nach erfolgreicher Aktualisierung zum (ggf. neuen) Barcode weiterleiten
            return redirect(url_for('workers.details', original_barcode=new_barcode))
        
        # GET-Anfrage: Details anzeigen
        with Database.get_db() as conn:
            worker = conn.execute('SELECT * FROM workers WHERE barcode = ? AND deleted = 0', [original_barcode]).fetchone()
            if not worker:
                flash('Mitarbeiter nicht gefunden.', 'error')
                return redirect(url_for('workers.index'))
            
            current_lendings = conn.execute('''
                SELECT l.*, t.name as tool_name
                FROM lendings l
                JOIN tools t ON l.tool_barcode = t.barcode AND t.deleted = 0
                WHERE l.worker_barcode = ?
                AND l.returned_at IS NULL
                ORDER BY l.lent_at DESC
            ''', [original_barcode]).fetchall()
            
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
            ''', [original_barcode]).fetchall()
            
            # Verbrauchsmaterial-Historie laden
            usage_history = conn.execute('''
                SELECT u.*, c.name as consumable_name
                FROM consumable_usages u
                JOIN consumables c ON u.consumable_barcode = c.barcode AND c.deleted = 0
                WHERE u.worker_barcode = ?
                ORDER BY u.used_at DESC
            ''', [original_barcode]).fetchall()
            
            return render_template('workers/details.html',
                               worker=worker,
                               departments=departments,
                               current_lendings=current_lendings,
                               lending_history=lending_history,
                               usage_history=usage_history)
                               
    except Exception as e:
        print(f"Fehler in worker details: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<barcode>/edit', methods=['GET', 'POST'])
@mitarbeiter_required
def edit(barcode):
    """Bearbeitet einen Mitarbeiter"""
    try:
        if request.method == 'POST':
            firstname = request.form.get('firstname')
            lastname = request.form.get('lastname')
            department = request.form.get('department')
            email = request.form.get('email')
            phone = request.form.get('phone')
            new_barcode = request.form.get('barcode')  # Neuer Barcode aus dem Formular
            
            if not all([firstname, lastname]):
                flash('Vor- und Nachname sind erforderlich', 'error')
                return redirect(url_for('workers.edit', barcode=barcode))
                
            with Database.get_db() as conn:
                # Aktualisiere den Mitarbeiter
                conn.execute('''
                    UPDATE workers 
                    SET firstname = ?,
                        lastname = ?,
                        department = ?,
                        email = ?,
                        phone = ?,
                        barcode = ?,
                        sync_status = 'pending'
                    WHERE barcode = ?
                ''', [firstname, lastname, department, email, phone, new_barcode, barcode])
                
                conn.commit()
                
                flash('Mitarbeiter erfolgreich aktualisiert', 'success')
                return redirect(url_for('workers.detail', barcode=new_barcode))  # Weiterleitung mit neuem Barcode
            
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Mitarbeiters: {str(e)}")
        flash('Fehler beim Aktualisieren des Mitarbeiters', 'error')
        return redirect(url_for('workers.details', barcode=barcode))

@bp.route('/<barcode>/delete', methods=['DELETE'])
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
                return jsonify({
                    'success': False,
                    'message': 'Mitarbeiter nicht gefunden'
                }), 404
                
            # Prüfe ob der Mitarbeiter noch Werkzeuge ausgeliehen hat
            lending = conn.execute('''
                SELECT * FROM lendings
                WHERE worker_barcode = ? AND returned_at IS NULL
            ''', [barcode]).fetchone()
            
            if lending:
                return jsonify({
                    'success': False,
                    'message': 'Mitarbeiter muss zuerst alle Werkzeuge zurückgeben'
                }), 400
                
            # Führe Soft Delete durch
            conn.execute('''
                UPDATE workers 
                SET deleted = 1,
                    deleted_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'),
                    sync_status = 'pending'
                WHERE barcode = ?
            ''', [barcode])
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Mitarbeiter erfolgreich gelöscht'
            })
            
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Mitarbeiters: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

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