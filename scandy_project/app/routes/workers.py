from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from app.models.mongodb_models import MongoDBWorker
from app.models.mongodb_database import mongodb
from app.utils.decorators import login_required, admin_required, mitarbeiter_required
from datetime import datetime, timedelta
from flask_login import current_user
import os
import tempfile
from docxtpl import DocxTemplate
from bson import ObjectId

bp = Blueprint('workers', __name__, url_prefix='/workers')

@bp.route('/')
@mitarbeiter_required
def index():
    """Mitarbeiter-Übersicht"""
    try:
        # Debug-Ausgabe
        print("\n=== WORKERS INDEX ===")
        
        # Hole alle aktiven Mitarbeiter
        workers = mongodb.find('workers', {'deleted': {'$ne': True}})
        workers = list(workers)
        
        # Füge aktive Ausleihen hinzu
        for worker in workers:
            active_lendings = mongodb.count_documents('lendings', {
                'worker_barcode': worker['barcode'],
                'returned_at': None
            })
            worker['active_lendings'] = active_lendings
        
        # Sortiere nach Nachname, Vorname
        workers.sort(key=lambda x: (x.get('lastname', ''), x.get('firstname', '')))
        
        print(f"Gefundene Mitarbeiter: {len(workers)}")
        if workers:
            print("Erster Datensatz:", workers[0])
        
        # Hole alle Abteilungen
        departments = mongodb.find('departments', {'deleted': {'$ne': True}})
        departments = [d['name'] for d in departments]
        
        print(f"Gefundene Abteilungen: {departments}")
        
        return render_template('workers/index.html',
                             workers=workers,
                             departments=departments,
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
    # Lade Abteilungen
    departments = mongodb.find('departments', {'deleted': {'$ne': True}})
    departments = [d['name'] for d in departments]
    
    if request.method == 'POST':
        barcode = request.form['barcode']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        department = request.form.get('department', '')
        email = request.form.get('email', '')
        
        try:
            # Prüfe ob der Barcode bereits existiert
            existing_tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
            existing_consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
            existing_worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
            
            if existing_tool or existing_consumable or existing_worker:
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
            worker_data = {
                'barcode': barcode,
                'firstname': firstname,
                'lastname': lastname,
                'department': department,
                'email': email,
                'created_at': datetime.now(),
                'modified_at': datetime.now(),
                'deleted': False
            }
            
            mongodb.insert_one('workers', worker_data)
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
        departments = mongodb.find('departments', {'deleted': {'$ne': True}})
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
                return redirect(url_for('workers.details', original_barcode=original_barcode))

            # Prüfen, ob der Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': original_barcode, 'deleted': {'$ne': True}})
            if not worker:
                flash('Mitarbeiter nicht gefunden.', 'error')
                return redirect(url_for('workers.index'))

            barcode_changed = (new_barcode != original_barcode)

            if barcode_changed:
                # Prüfen, ob der neue Barcode bereits existiert
                existing_tool = mongodb.find_one('tools', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                existing_consumable = mongodb.find_one('consumables', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                existing_worker = mongodb.find_one('workers', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                
                if existing_tool or existing_consumable or existing_worker:
                    flash(f'Der Barcode "{new_barcode}" existiert bereits. Bitte wählen Sie einen anderen.', 'error')
                    return redirect(url_for('workers.details', original_barcode=original_barcode))
                
                # Update Barcode in referenzierenden Tabellen
                mongodb.update_many('lendings', 
                                  {'worker_barcode': original_barcode}, 
                                  {'$set': {'worker_barcode': new_barcode}})
                mongodb.update_many('consumable_usages', 
                                  {'worker_barcode': original_barcode}, 
                                  {'$set': {'worker_barcode': new_barcode}})

            # Update der Mitarbeiterdaten
            update_data = {
                'barcode': new_barcode,
                'firstname': firstname,
                'lastname': lastname,
                'department': department,
                'email': email,
                'modified_at': datetime.now()
            }
            
            mongodb.update_one('workers', 
                             {'barcode': original_barcode}, 
                             {'$set': update_data})

            flash('Mitarbeiter erfolgreich aktualisiert', 'success')
            return redirect(url_for('workers.details', original_barcode=new_barcode))

        # GET-Methode: Details anzeigen
        worker = mongodb.find_one('workers', {'barcode': original_barcode, 'deleted': {'$ne': True}})
        if not worker:
            flash('Mitarbeiter nicht gefunden', 'error')
            return redirect(url_for('workers.index'))

        # Hole aktuelle Ausleihen
        active_lendings = mongodb.find('lendings', {
            'worker_barcode': original_barcode,
            'returned_at': None
        })
        active_lendings = list(active_lendings)
        
        # Füge Tool-Informationen hinzu
        for lending in active_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            if tool:
                lending['tool_name'] = tool['name']

        # Hole Verlauf aller Ausleihen
        all_lendings = mongodb.find('lendings', {'worker_barcode': original_barcode})
        all_lendings = list(all_lendings)
        
        # Sortiere nach Datum (neueste zuerst)
        all_lendings.sort(key=lambda x: x.get('lent_at', datetime.min), reverse=True)
        
        # Füge Tool-Informationen hinzu
        for lending in all_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            if tool:
                lending['tool_name'] = tool['name']

        return render_template('workers/details.html',
                             worker=worker,
                             departments=departments,
                             active_lendings=active_lendings,
                             all_lendings=all_lendings,
                             is_admin=current_user.is_admin)

    except Exception as e:
        print(f"Fehler beim Laden der Mitarbeiterdetails: {str(e)}")
        import traceback
        print(traceback.format_exc())
        flash('Fehler beim Laden der Mitarbeiterdetails', 'error')
        return redirect(url_for('workers.index'))

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
                
            # Prüfen, ob der Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
            if not worker:
                flash('Mitarbeiter nicht gefunden', 'error')
                return redirect(url_for('workers.index'))

            # Update der Mitarbeiterdaten
            update_data = {
                'barcode': new_barcode,
                'firstname': firstname,
                'lastname': lastname,
                'department': department,
                'email': email,
                'phone': phone,
                'modified_at': datetime.now()
            }
            
            mongodb.update_one('workers', 
                             {'barcode': barcode}, 
                             {'$set': update_data})
            
            flash('Mitarbeiter erfolgreich aktualisiert', 'success')
            return redirect(url_for('workers.details', original_barcode=new_barcode))
            
    except Exception as e:
        print(f"Fehler beim Aktualisieren des Mitarbeiters: {str(e)}")
        flash('Fehler beim Aktualisieren des Mitarbeiters', 'error')
        return redirect(url_for('workers.details', barcode=barcode))

@bp.route('/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_by_barcode(barcode):
    """Löscht einen Mitarbeiter (Soft Delete)"""
    try:
        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404
            
        # Prüfe ob der Mitarbeiter noch Werkzeuge ausgeliehen hat
        lending = mongodb.find_one('lendings', {'worker_barcode': barcode, 'returned_at': None})
        
        if lending:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter muss zuerst alle Werkzeuge zurückgeben'
            }), 400
            
        # Führe Soft Delete durch
        mongodb.update_one('workers', 
                         {'barcode': barcode}, 
                         {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
        
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
        workers = mongodb.find('workers', {
            'firstname': {'$regex': query, '$options': 'i'},
            'lastname': {'$regex': query, '$options': 'i'},
            'barcode': {'$regex': query, '$options': 'i'},
            'deleted': {'$ne': True}
        })
        return jsonify([dict(worker) for worker in workers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/timesheets')
@mitarbeiter_required
def timesheet_list():
    user_id = current_user.username
    sort = request.args.get('sort', 'kw_desc')
    
    # Aktuelle Kalenderwoche ermitteln
    today = datetime.now()
    current_year = today.isocalendar()[0]
    current_week = today.isocalendar()[1]
    
    # Prüfen ob ein Eintrag für die aktuelle Woche existiert
    existing_entry = mongodb.find_one('timesheets', {
        'user_id': user_id,
        'year': current_year,
        'kw': current_week
    })
    
    # Wenn kein Eintrag existiert, erstelle einen neuen
    if not existing_entry:
        mongodb.insert_one('timesheets', {
            'user_id': user_id,
            'year': current_year,
            'kw': current_week,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
    
    # MongoDB Aggregation Pipeline für Timesheets
    pipeline = [
        {'$match': {'user_id': user_id}},
        {
            '$addFields': {
                'filled_days': {
                    '$add': [
                        {'$cond': [{'$and': [{'$ne': ['$montag_start', '']}, {'$ne': ['$montag_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$dienstag_start', '']}, {'$ne': ['$dienstag_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$mittwoch_start', '']}, {'$ne': ['$mittwoch_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$donnerstag_start', '']}, {'$ne': ['$donnerstag_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$freitag_start', '']}, {'$ne': ['$freitag_tasks', '']}]}, 1, 0]}
                    ]
                },
                'created_at_de': {
                    '$dateToString': {
                        'format': '%d.%m.%Y',
                        'date': '$created_at'
                    }
                },
                'updated_at_de': {
                    '$dateToString': {
                        'format': '%d.%m.%Y',
                        'date': '$updated_at'
                    }
                }
            }
        }
    ]
    
    # Sortierung hinzufügen
    sort_stage = {}
    if sort == 'year_desc':
        sort_stage = {'year': -1, 'kw': -1}
    elif sort == 'year_asc':
        sort_stage = {'year': 1, 'kw': 1}
    elif sort == 'kw_desc':
        sort_stage = {'year': -1, 'kw': -1}
    elif sort == 'kw_asc':
        sort_stage = {'year': 1, 'kw': 1}
    elif sort == 'filled_desc':
        sort_stage = {'filled_days': -1, 'year': -1, 'kw': -1}
    elif sort == 'filled_asc':
        sort_stage = {'filled_days': 1, 'year': -1, 'kw': -1}
    elif sort == 'created_desc':
        sort_stage = {'created_at': -1}
    elif sort == 'created_asc':
        sort_stage = {'created_at': 1}
    elif sort == 'updated_desc':
        sort_stage = {'updated_at': -1}
    elif sort == 'updated_asc':
        sort_stage = {'updated_at': 1}
    
    if sort_stage:
        pipeline.append({'$sort': sort_stage})
    
    # MongoDB Aggregation ausführen
    timesheets = list(mongodb.db.timesheets.aggregate(pipeline))
    
    # Berechne unausgefüllte Tage für alle Wochen
    unfilled_days = 0
    for ts in timesheets:
        # Berechne den Wochenstart
        week_start = datetime.fromisocalendar(ts['year'], ts['kw'], 1)  # 1 = Montag
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
        
        for i, day in enumerate(days):
            # Berechne das Datum für den aktuellen Tag
            current_day = week_start + timedelta(days=i)
            
            # Prüfe nur vergangene Tage
            if current_day.date() < today.date():
                has_times = ts.get(f'{day}_start') or ts.get(f'{day}_end')
                has_tasks = ts.get(f'{day}_tasks')
                if not (has_times and has_tasks):
                    unfilled_days += 1
    
    return render_template('workers/timesheet_list.html', 
                         timesheets=timesheets,
                         unfilled_days=unfilled_days,
                         unfilled_timesheet_days=unfilled_days,
                         today=today,
                         datetime=datetime,
                         timedelta=timedelta
    )

@bp.route('/timesheet/new', methods=['GET', 'POST'])
@mitarbeiter_required
def timesheet_create():
    if request.method == 'POST':
        user_id = current_user.username
        week = request.form.get('week')  # z.B. '2024-W20'
        if week and '-W' in week:
            year, week_str = week.split('-W')
            calendar_week = int(week_str)
            year = int(year)
        else:
            flash('Ungültiges Wochenformat.', 'error')
            return redirect(url_for('workers.timesheet_create'))
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
        data = {
            'user_id': user_id,
            'year': year,
            'kw': calendar_week,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        for day in days:
            data[f'{day}_tasks'] = request.form.get(f'tasks_{day}', '')
            data[f'{day}_start'] = request.form.get(f'start_{day}', '')
            data[f'{day}_end'] = request.form.get(f'end_{day}', '')
        mongodb.insert_one('timesheets', data)
        flash('Wochenplan erfolgreich gespeichert.', 'success')
        return redirect(url_for('workers.timesheet_list'))
    return render_template('workers/timesheet.html', now=datetime.now())

@bp.route('/timesheet/<string:ts_id>/edit', methods=['GET', 'POST'])
@mitarbeiter_required
def timesheet_edit(ts_id):
    user_id = current_user.username
    
    # Konvertiere ts_id zu ObjectId
    try:
        object_id = ObjectId(ts_id)
    except:
        flash('Ungültige Timesheet-ID.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    
    ts = mongodb.find_one('timesheets', {'_id': object_id, 'user_id': user_id})
    if not ts:
        flash('Wochenplan nicht gefunden oder keine Berechtigung.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    
    if request.method == 'POST':
        week = request.form.get('week')
        if week and '-W' in week:
            year, week_str = week.split('-W')
            calendar_week = int(week_str)
            year = int(year)
        else:
            flash('Ungültiges Wochenformat.', 'error')
            return redirect(url_for('workers.timesheet_edit', ts_id=ts_id))
        
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
        update_data = {
            'year': year,
            'kw': calendar_week,
            'updated_at': datetime.now()
        }
        
        for day in days:
            update_data[f'{day}_tasks'] = request.form.get(f'tasks_{day}', '')
            update_data[f'{day}_start'] = request.form.get(f'start_{day}', '')
            update_data[f'{day}_end'] = request.form.get(f'end_{day}', '')
        
        mongodb.update_one('timesheets', 
                         {'_id': object_id}, 
                         {'$set': update_data})
        flash('Wochenplan aktualisiert.', 'success')
        return redirect(url_for('workers.timesheet_list'))
    return render_template('workers/timesheet.html', ts=ts, now=datetime.now())

@bp.route('/timesheet/<string:ts_id>/download')
@mitarbeiter_required
def timesheet_download(ts_id):
    user_id = current_user.username
    
    # Konvertiere ts_id zu ObjectId
    try:
        object_id = ObjectId(ts_id)
    except:
        flash('Ungültige Timesheet-ID.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    
    ts = mongodb.find_one('timesheets', {'_id': object_id, 'user_id': user_id})
    if not ts:
        flash('Wochenplan nicht gefunden oder keine Berechtigung.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    # Kontext für docxtpl bauen
    name = current_user.username
    context = {
        'kw': ts['kw'],
        'name': name,
    }
    # Korrekte Berechnung des Wochenstarts nach ISO-Kalenderwoche
    week_start = datetime.fromisocalendar(ts['year'], ts['kw'], 1)  # 1 = Montag
    days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
    for i, day in enumerate(days):
        context[f'{day}_tasks'] = ts.get(f'{day}_tasks', '')
        context[f'{day}_datum'] = (week_start + timedelta(days=i)).strftime('%d.%m.')
        start_time = ts.get(f'{day}_start')
        end_time = ts.get(f'{day}_end')
        if start_time and end_time:
            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
            if end < start:
                end += timedelta(days=1)
            hours = (end - start).total_seconds() / 3600
            if hours > 6:
                hours -= 0.5  # Automatisch 30 Minuten Pause abziehen
            if hours < 0:
                hours = 0
            context[f'{day}_hours'] = f'{hours:.2f}'
        else:
            context[f'{day}_hours'] = ''
    template_path = os.path.join('app', 'static', 'word', 'woplan.docx')
    doc = DocxTemplate(template_path)
    doc.render(context)
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f'woplan_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
    doc.save(output_path)
    return send_file(output_path, as_attachment=True, download_name=f'woplan_kw{ts["kw"]}.docx')