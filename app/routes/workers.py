from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from app.models.mongodb_models import MongoDBWorker
from app.models.mongodb_database import mongodb
from app.utils.decorators import login_required, admin_required, mitarbeiter_required, teilnehmer_required
from app.utils.database_helpers import get_departments_from_settings
from datetime import datetime, timedelta
from flask_login import current_user
import os
import tempfile
from docxtpl import DocxTemplate
from bson import ObjectId
from typing import Union

bp = Blueprint('workers', __name__, url_prefix='/workers')

def convert_id_for_query(id_value: str) -> Union[str, ObjectId]:
    """
    Konvertiert eine ID für Datenbankabfragen.
    Versucht zuerst mit String-ID, dann mit ObjectId.
    """
    try:
        # Versuche zuerst mit String-ID (für importierte Daten)
        return id_value
    except:
        # Falls das fehlschlägt, versuche ObjectId
        try:
            return ObjectId(id_value)
        except:
            # Falls auch das fehlschlägt, gib die ursprüngliche ID zurück
            return id_value

def find_document_by_id(collection: str, id_value: str):
    """
    Findet ein Dokument in einer Collection mit robuster ID-Behandlung.
    Unterstützt sowohl String-IDs als auch ObjectIds.
    """
    try:
        # Versuche zuerst mit String-ID
        doc = mongodb.find_one(collection, {'_id': id_value})
        if doc:
            return doc
        
        # Falls nicht gefunden, versuche mit ObjectId
        try:
            obj_id = ObjectId(id_value)
            doc = mongodb.find_one(collection, {'_id': obj_id})
            if doc:
                return doc
        except:
            pass
        
        # Falls auch das fehlschlägt, versuche mit convert_id_for_query
        converted_id = convert_id_for_query(id_value)
        doc = mongodb.find_one(collection, {'_id': converted_id})
        return doc
        
    except Exception as e:
        print(f"Fehler beim Suchen von Dokument {id_value} in {collection}: {e}")
        return None

@bp.route('/')
@mitarbeiter_required
def index():
    """Zeigt die Mitarbeiter-Übersicht an"""
    try:
        # Hole alle nicht gelöschten Mitarbeiter
        workers = mongodb.find('workers', {'deleted': {'$ne': True}})
        workers = list(workers)
        
        # Für jeden Mitarbeiter die aktiven Ausleihen zählen
        for worker in workers:
            active_lendings_count = mongodb.count_documents('lendings', {
                'worker_barcode': worker.get('barcode'),
                'returned_at': None
            })
            worker['active_lendings'] = active_lendings_count
        
        # Hole alle Abteilungen für Filter
        departments = get_departments_from_settings()
        
        # Sortiere nach Nachname
        workers.sort(key=lambda x: x.get('lastname', ''))
        
        return render_template('workers/index.html', 
                           workers=workers,
                           departments=departments,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Mitarbeiter: {str(e)}", exc_info=True)
        flash('Fehler beim Laden der Mitarbeiter', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/add', methods=['GET', 'POST'])
@mitarbeiter_required
def add():
    # Lade Abteilungen
    departments = get_departments_from_settings()
    
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
        departments = get_departments_from_settings()
        
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
            
            # Stelle sicher, dass das Datum korrekt formatiert ist
            if isinstance(lending.get('lent_at'), str):
                try:
                    lending['lent_at'] = datetime.strptime(lending['lent_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['lent_at'] = datetime.now()

        # Hole Verlauf aller Ausleihen
        all_lendings = mongodb.find('lendings', {'worker_barcode': original_barcode})
        all_lendings = list(all_lendings)
        
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
        
        all_lendings.sort(key=safe_date_key, reverse=True)
        
        # Sortiere auch aktive Ausleihen nach Datum
        active_lendings.sort(key=safe_date_key, reverse=True)

        # Füge Tool-Informationen hinzu
        for lending in all_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            if tool:
                lending['tool_name'] = tool['name']
            
            # Stelle sicher, dass die Datumsfelder korrekt formatiert sind
            if isinstance(lending.get('lent_at'), str):
                try:
                    lending['lent_at'] = datetime.strptime(lending['lent_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['lent_at'] = datetime.now()
            
            if isinstance(lending.get('returned_at'), str):
                try:
                    lending['returned_at'] = datetime.strptime(lending['returned_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['returned_at'] = None

        return render_template('workers/details.html',
                             worker=worker,
                             departments=departments,
                             current_lendings=active_lendings,
                             lending_history=all_lendings,
                             is_admin=current_user.is_admin)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Mitarbeiterdetails: {str(e)}", exc_info=True)
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
        logger.error(f"Fehler beim Aktualisieren des Mitarbeiters: {str(e)}", exc_info=True)
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

@bp.route('/admin/migrate-timesheets', methods=['POST'])
@admin_required
def admin_migrate_timesheets():
    """Admin-Route zur manuellen Migration von Timesheet-Datumsfeldern"""
    try:
        migrated_count = migrate_timesheet_dates()
        flash(f'Migration abgeschlossen. {migrated_count} Timesheet-Einträge wurden migriert.', 'success')
    except Exception as e:
        flash(f'Fehler bei der Migration: {str(e)}', 'error')
    
    return redirect(url_for('workers.timesheet_list'))

@bp.route('/admin/migrate-all-dates', methods=['POST'])
@admin_required
def admin_migrate_all_dates():
    """Admin-Route zur Migration aller Datumsfelder in allen Collections"""
    try:
        collections = ['tickets', 'users', 'tools', 'consumables', 'workers', 'timesheets']
        total_migrated = 0
        results = {}
        
        for collection in collections:
            try:
                # Finde alle Dokumente mit String-Datumsfeldern
                documents = list(mongodb.db[collection].find({
                    '$or': [
                        {'created_at': {'$type': 'string'}},
                        {'updated_at': {'$type': 'string'}},
                        {'due_date': {'$type': 'string'}},
                        {'resolved_at': {'$type': 'string'}}
                    ]
                }))
                
                migrated_count = 0
                for doc in documents:
                    update_data = {}
                    
                    # Konvertiere alle Datumsfelder
                    for field in ['created_at', 'updated_at', 'due_date', 'resolved_at']:
                        if isinstance(doc.get(field), str):
                            try:
                                for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                    try:
                                        update_data[field] = datetime.strptime(doc[field], fmt)
                                        break
                                    except ValueError:
                                        continue
                                # Wenn kein Format passt, verwende aktuelles Datum
                                if field not in update_data:
                                    update_data[field] = datetime.now()
                            except:
                                update_data[field] = datetime.now()
                    
                    # Update nur wenn Änderungen vorhanden
                    if update_data:
                        result = mongodb.db[collection].update_one(
                            {'_id': doc['_id']},
                            {'$set': update_data}
                        )
                        if result.modified_count > 0:
                            migrated_count += 1
                
                results[collection] = migrated_count
                total_migrated += migrated_count
                
            except Exception as e:
                results[collection] = {'error': str(e)}
        
        flash(f'Migration abgeschlossen. {total_migrated} Dokumente wurden migriert.', 'success')
        return jsonify({
            'success': True,
            'total_migrated': total_migrated,
            'results': results
        })
        
    except Exception as e:
        flash(f'Fehler bei der Migration: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/admin/check-timesheet-dates')
@admin_required
def check_timesheet_dates():
    """Admin-Route zur Überprüfung der Timesheet-Datumsfelder"""
    try:
        # Zähle Timesheets mit String-Datumsfeldern
        string_dates = mongodb.db.timesheets.count_documents({
            '$or': [
                {'created_at': {'$type': 'string'}},
                {'updated_at': {'$type': 'string'}}
            ]
        })
        
        # Zähle Timesheets mit Date-Datumsfeldern
        date_dates = mongodb.db.timesheets.count_documents({
            '$and': [
                {'created_at': {'$type': 'date'}},
                {'updated_at': {'$type': 'date'}}
            ]
        })
        
        total = mongodb.db.timesheets.count_documents({})
        
        return jsonify({
            'total_timesheets': total,
            'string_dates': string_dates,
            'date_dates': date_dates,
            'needs_migration': string_dates > 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/check-database-status')
@admin_required
def check_database_status():
    """Admin-Route zur Überprüfung des Datenbankstatus nach Backup-Restore"""
    try:
        collections = ['tickets', 'users', 'tools', 'consumables', 'workers', 'timesheets']
        status = {}
        
        for collection in collections:
            try:
                # Zähle Dokumente
                total = mongodb.db[collection].count_documents({})
                
                # Prüfe ID-Typen
                sample_docs = list(mongodb.db[collection].find().limit(5))
                id_types = {}
                for doc in sample_docs:
                    doc_id = doc.get('_id')
                    if doc_id:
                        id_type = type(doc_id).__name__
                        id_types[id_type] = id_types.get(id_type, 0) + 1
                
                # Prüfe Datumsfelder (falls vorhanden)
                date_fields = {}
                if sample_docs:
                    sample_doc = sample_docs[0]
                    for field in ['created_at', 'updated_at', 'due_date', 'resolved_at']:
                        if field in sample_doc:
                            field_value = sample_doc[field]
                            if field_value:
                                date_fields[field] = type(field_value).__name__
                
                status[collection] = {
                    'total_documents': total,
                    'id_types': id_types,
                    'date_fields': date_fields,
                    'sample_ids': [str(doc.get('_id')) for doc in sample_docs[:3]]
                }
                
            except Exception as e:
                status[collection] = {
                    'error': str(e)
                }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def migrate_timesheet_dates():
    """Migriert Timesheet-Datumsfelder von String zu Date-Objekten"""
    try:
        # Finde alle Timesheets mit String-Datumsfeldern
        timesheets = list(mongodb.db.timesheets.find({
            '$or': [
                {'created_at': {'$type': 'string'}},
                {'updated_at': {'$type': 'string'}}
            ]
        }))
        
        migrated_count = 0
        for ts in timesheets:
            update_data = {}
            
            # Konvertiere created_at
            if isinstance(ts.get('created_at'), str):
                try:
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            update_data['created_at'] = datetime.strptime(ts['created_at'], fmt)
                            break
                        except ValueError:
                            continue
                    # Wenn kein Format passt, verwende aktuelles Datum
                    if 'created_at' not in update_data:
                        update_data['created_at'] = datetime.now()
                except:
                    update_data['created_at'] = datetime.now()
            
            # Konvertiere updated_at
            if isinstance(ts.get('updated_at'), str):
                try:
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            update_data['updated_at'] = datetime.strptime(ts['updated_at'], fmt)
                            break
                        except ValueError:
                            continue
                    # Wenn kein Format passt, verwende aktuelles Datum
                    if 'updated_at' not in update_data:
                        update_data['updated_at'] = datetime.now()
                except:
                    update_data['updated_at'] = datetime.now()
            
            # Update nur wenn Änderungen vorhanden
            if update_data:
                result = mongodb.db.timesheets.update_one(
                    {'_id': ts['_id']},
                    {'$set': update_data}
                )
                if result.modified_count > 0:
                    migrated_count += 1
        
        return migrated_count
    except Exception as e:
        print(f"Fehler bei Timesheet-Migration: {e}")
        return 0

@bp.route('/timesheets')
@login_required
def timesheet_list():
    """Zeigt die Wochenberichte für den aktuellen Benutzer an (für alle Rollen mit timesheet_enabled)"""
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    
    # Führe Migration aus, falls noch nicht geschehen
    try:
        migrate_timesheet_dates()
    except Exception as e:
        # Migration-Fehler nicht blockieren, nur loggen
        print(f"Migration-Fehler (nicht kritisch): {e}")
    
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
                    '$cond': {
                        'if': {'$type': '$created_at'},
                        'then': {
                            '$cond': {
                                'if': {'$eq': [{'$type': '$created_at'}, 'date']},
                                'then': {
                                    '$dateToString': {
                                        'format': '%d.%m.%Y',
                                        'date': '$created_at'
                                    }
                                },
                                'else': '$created_at'
                            }
                        },
                        'else': '$created_at'
                    }
                },
                'updated_at_de': {
                    '$cond': {
                        'if': {'$type': '$updated_at'},
                        'then': {
                            '$cond': {
                                'if': {'$eq': [{'$type': '$updated_at'}, 'date']},
                                'then': {
                                    '$dateToString': {
                                        'format': '%d.%m.%Y',
                                        'date': '$updated_at'
                                    }
                                },
                                'else': '$updated_at'
                            }
                        },
                        'else': '$updated_at'
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
    # Für Date-Sortierung verwenden wir Python-Sortierung statt MongoDB-Sortierung
    # da die Felder möglicherweise als Strings gespeichert sind
    elif sort in ['created_desc', 'created_asc', 'updated_desc', 'updated_asc']:
        # Keine MongoDB-Sortierung für Date-Felder, wird später in Python gemacht
        pass
    
    if sort_stage:
        pipeline.append({'$sort': sort_stage})
    
    # MongoDB Aggregation ausführen
    timesheets = list(mongodb.db.timesheets.aggregate(pipeline))
    
    # Python-Sortierung für Date-Felder (falls MongoDB-Sortierung nicht möglich war)
    if sort in ['created_desc', 'created_asc', 'updated_desc', 'updated_asc']:
        def parse_date(date_value):
            """Sichere Datum-Parsing-Funktion"""
            if isinstance(date_value, datetime):
                return date_value
            elif isinstance(date_value, str):
                try:
                    # Versuche verschiedene Datum-Formate
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(date_value, fmt)
                        except ValueError:
                            continue
                    # Fallback: aktuelles Datum
                    return datetime.now()
                except:
                    return datetime.now()
            else:
                return datetime.now()
        
        reverse = sort.endswith('_desc')
        if sort.startswith('created'):
            timesheets.sort(key=lambda x: parse_date(x.get('created_at', datetime.now())), reverse=reverse)
        elif sort.startswith('updated'):
            timesheets.sort(key=lambda x: parse_date(x.get('updated_at', datetime.now())), reverse=reverse)
    
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

@bp.route('/teilnehmer/timesheets')
@teilnehmer_required
def teilnehmer_timesheet_list():
    """Spezielle Route für Teilnehmer zu den Wochenberichten"""
    return timesheet_list()

@bp.route('/timesheet/new', methods=['GET', 'POST'])
@login_required
def timesheet_create():
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
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
@login_required
def timesheet_edit(ts_id):
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    user_id = current_user.username
    
    # Konvertiere ts_id zu ObjectId
    try:
        object_id = convert_id_for_query(ts_id)
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
                         {'_id': convert_id_for_query(ts_id)}, 
                         {'$set': update_data})
        flash('Wochenplan aktualisiert.', 'success')
        return redirect(url_for('workers.timesheet_list'))
    return render_template('workers/timesheet.html', ts=ts, now=datetime.now())

@bp.route('/timesheet/<string:ts_id>/download')
@login_required
def timesheet_download(ts_id):
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    user_id = current_user.username
    
    # Konvertiere ts_id zu ObjectId
    try:
        object_id = convert_id_for_query(ts_id)
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

@bp.route('/timesheet/<ts_id>/delete', methods=['POST'])
@login_required
def timesheet_delete(ts_id):
    # Robuste ID-Behandlung für verschiedene ID-Typen
    ts = find_document_by_id('timesheets', ts_id)
    if not ts:
        flash('Wochenbericht nicht gefunden.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    # Nur Besitzer oder Admin darf löschen
    if ts.get('user_id') != current_user.username and not current_user.is_admin:
        flash('Sie dürfen nur Ihre eigenen Wochenberichte löschen.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    
    # Verwende die ID für alle Abfragen
    ts_id_for_query = convert_id_for_query(ts_id)
    mongodb.delete_one('timesheets', {'_id': ts_id_for_query})
    flash('Wochenbericht wurde gelöscht.', 'success')
    return redirect(url_for('workers.timesheet_list'))