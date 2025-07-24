from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, render_template_string, current_app
from app.models.mongodb_models import MongoDBTicket
from app.models.mongodb_database import mongodb
from app.utils.decorators import login_required, admin_required, not_teilnehmer_required
from app.utils.database_helpers import get_ticket_categories_from_settings, get_categories_from_settings, get_next_ticket_number
from app.models.user import User
import logging
from datetime import datetime
from flask_login import current_user
from docxtpl import DocxTemplate
import os
from bson import ObjectId
from typing import Union

bp = Blueprint('tickets', __name__, url_prefix='/tickets')

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

def normalize_id_for_database(id_value):
    """
    Normalisiert eine ID für die Datenbank - konvertiert alles zu String
    """
    if isinstance(id_value, ObjectId):
        return str(id_value)
    elif isinstance(id_value, str):
        return id_value
    else:
        return str(id_value)

def find_document_by_id(collection: str, id_value: str):
    """
    Findet ein Dokument in einer Collection mit robuster ID-Behandlung.
    Versucht verschiedene ID-Formate: String, ObjectId, convert_id_for_query
    """
    print(f"DEBUG: Suche Dokument in Collection '{collection}' mit ID: {id_value}")
    
    # Versuche zuerst mit String-ID
    doc = mongodb.find_one(collection, {'_id': id_value})
    if doc:
        print(f"DEBUG: Dokument mit String-ID gefunden: {doc.get('title', doc.get('name', 'Unknown'))}")
        return doc
    
    # Falls nicht gefunden, versuche mit ObjectId
    try:
        from bson import ObjectId
        obj_id = ObjectId(id_value)
        doc = mongodb.find_one(collection, {'_id': obj_id})
        if doc:
            print(f"DEBUG: Dokument mit ObjectId gefunden: {doc.get('title', doc.get('name', 'Unknown'))}")
            return doc
    except Exception as e:
        print(f"DEBUG: ObjectId-Konvertierung fehlgeschlagen: {e}")
    
    # Falls immer noch nicht gefunden, versuche mit convert_id_for_query
    doc = mongodb.find_one(collection, {'_id': convert_id_for_query(id_value)})
    if doc:
        print(f"DEBUG: Dokument mit convert_id_for_query gefunden: {doc.get('title', doc.get('name', 'Unknown'))}")
    else:
        print(f"DEBUG: Kein Dokument gefunden für ID: {id_value}")
    
    return doc

@bp.route('/debug/tickets')
@login_required
def debug_tickets():
    """Debug-Route um alle Tickets anzuzeigen"""
    try:
        all_tickets = mongodb.find('tickets', {})
        ticket_info = []
        
        for ticket in all_tickets:
            ticket_info.append({
                'id': str(ticket.get('_id')),
                'id_type': type(ticket.get('_id')).__name__,
                'title': ticket.get('title', 'No Title'),
                'status': ticket.get('status', 'Unknown'),
                'created_by': ticket.get('created_by', 'Unknown'),
                'ticket_number': ticket.get('ticket_number', 'No Number')
            })
        
        return jsonify({
            'total_tickets': len(ticket_info),
            'tickets': ticket_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/debug/test-ticket/<ticket_id>')
@login_required
def test_ticket(ticket_id):
    """Testet das Finden eines spezifischen Tickets"""
    try:
        print(f"DEBUG: Teste Ticket-ID: {ticket_id}")
        
        # Teste verschiedene Suchmethoden
        results = {}
        
        # Methode 1: Direkte String-Suche
        ticket = mongodb.find_one('tickets', {'_id': ticket_id})
        results['string_search'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None
        }
        
        # Methode 2: ObjectId-Suche
        try:
            from bson import ObjectId
            obj_id = ObjectId(ticket_id)
            ticket = mongodb.find_one('tickets', {'_id': obj_id})
            results['objectid_search'] = {
                'found': ticket is not None,
                'title': ticket.get('title') if ticket else None
            }
        except Exception as e:
            results['objectid_search'] = {
                'found': False,
                'error': str(e)
            }
        
        # Methode 3: find_document_by_id
        ticket = find_document_by_id('tickets', ticket_id)
        results['find_document_by_id'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None
        }
        
        return jsonify({
            'ticket_id': ticket_id,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/debug/normalize-ticket-ids')
@login_required
def normalize_ticket_ids():
    """Normalisiert alle Ticket-IDs zu Strings"""
    try:
        from bson import ObjectId
        
        all_tickets = mongodb.find('tickets', {})
        updated_count = 0
        
        for ticket in all_tickets:
            ticket_id = ticket.get('_id')
            
            # Falls die ID ein ObjectId ist, konvertiere sie zu String
            if isinstance(ticket_id, ObjectId):
                string_id = str(ticket_id)
                
                # Erstelle ein neues Dokument mit String-ID
                new_ticket = ticket.copy()
                new_ticket['_id'] = string_id
                
                # Lösche das alte Dokument und füge das neue ein
                mongodb.delete_one('tickets', {'_id': ticket_id})
                mongodb.insert_one('tickets', new_ticket)
                
                updated_count += 1
                print(f"Ticket-ID normalisiert: {ticket.get('title', 'Unknown')} von {ticket_id} zu {string_id}")
        
        return jsonify({
            'status': 'success',
            'message': f'{updated_count} Ticket-IDs normalisiert',
            'updated_count': updated_count
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/debug/normalize-all-ids')
@login_required
def normalize_all_ids():
    """Normalisiert alle IDs in allen Collections zu Strings"""
    try:
        from bson import ObjectId
        
        collections_to_normalize = [
            'tickets', 'users', 'tools', 'consumables', 'workers',
            'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit'
        ]
        
        total_updated = 0
        results = {}
        
        for collection_name in collections_to_normalize:
            try:
                documents = mongodb.find(collection_name, {})
                updated_count = 0
                
                for doc in documents:
                    doc_id = doc.get('_id')
                    
                    # Falls die ID ein ObjectId ist, konvertiere sie zu String
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)
                        
                        # Erstelle ein neues Dokument mit String-ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id
                        
                        # Lösche das alte Dokument und füge das neue ein
                        mongodb.delete_one(collection_name, {'_id': doc_id})
                        mongodb.insert_one(collection_name, new_doc)
                        
                        updated_count += 1
                
                results[collection_name] = updated_count
                total_updated += updated_count
                print(f"Collection {collection_name}: {updated_count} IDs normalisiert")
                
            except Exception as e:
                results[collection_name] = f"Fehler: {str(e)}"
                print(f"Fehler bei Collection {collection_name}: {e}")
        
        return jsonify({
            'status': 'success',
            'message': f'{total_updated} IDs in allen Collections normalisiert',
            'total_updated': total_updated,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/debug/test-update-ticket/<ticket_id>')
@login_required
def test_update_ticket(ticket_id):
    """Testet die update_ticket-Route mit einer spezifischen Ticket-ID"""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
        
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(ticket_id)
        
        # Teste ein einfaches Update
        test_data = {'priority': 'normal', 'updated_at': datetime.now()}
        result = mongodb.update_one('tickets', {'_id': ticket_id_for_query}, {'$set': test_data})
        
        return jsonify({
            'success': True,
            'message': 'Test-Update erfolgreich',
            'ticket_id': ticket_id,
            'ticket_id_for_query': str(ticket_id_for_query),
            'ticket_id_type': type(ticket_id_for_query).__name__,
            'update_result': str(result)
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': str(e),
            'ticket_id': ticket_id
        })

@bp.route('/debug/test-mongodb')
@login_required
def test_mongodb():
    """Testet die MongoDB-Verbindung und -Operationen"""
    try:
        # Teste einfache Abfrage
        count = mongodb.count_documents('tickets', {})
        
        # Teste einfaches Update
        test_ticket = mongodb.find_one('tickets', {})
        if test_ticket:
            test_id = test_ticket['_id']
            result = mongodb.update_one('tickets', {'_id': test_id}, {'$set': {'test_field': 'test_value'}})
            
            # Entferne das Test-Feld wieder
            mongodb.update_one('tickets', {'_id': test_id}, {'$unset': {'test_field': ''}})
            
            return jsonify({
                'success': True,
                'message': 'MongoDB-Verbindung funktioniert',
                'ticket_count': count,
                'test_update_result': str(result)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Keine Tickets in der Datenbank gefunden'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'MongoDB-Fehler: {str(e)}'
        })

@bp.route('/debug/test-specific-ticket/<ticket_id>')
@login_required
def test_specific_ticket(ticket_id):
    """Testet eine spezifische Ticket-ID mit allen Methoden"""
    try:
        results = {}
        
        # Teste find_document_by_id
        ticket = find_document_by_id('tickets', ticket_id)
        results['find_document_by_id'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None,
            'id': str(ticket.get('_id')) if ticket else None
        }
        
        # Teste convert_id_for_query
        converted_id = convert_id_for_query(ticket_id)
        results['convert_id_for_query'] = {
            'converted_id': str(converted_id),
            'type': type(converted_id).__name__
        }
        
        # Teste direkte MongoDB-Abfrage
        direct_result = mongodb.find_one('tickets', {'_id': converted_id})
        results['direct_mongodb_query'] = {
            'found': direct_result is not None,
            'title': direct_result.get('title') if direct_result else None
        }
        
        # Teste einfaches Update
        if ticket:
            test_data = {'test_update': datetime.now()}
            update_result = mongodb.update_one('tickets', {'_id': converted_id}, {'$set': test_data})
            
            # Entferne das Test-Feld wieder
            mongodb.update_one('tickets', {'_id': converted_id}, {'$unset': {'test_update': ''}})
            
            results['test_update'] = {
                'success': bool(update_result),
                'result': str(update_result)
            }
        
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'ticket_id': ticket_id
        })

@bp.route('/debug/test-update-operation/<ticket_id>')
@login_required
def test_update_operation(ticket_id):
    """Testet die Update-Operation für ein spezifisches Ticket"""
    try:
        print(f"DEBUG: Teste Update-Operation für Ticket-ID: {ticket_id}")
        
        # Finde das Ticket
        ticket = find_document_by_id('tickets', ticket_id)
        if not ticket:
            return jsonify({'error': 'Ticket nicht gefunden'}), 404
        
        actual_ticket_id = ticket.get('_id')
        print(f"DEBUG: Gefundene Ticket-ID: {actual_ticket_id}")
        print(f"DEBUG: Ticket-ID Typ: {type(actual_ticket_id).__name__}")
        
        # Teste verschiedene Update-Methoden
        results = {}
        
        # Methode 1: Direkte MongoDB-Operation
        try:
            result = mongodb.db.tickets.update_one(
                {'_id': actual_ticket_id},
                {'$set': {'test_field': 'test_value', 'updated_at': datetime.now()}}
            )
            results['direct_mongodb'] = {
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'success': result.modified_count > 0
            }
        except Exception as e:
            results['direct_mongodb'] = {'error': str(e)}
        
        # Methode 2: Wrapper-Methode
        try:
            result = mongodb.update_one('tickets', {'_id': actual_ticket_id}, {'$set': {'test_field2': 'test_value2'}})
            results['wrapper_method'] = {
                'result': result,
                'result_type': type(result).__name__
            }
        except Exception as e:
            results['wrapper_method'] = {'error': str(e)}
        
        # Methode 3: Mit verschiedenen ID-Formaten
        try:
            # Versuche mit String-ID
            string_result = mongodb.update_one('tickets', {'_id': str(actual_ticket_id)}, {'$set': {'test_field3': 'test_value3'}})
            results['string_id'] = {
                'result': string_result,
                'result_type': type(string_result).__name__
            }
        except Exception as e:
            results['string_id'] = {'error': str(e)}
        
        return jsonify({
            'ticket_id': ticket_id,
            'actual_ticket_id': str(actual_ticket_id),
            'actual_ticket_id_type': type(actual_ticket_id).__name__,
            'results': results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/debug/analyze-ticket/<ticket_id>')
def analyze_ticket(ticket_id):
    """Analysiert ein Ticket ohne Authentifizierung (nur für Debugging)"""
    try:
        print(f"DEBUG: Analysiere Ticket-ID: {ticket_id}")
        
        # Teste verschiedene Suchmethoden
        results = {}
        
        # Methode 1: Direkte String-Suche
        ticket = mongodb.find_one('tickets', {'_id': ticket_id})
        results['string_search'] = {
            'found': ticket is not None,
            'title': ticket.get('title') if ticket else None,
            'id': str(ticket.get('_id')) if ticket else None,
            'id_type': type(ticket.get('_id')).__name__ if ticket else None
        }
        
        # Methode 2: ObjectId-Suche
        try:
            from bson import ObjectId
            obj_id = ObjectId(ticket_id)
            ticket = mongodb.find_one('tickets', {'_id': obj_id})
            results['objectid_search'] = {
                'found': ticket is not None,
                'title': ticket.get('title') if ticket else None,
                'id': str(ticket.get('_id')) if ticket else None,
                'id_type': type(ticket.get('_id')).__name__ if ticket else None
            }
        except Exception as e:
            results['objectid_search'] = {
                'found': False,
                'error': str(e)
            }
        
        # Methode 3: Direkte MongoDB-Abfrage
        try:
            direct_ticket = mongodb.db.tickets.find_one({'_id': ticket_id})
            results['direct_mongodb_string'] = {
                'found': direct_ticket is not None,
                'title': direct_ticket.get('title') if direct_ticket else None,
                'id': str(direct_ticket.get('_id')) if direct_ticket else None,
                'id_type': type(direct_ticket.get('_id')).__name__ if direct_ticket else None
            }
        except Exception as e:
            results['direct_mongodb_string'] = {'error': str(e)}
        
        # Methode 4: Direkte MongoDB-Abfrage mit ObjectId
        try:
            from bson import ObjectId
            obj_id = ObjectId(ticket_id)
            direct_ticket = mongodb.db.tickets.find_one({'_id': obj_id})
            results['direct_mongodb_objectid'] = {
                'found': direct_ticket is not None,
                'title': direct_ticket.get('title') if direct_ticket else None,
                'id': str(direct_ticket.get('_id')) if direct_ticket else None,
                'id_type': type(direct_ticket.get('_id')).__name__ if direct_ticket else None
            }
        except Exception as e:
            results['direct_mongodb_objectid'] = {'error': str(e)}
        
        # Teste Update-Operationen
        update_results = {}
        
        # Finde das Ticket für Updates
        found_ticket = None
        found_id = None
        
        if results['string_search']['found']:
            found_ticket = mongodb.find_one('tickets', {'_id': ticket_id})
            found_id = ticket_id
        elif results['objectid_search']['found']:
            found_ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
            found_id = ObjectId(ticket_id)
        
        if found_ticket:
            # Teste Update mit String-ID
            try:
                result = mongodb.db.tickets.update_one(
                    {'_id': ticket_id},
                    {'$set': {'debug_test': 'string_update'}}
                )
                update_results['string_update'] = {
                    'matched_count': result.matched_count,
                    'modified_count': result.modified_count,
                    'success': result.modified_count > 0
                }
                # Entferne das Test-Feld
                mongodb.db.tickets.update_one(
                    {'_id': ticket_id},
                    {'$unset': {'debug_test': ''}}
                )
            except Exception as e:
                update_results['string_update'] = {'error': str(e)}
            
            # Teste Update mit ObjectId
            try:
                result = mongodb.db.tickets.update_one(
                    {'_id': ObjectId(ticket_id)},
                    {'$set': {'debug_test': 'objectid_update'}}
                )
                update_results['objectid_update'] = {
                    'matched_count': result.matched_count,
                    'modified_count': result.modified_count,
                    'success': result.modified_count > 0
                }
                # Entferne das Test-Feld
                mongodb.db.tickets.update_one(
                    {'_id': ObjectId(ticket_id)},
                    {'$unset': {'debug_test': ''}}
                )
            except Exception as e:
                update_results['objectid_update'] = {'error': str(e)}
        
        return jsonify({
            'ticket_id': ticket_id,
            'search_results': results,
            'update_results': update_results
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Erstellt ein neues Ticket."""
    # Verwende den TicketService
    from app.services.ticket_service import TicketService
    ticket_service = TicketService()
    
    if request.method == 'POST':
        try:
            # Prüfe ob die Anfrage JSON enthält
            if request.is_json:
                data = request.get_json()
            else:
                data = {
                    'title': request.form.get('title'),
                    'description': request.form.get('description'),
                    'priority': request.form.get('priority', 'normal'),
                    'category': request.form.get('category'),
                    'due_date': request.form.get('due_date'),
                    'estimated_time': request.form.get('estimated_time')
                }

            # Ticket erstellen
            success, message, ticket_id = ticket_service.create_ticket(data, current_user.username)

            if success:
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': message,
                        'ticket_id': ticket_id
                    })
                flash(message, 'success')
                return redirect(url_for('tickets.create'))
            else:
                if request.is_json:
                    return jsonify({'success': False, 'message': message}), 400
                flash(message, 'error')
                return redirect(url_for('tickets.create'))
                
        except Exception as e:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': f'Fehler beim Erstellen des Tickets: {str(e)}'
                }), 500
            flash(f'Fehler beim Erstellen des Tickets: {str(e)}', 'error')
            return redirect(url_for('tickets.create'))
    
    # Verwende den TicketService für alle Ticket-Operationen
    print(f"DEBUG: Lade Tickets für Benutzer: {current_user.username}, Rolle: {current_user.role}")
    tickets_data = ticket_service.get_tickets_by_user(current_user.username, current_user.role)
    open_tickets = tickets_data['open_tickets']
    assigned_tickets = tickets_data['assigned_tickets']
    all_tickets = tickets_data['all_tickets']
    
    print(f"DEBUG: Route erhalten: {len(open_tickets)} offene, {len(assigned_tickets)} zugewiesene, {len(all_tickets)} alle Tickets")
    
    # Debug: Zeige Details der ersten Tickets
    if open_tickets:
        print(f"DEBUG: Erstes offenes Ticket: {open_tickets[0].get('title', 'Kein Titel')} (ID: {open_tickets[0].get('id', 'Keine ID')})")
    if assigned_tickets:
        print(f"DEBUG: Erstes zugewiesenes Ticket: {assigned_tickets[0].get('title', 'Kein Titel')} (ID: {assigned_tickets[0].get('id', 'Keine ID')})")
    
    # Hole alle Kategorien aus der settings Collection
    categories = get_ticket_categories_from_settings()
    
    # Für Admins und Mitarbeiter: Hole auch alle Mitarbeiter
    workers = []
    if current_user.role in ['admin', 'mitarbeiter']:
        workers = list(mongodb.find('users', {'role': {'$in': ['admin', 'mitarbeiter']}}))
    
    print(f"DEBUG: Rendere Template mit {len(open_tickets)} offenen, {len(assigned_tickets)} zugewiesenen, {len(all_tickets)} allen Tickets")
            
    return render_template('tickets/create.html', 
                         assigned_tickets=assigned_tickets,
                         open_tickets=open_tickets,
                         all_tickets=all_tickets,
                         workers=workers,
                         show_all_tickets=current_user.role in ['admin', 'mitarbeiter'],
                         categories=categories,
                         now=datetime.now(),
                         status_colors={
                             'offen': 'info',
                             'in_bearbeitung': 'warning',
                             'wartet_auf_antwort': 'warning',
                             'gelöst': 'success',
                             'geschlossen': 'ghost'
                         },
                         priority_colors={
                             'niedrig': 'secondary',
                             'normal': 'primary',
                             'hoch': 'error',
                             'dringend': 'error'
                         })

@bp.route('/view/<ticket_id>')
@login_required
def view(ticket_id):
    """Zeigt die Details eines Tickets für den Benutzer."""
    logging.info(f"Lade Ticket {ticket_id} für Benutzer {current_user.username}")
    
    # Robuste ID-Behandlung für verschiedene ID-Typen
    ticket = find_document_by_id('tickets', ticket_id)
    
    if not ticket:
        logging.error(f"Ticket {ticket_id} nicht gefunden")
        flash('Ticket nicht gefunden.', 'error')
        return redirect(url_for('tickets.create'))
        
    # Prüfe ob der Benutzer berechtigt ist, das Ticket zu sehen
    if (
        ticket.get('created_by') != current_user.username
        and ticket.get('assigned_to') not in [None, '', current_user.username]
        and current_user.role not in ['admin', 'mitarbeiter']
    ):
        logging.error(f"Benutzer {current_user.username} hat keine Berechtigung für Ticket {ticket_id}")
        flash('Sie haben keine Berechtigung, dieses Ticket zu sehen.', 'error')
        return redirect(url_for('tickets.create'))
    
    # Hole die Nachrichten für das Ticket
    logging.info(f"Hole Nachrichten für Ticket {ticket_id}")
    
    try:
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(ticket_id)
        
        messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id_for_query})
        messages = list(messages)
        
        # Sortiere Nachrichten nach Datum (älteste zuerst)
        messages.sort(key=lambda x: x.get('created_at', datetime.min))
        
        # Formatiere Datum für jede Nachricht
        for msg in messages:
            if isinstance(msg.get('created_at'), datetime):
                msg['formatted_date'] = msg['created_at'].strftime('%d.%m.%Y %H:%M')
            else:
                msg['formatted_date'] = str(msg.get('created_at', ''))
        
        logging.info(f"Nachrichtenabfrage ergab {len(messages)} Nachrichten")
        
        # Füge id-Feld hinzu (für Template-Kompatibilität)
        ticket['id'] = str(ticket['_id'])
        
        # Hole die Auftragsdetails
        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query})
        
        # Hole Materialliste
        material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query}))
        
        # Hole Arbeitsliste
        arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': ticket_id_for_query}))
        
        # Berechne die Summe der Arbeitsstunden aus der Arbeitsliste
        total_arbeitsstunden = 0
        if arbeit_list:
            for arbeit in arbeit_list:
                arbeitsstunden = arbeit.get('arbeitsstunden', 0)
                if isinstance(arbeitsstunden, (int, float)):
                    total_arbeitsstunden += arbeitsstunden
                elif isinstance(arbeitsstunden, str):
                    try:
                        total_arbeitsstunden += float(arbeitsstunden)
                    except ValueError:
                        pass
        
        # Formatiere das Fertigstellungstermin-Datum
        if auftrag_details and auftrag_details.get('fertigstellungstermin'):
            try:
                fertigstellungstermin = auftrag_details['fertigstellungstermin']
                if isinstance(fertigstellungstermin, str):
                    # Versuche verschiedene Datumsformate zu parsen
                    if 'T' in fertigstellungstermin:
                        fertigstellungstermin = datetime.strptime(fertigstellungstermin, '%Y-%m-%dT%H:%M')
                    else:
                        fertigstellungstermin = datetime.strptime(fertigstellungstermin, '%Y-%m-%d')
                    auftrag_details['fertigstellungstermin_formatted'] = fertigstellungstermin.strftime('%d.%m.%Y')
                elif isinstance(fertigstellungstermin, datetime):
                    auftrag_details['fertigstellungstermin_formatted'] = fertigstellungstermin.strftime('%d.%m.%Y')
                else:
                    auftrag_details['fertigstellungstermin_formatted'] = str(fertigstellungstermin)
            except (ValueError, TypeError):
                auftrag_details['fertigstellungstermin_formatted'] = str(auftrag_details['fertigstellungstermin'])
        
        # Füge die berechneten Arbeitsstunden zu den Auftragsdetails hinzu
        if auftrag_details:
            auftrag_details['total_arbeitsstunden'] = total_arbeitsstunden
            
            # Extrahiere nur die ausgeführten Arbeiten (ohne Stunden und Leistungskategorie)
            if auftrag_details.get('ausgefuehrte_arbeiten'):
                arbeit_zeilen = auftrag_details['ausgefuehrte_arbeiten'].split('\n')
                nur_arbeiten = []
                for zeile in arbeit_zeilen:
                    if zeile.strip():
                        teile = zeile.split('|')
                        if len(teile) > 0 and teile[0].strip():
                            nur_arbeiten.append(teile[0].strip())
                auftrag_details['ausgefuehrte_arbeiten_nur_text'] = '\n'.join(nur_arbeiten)
        
        # Hole alle Kategorien aus der settings Collection
        categories = get_ticket_categories_from_settings()
        
        # Hole alle Benutzer für die Zuweisung (falls benötigt)
        users = mongodb.find('users', {'is_active': True})
        users = [dict(user) for user in users]
        
        return render_template('tickets/view.html', 
                             ticket=ticket, 
                             messages=messages,
                             auftrag_details=auftrag_details,
                             categories=categories,
                             workers=users,
                             status_colors={
                                 'offen': 'info',
                                 'in_bearbeitung': 'warning',
                                 'wartet_auf_antwort': 'warning',
                                 'gelöst': 'success',
                                 'geschlossen': 'ghost'
                             })
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Nachrichten: {str(e)}")
        flash('Fehler beim Laden der Nachrichten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/<ticket_id>/message', methods=['POST'])
@login_required
def add_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu"""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', ticket_id)
        if not ticket:
            logging.error(f"Ticket {ticket_id} nicht gefunden")
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
        
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(ticket_id)
        
        # Hole die Nachricht aus dem Request
        if not request.is_json:
            logging.error("Ungültiges Anfrageformat (kein JSON)")
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400
            
        data = request.get_json()
        message = data['message'].strip()
        if not message:
            logging.error("Leere Nachricht")
            return jsonify({'success': False, 'message': 'Nachricht darf nicht leer sein'}), 400

        logging.info(f"Versuche Nachricht zu speichern: Ticket {ticket_id}, Benutzer {current_user.username}, Nachricht: {message}")

        # Verwende mongodb.insert_one für die Nachrichtenspeicherung
        message_data = {
            'ticket_id': ticket_id_for_query,
            'message': message,
            'sender': current_user.username,
            'created_at': datetime.now()
        }
        
        result = mongodb.insert_one('ticket_messages', message_data)
        
        logging.info(f"Nachricht erfolgreich gespeichert")

        # Hole die aktuelle Zeit für die Antwort
        created_at = datetime.now()
        formatted_date = created_at.strftime('%d.%m.%Y, %H:%M')

        return jsonify({
            'success': True,
            'message': {
                'text': message,
                'sender': current_user.username,
                'created_at': formatted_date
            }
        })

    except Exception as e:
        logging.error(f"Fehler beim Hinzufügen der Nachricht: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Ein Fehler ist aufgetreten'}), 500

@bp.route('/<id>')
@login_required
def detail(id):
    """Zeigt die Details eines Tickets."""
    print(f"DEBUG: Ticket-Detail aufgerufen für ID: {id}")
    
    # Robuste ID-Behandlung für verschiedene ID-Typen
    ticket = find_document_by_id('tickets', id)
    
    if not ticket:
        print(f"DEBUG: Ticket nicht gefunden für ID: {id}")
        return render_template('404.html'), 404
    
    # Prüfe Berechtigungen: Admins/Mitarbeiter können alle Tickets sehen, normale User nur ihre eigenen oder zugewiesenen
    if current_user.role not in ['admin', 'mitarbeiter'] and ticket.get('created_by') != current_user.username and ticket.get('assigned_to') != current_user.username:
        flash('Sie haben keine Berechtigung, dieses Ticket zu sehen.', 'error')
        return redirect(url_for('tickets.create'))
    
    # Füge id-Feld hinzu (für Template-Kompatibilität)
    ticket['id'] = str(ticket['_id'])
    
    # Konvertiere alle Datumsfelder zu datetime-Objekten
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
        
    # Hole die Notizen für das Ticket
    notes = mongodb.find('ticket_notes', {'ticket_id': convert_id_for_query(id)})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': convert_id_for_query(id)})

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': convert_id_for_query(id)})
    
    # Hole Materialliste
    material_list = list(mongodb.find('auftrag_material', {'ticket_id': convert_id_for_query(id)}))
    
    # Hole Arbeitsliste
    arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': convert_id_for_query(id)}))

    # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
    users = mongodb.find('users', {'is_active': True})
    users = [dict(user) for user in users]

    # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
    assigned_users = mongodb.find('ticket_assignments', {'ticket_id': convert_id_for_query(id)})

    # Hole alle Kategorien aus der settings Collection
    categories = get_ticket_categories_from_settings()

    # Bestimme Berechtigungen
    can_edit = current_user.role in ['admin', 'mitarbeiter'] or ticket.get('created_by') == current_user.username
    can_assign = current_user.role in ['admin', 'mitarbeiter']
    can_change_status = current_user.role in ['admin', 'mitarbeiter']
    can_delete = current_user.role in ['admin', 'mitarbeiter']

    return render_template('tickets/detail.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         users=users,
                         assigned_users=assigned_users,
                         auftrag_details=auftrag_details,
                         material_list=material_list,
                         categories=categories,
                         can_edit=can_edit,
                         can_assign=can_assign,
                         can_change_status=can_change_status,
                         can_delete=can_delete,
                         now=datetime.now())

@bp.route('/<id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Löscht ein Ticket."""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404
            
        # Prüfe Berechtigungen: Nur Admins und Mitarbeiter können Tickets löschen
        if current_user.role not in ['admin', 'mitarbeiter']:
            return jsonify({
                'success': False,
                'message': 'Sie haben keine Berechtigung, Tickets zu löschen'
            }), 403
        
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)
            
        # Lösche das Ticket
        if not mongodb.delete_one('tickets', {'_id': ticket_id_for_query}):
            return jsonify({
                'success': False,
                'message': 'Fehler beim Löschen des Tickets'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Ticket wurde gelöscht'
        })
        
    except Exception as e:
        logging.error(f"Fehler beim Löschen des Tickets #{id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Löschen des Tickets'
        }), 500

@bp.route('/<id>/auftrag-details-modal')
@login_required
def auftrag_details_modal(id):
    # Robuste ID-Behandlung für verschiedene ID-Typen
    ticket = find_document_by_id('tickets', id)
    
    if not ticket:
        return render_template('404.html'), 404
    
    # Verwende die Ticket-ID für alle Abfragen
    ticket_id_for_query = convert_id_for_query(id)
    
    # Füge id-Feld hinzu (für Template-Kompatibilität)
    ticket['id'] = str(ticket['_id'])
    
    # Konvertiere alle Datumsfelder zu datetime-Objekten
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
        
    # Hole die Notizen für das Ticket
    notes = mongodb.find('ticket_notes', {'ticket_id': ticket_id_for_query})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id_for_query})

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query})
    
    # Hole Materialliste
    material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query}))
    
    # Hole Arbeitsliste
    arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': convert_id_for_query(id)}))

    return render_template('tickets/auftrag_details_modal.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         auftrag_details=auftrag_details,
                         material_list=material_list,
                         arbeit_list=arbeit_list)

@bp.route('/<id>/update-status', methods=['POST'])
@login_required
def update_status(id):
    """Aktualisiert den Status eines Tickets und weist es ggf. automatisch zu"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({'success': False, 'message': 'Status ist erforderlich'}), 400

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        update_fields = {'status': new_status, 'updated_at': datetime.now()}

        # Automatische Zuweisung: Wenn Status von 'offen' auf etwas anderes wechselt und noch niemand zugewiesen ist
        if new_status != 'offen' and (not ticket.get('assigned_to')):
            update_fields['assigned_to'] = current_user.username
        # Wenn Status auf 'offen' gesetzt wird, Zuweisung entfernen
        elif new_status == 'offen':
            update_fields['assigned_to'] = None

        # Verwende die gleiche ID für das Update
        result = mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': update_fields})
        print(f"DEBUG: update_one Erfolg: {result}")

        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren des Status'})

        # Spezielle Nachricht bei automatischer Zuweisung
        if new_status != 'offen' and (not ticket.get('assigned_to')):
            return jsonify({
                'success': True, 
                'message': f'Status erfolgreich auf "{new_status}" geändert. Ticket wurde automatisch Ihnen zugewiesen.'
            })
        elif new_status == 'offen':
            return jsonify({
                'success': True, 
                'message': f'Status erfolgreich auf "{new_status}" geändert. Zuweisung wurde entfernt.'
            })
        else:
            return jsonify({'success': True, 'message': 'Status erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<id>/update-assignment', methods=['POST'])
@login_required
def update_assignment(id):
    """Aktualisiert die Zuweisung eines Tickets"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        assigned_to = data.get('assigned_to')
        
        # Wenn assigned_to leer ist, setze es auf None
        if not assigned_to or assigned_to == "":
            assigned_to = None

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Aktualisiere die Zuweisung direkt im Ticket
        result = mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': {'assigned_to': assigned_to, 'updated_at': datetime.now()}})
        
        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Zuweisung'})

        return jsonify({'success': True, 'message': 'Zuweisung erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Zuweisung: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<id>/update-due-date', methods=['POST'])
@login_required
def update_due_date(id):
    """Aktualisiert das Fälligkeitsdatum eines Tickets"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        due_date = data.get('due_date')
        
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Verarbeite due_date
        update_data = {'updated_at': datetime.now()}
        if due_date:
            try:
                # Versuche verschiedene Datumsformate zu parsen
                if 'T' in due_date:
                    due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                else:
                    due_date = datetime.strptime(due_date, '%Y-%m-%d')
                update_data['due_date'] = due_date
            except ValueError as e:
                return jsonify({'success': False, 'message': 'Ungültiges Datumsformat'}), 400
        else:
            update_data['due_date'] = None

        # Führe das Update aus
        result = mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': update_data})
        
        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren des Fälligkeitsdatums'})

        return jsonify({'success': True, 'message': 'Fälligkeitsdatum erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Fälligkeitsdatums: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<id>/update-details', methods=['POST'])
@login_required
def update_details(id):
    """Aktualisiert die Auftragsdetails eines Tickets"""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        if not ticket:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
            else:
                flash('Ticket nicht gefunden', 'error')
                return redirect(url_for('tickets.create'))
        
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)
        
        # Verarbeite die Daten je nach Request-Typ
        if request.is_json:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400
        else:
            # Formular-Daten verarbeiten
            form_data = request.form.to_dict()
            data = {}
            
            # Basis-Formulardaten
            for key, value in form_data.items():
                data[key] = value
            
            # Verarbeite den Auftraggeber-Typ (Radio-Button)
            auftraggeber_typ = data.get('auftraggeber_typ', '')
            data['auftraggeber_intern'] = auftraggeber_typ == 'intern'
            data['auftraggeber_extern'] = auftraggeber_typ == 'extern'
            
            # Materialliste aus Formular sammeln
            material_list = []
            material_names = request.form.getlist('material')
            material_mengen = request.form.getlist('menge')
            material_preise = request.form.getlist('einzelpreis')
            
            for i in range(len(material_names)):
                if material_names[i] or material_mengen[i] or material_preise[i]:
                    material_list.append({
                        'material': material_names[i],
                        'menge': float(material_mengen[i]) if material_mengen[i] else 0,
                        'einzelpreis': float(material_preise[i]) if material_preise[i] else 0
                    })
            
            # Arbeitsliste aus Formular sammeln
            arbeit_list = []
            arbeit_names = request.form.getlist('arbeit')
            arbeit_stunden = request.form.getlist('arbeitsstunden')
            arbeit_kategorien = request.form.getlist('leistungskategorie')
            
            for i in range(len(arbeit_names)):
                if arbeit_names[i] or arbeit_stunden[i] or arbeit_kategorien[i]:
                    arbeit_list.append({
                        'arbeit': arbeit_names[i],
                        'arbeitsstunden': float(arbeit_stunden[i]) if arbeit_stunden[i] else 0,
                        'leistungskategorie': arbeit_kategorien[i]
                    })
            
            data['material_list'] = material_list
            data['arbeit_list'] = arbeit_list

        logging.info(f"Empfangene Daten für Ticket {id}: {data}")
        
        # Verarbeite ausgeführte Arbeiten
        arbeit_list = data.get('arbeit_list', [])
        
        # Filtere nur wirklich leere Zeilen heraus (alle Felder leer)
        filtered_arbeit_list = []
        for arbeit in arbeit_list:
            arbeit_name = arbeit.get('arbeit', '').strip()
            arbeitsstunden = arbeit.get('arbeitsstunden', 0)
            leistungskategorie = arbeit.get('leistungskategorie', '').strip()
            
            # Nur hinzufügen wenn mindestens ein Feld ausgefüllt ist
            if arbeit_name or arbeitsstunden > 0 or leistungskategorie:
                filtered_arbeit_list.append(arbeit)
        
        ausgefuehrte_arbeiten = '\n'.join([
            f"{arbeit.get('arbeit', '')}|{arbeit.get('arbeitsstunden', '')}|{arbeit.get('leistungskategorie', '')}"
            for arbeit in filtered_arbeit_list
        ])
        logging.info(f"Verarbeitete ausgeführte Arbeiten: {ausgefuehrte_arbeiten}")
        
        # Bereite die Auftragsdetails vor
        auftrag_details_daten = {
            'ticket_id': ticket_id_for_query,
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': data.get('auftraggeber_intern', False),
            'auftraggeber_extern': data.get('auftraggeber_extern', False),
            'auftraggeber_name': data.get('auftraggeber_name', ''),
            'kontakt': data.get('kontakt', ''),
            'auftragsbeschreibung': data.get('auftragsbeschreibung', ''),
            'ausgefuehrte_arbeiten': ausgefuehrte_arbeiten,
            'fertigstellungstermin': data.get('fertigstellungstermin'),
            'gesamtsumme': data.get('gesamtsumme', 0)
        }
        
        # Speichere oder aktualisiere die Auftragsdetails
        existing_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query})
        if existing_details:
            mongodb.update_one('auftrag_details', {'ticket_id': ticket_id_for_query}, {'$set': auftrag_details_daten})
        else:
            mongodb.insert_one('auftrag_details', auftrag_details_daten)
        
        # Verarbeite die Materialliste
        material_list = data.get('material_list', [])
        mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id_for_query})
        
        if material_list:
            # Filtere nur wirklich leere Zeilen heraus (alle Felder leer)
            filtered_material_list = []
            for m in material_list:
                material = m.get('material', '').strip()
                menge = m.get('menge', 0)
                einzelpreis = m.get('einzelpreis', 0)
                
                # Nur hinzufügen wenn mindestens ein Feld ausgefüllt ist
                if material or menge > 0 or einzelpreis > 0:
                    filtered_material_list.append({
                        'ticket_id': ticket_id_for_query,
                        'material': material,
                        'menge': menge,
                        'einzelpreis': einzelpreis
                    })
            
            if filtered_material_list:
                mongodb.insert_many('auftrag_material', filtered_material_list)
        
        # Verarbeite die Arbeitsliste
        mongodb.delete_many('auftrag_arbeit', {'ticket_id': ticket_id_for_query})
        
        if filtered_arbeit_list:
            arbeit_daten = [{
                'ticket_id': ticket_id_for_query,
                'arbeit': arbeit.get('arbeit', ''),
                'arbeitsstunden': arbeit.get('arbeitsstunden', 0),
                'leistungskategorie': arbeit.get('leistungskategorie', '')
            } for arbeit in filtered_arbeit_list]
            mongodb.insert_many('auftrag_arbeit', arbeit_daten)
        
        # Setze das 'updated_at' Feld am Ticket selbst
        mongodb.update_one('tickets', {'_id': ticket_id_for_query}, {'$set': {'updated_at': datetime.now()}})

        # Rückgabe je nach Request-Typ
        if request.is_json:
            return jsonify({'success': True, 'message': 'Auftragsdetails erfolgreich gespeichert'})
        else:
            flash('Auftragsdetails erfolgreich gespeichert', 'success')
            return redirect(url_for('tickets.view', ticket_id=id))

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Auftragsdetails: {e}", exc_info=True)
        if request.is_json:
            return jsonify({'success': False, 'message': str(e)}), 500
        else:
            flash(f'Fehler beim Speichern: {str(e)}', 'error')
            return redirect(url_for('tickets.auftrag_details_page', id=id))

@bp.route('/<id>/export')
@login_required
@admin_required
def export_ticket(id):
    """Exportiert das Ticket als ausgefülltes Word-Dokument."""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        if not ticket:
            logging.error(f"Ticket nicht gefunden: {id}")
            flash('Ticket nicht gefunden.', 'error')
            return redirect(url_for('tickets.create'))
        
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)
        
        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query}) or {}
        material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query})) or []

        # --- Auftragnehmer (Vorname Nachname) ---
        auftragnehmer_user = None
        if ticket.get('assigned_to'):
            from app.models.mongodb_models import MongoDBUser
            auftragnehmer_user = MongoDBUser.get_by_username(ticket['assigned_to'])
        if auftragnehmer_user:
            # MongoDBUser.get_by_username() gibt ein Dictionary zurück, kein Objekt
            auftragnehmer_name = f"{auftragnehmer_user.get('firstname', '') or ''} {auftragnehmer_user.get('lastname', '') or ''}".strip()
        else:
            auftragnehmer_name = ''

        # --- Checkboxen für Auftraggeber intern/extern ---
        intern_checkbox = '☒' if auftrag_details.get('auftraggeber_intern') else '☐'
        extern_checkbox = '☒' if auftrag_details.get('auftraggeber_extern') else '☐'

        # --- Ausgeführte Arbeiten (bis zu 5) ---
        arbeiten_liste = auftrag_details.get('ausgefuehrte_arbeiten', '')
        arbeiten_zeilen = []
        if arbeiten_liste:
            for zeile in arbeiten_liste.split('\n'):
                if not zeile.strip():
                    continue
                teile = [t.strip() for t in zeile.split('|')]
                eintrag = {
                    'arbeiten': teile[0] if len(teile) > 0 else '',
                    'arbeitsstunden': teile[1] if len(teile) > 1 else '',
                    'leistungskategorie': teile[2] if len(teile) > 2 else ''
                }
                arbeiten_zeilen.append(eintrag)
        # Fülle auf 5 Zeilen auf
        while len(arbeiten_zeilen) < 5:
            arbeiten_zeilen.append({'arbeiten':'','arbeitsstunden':'','leistungskategorie':''})

        # Materialdaten aufbereiten
        material_rows = []
        summe_material = 0
        for m in material_list:
            menge = float(m.get('menge') or 0)
            einzelpreis = float(m.get('einzelpreis') or 0)
            gesamtpreis = menge * einzelpreis
            summe_material += gesamtpreis
            material_rows.append({
                'material': m.get('material', '') or '',
                'materialmenge': f"{menge:.2f}".replace('.', ',') if menge else '',
                'materialpreis': f"{einzelpreis:.2f}".replace('.', ',') if einzelpreis else '',
                'materialpreisges': f"{gesamtpreis:.2f}".replace('.', ',') if gesamtpreis else ''
            })
        while len(material_rows) < 5:
            material_rows.append({'material':'','materialmenge':'','materialpreis':'','materialpreisges':''})

        arbeitspausch = 0
        ubertrag = 0
        zwischensumme = summe_material + arbeitspausch + ubertrag
        mwst = zwischensumme * 0.07
        gesamtsumme = zwischensumme + mwst

        # --- Kontext für docxtpl bauen ---
        context = {
            'auftragnehmer': auftragnehmer_name,
            'auftragnummer': ticket.get('ticket_number', id),
            'datum': datetime.now().strftime('%d.%m.%Y'),
            'internchk': '☒' if auftrag_details.get('auftraggeber_intern') else '☐',
            'externchk': '☒' if auftrag_details.get('auftraggeber_extern') else '☐',
            'auftraggebername': auftrag_details.get('auftraggeber_name', ''),
            'auftraggebermail': auftrag_details.get('kontakt', ''),
            'bereich': auftrag_details.get('bereich', ''),
            'auftragsbeschreibung': auftrag_details.get('auftragsbeschreibung', ''),
            'duedate': auftrag_details.get('fertigstellungstermin', ''),
            'gesamtsumme': f"{gesamtsumme:.2f}".replace('.', ','),
            'matsum': f"{summe_material:.2f}".replace('.', ','),
            'ubertrag': f"{ubertrag:.2f}".replace('.', ','),
            'arpausch': f"{arbeitspausch:.2f}".replace('.', ','),
            'zwsum': f"{zwischensumme:.2f}".replace('.', ','),
            'mwst': f"{mwst:.2f}".replace('.', ','),
            'arbeitenblock': '\n'.join([arbeit['arbeiten'] for arbeit in arbeiten_zeilen]),
            'stundenblock': '\n'.join([arbeit['arbeitsstunden'] for arbeit in arbeiten_zeilen]),
            'kategorieblock': '\n'.join([arbeit['leistungskategorie'] for arbeit in arbeiten_zeilen]),
            'materialblock': '\n'.join([material['material'] for material in material_rows]),
            'mengenblock': '\n'.join([material['materialmenge'] for material in material_rows]),
            'preisblock': '\n'.join([material['materialpreis'] for material in material_rows]),
            'gesamtblock': '\n'.join([material['materialpreisges'] for material in material_rows])
        }

        # --- Word-Dokument generieren ---
        logging.info(f"Starte Export für Ticket {id}")
        
        # Lade das Template
        template_path = os.path.join(current_app.root_path, 'static', 'word', 'btzauftrag.docx')
        logging.info(f"Template-Pfad: {template_path}")
        
        if not os.path.exists(template_path):
            logging.error(f"Template-Datei nicht gefunden: {template_path}")
            flash('Word-Template nicht gefunden.', 'error')
            return redirect(url_for('tickets.create'))
        
        from docxtpl import DocxTemplate
        doc = DocxTemplate(template_path)
        logging.info("Template erfolgreich geladen")
        
        # Rendere das Dokument
        logging.info(f"Rendere Dokument mit Kontext: {context}")
        doc.render(context)
        logging.info("Dokument erfolgreich gerendert")
        
        # Erstelle das uploads-Verzeichnis falls es nicht existiert
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Speichere das generierte Dokument
        ticket_number = ticket.get('ticket_number', id)
        output_path = os.path.join(uploads_dir, f'ticket_{ticket_number}_export.docx')
        
        logging.info(f"Speichere Dokument unter: {output_path}")
        doc.save(output_path)
        logging.info("Dokument erfolgreich gespeichert")
        
        logging.info(f"Word-Dokument erfolgreich generiert: {output_path}")
        
        # Sende das Dokument
        return send_file(output_path, as_attachment=True, download_name=f'ticket_{ticket_number}_export.docx')
        
    except Exception as e:
        logging.error(f"Fehler beim Generieren des Word-Dokuments: {str(e)}", exc_info=True)
        flash(f'Fehler beim Generieren des Dokuments: {str(e)}', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/<id>/note', methods=['POST'])
@login_required
@admin_required
def add_note(id):
    """Fügt eine neue Notiz zu einem Ticket hinzu"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        note_text = data.get('note', '').strip()
        
        if not note_text:
            return jsonify({'success': False, 'message': 'Notiz darf nicht leer sein'}), 400

        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)

        # Erstelle die Notiz
        note_data = {
            'ticket_id': ticket_id_for_query,
            'note': note_text,
            'created_by': current_user.username,
            'created_at': datetime.now()
        }
        
        result = mongodb.insert_one('ticket_notes', note_data)
        
        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Speichern der Notiz'}), 500

        return jsonify({
            'success': True,
            'message': 'Notiz erfolgreich hinzugefügt',
            'note': {
                'id': str(result),
                'text': note_text,
                'created_by': current_user.username,
                'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
        })

    except Exception as e:
        logging.error(f"Fehler beim Hinzufügen der Notiz: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

def get_unassigned_ticket_count():
    count = mongodb.count_documents('tickets', {
        '$and': [
            {
                '$or': [
                    {'assigned_to': None},
                    {'assigned_to': ''},
                    {'assigned_to': {'$exists': False}}
                ]
            },
            {'status': 'offen'},
            {'deleted': {'$ne': True}}
        ]
    })
    return count

# Kontextprozessor für alle Templates
@bp.app_context_processor
def inject_unread_tickets_count():
    count = get_unassigned_ticket_count()
    return dict(unread_tickets_count=count)

@bp.route('/auftrag-neu', methods=['GET', 'POST'])
@login_required
def public_create_order():
    """Interne Auftragserstellung für eingeloggte Benutzer."""
    return _handle_auftrag_creation()

@bp.route('/auftrag-extern', methods=['GET', 'POST'])
def external_create_order():
    """Externe Auftragserstellung ohne Login für externe Einbindungen."""
    if request.method == 'POST':
        return _handle_auftrag_creation(external=True)
    categories = get_ticket_categories_from_settings()
    return render_template('tickets/auftrag_external_embed.html', 
                         categories=categories,
                         error=None)

def _handle_auftrag_creation(external=False):
    """Gemeinsame Logik für interne und externe Auftragserstellung."""
    if request.method == 'POST':
        try:
            # Hole die Formulardaten
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            priority = request.form.get('priority', 'normal')
            due_date = request.form.get('due_date')
            estimated_time = request.form.get('estimated_time')
            auftraggeber_name = request.form.get('name', '')  # Name des Auftraggebers (Feldname im Template: 'name')
            kontakt = request.form.get('kontakt', '')  # Kontaktdaten
            bereich = request.form.get('bereich', '')  # Bereich
            auftraggeber_typ = request.form.get('auftraggeber_typ', 'extern')  # Intern/Extern
            
            # Validiere die Pflichtfelder
            if not title:
                categories = get_ticket_categories_from_settings()
                if external or not current_user.is_authenticated:
                    return render_template('tickets/auftrag_external_embed.html', 
                                         categories=categories,
                                         error='Titel ist erforderlich.')
                else:
                    flash('Titel ist erforderlich.', 'error')
                    return redirect(url_for('tickets.public_create_order'))
                
            if not description:
                categories = get_ticket_categories_from_settings()
                if external or not current_user.is_authenticated:
                    return render_template('tickets/auftrag_external_embed.html', 
                                         categories=categories,
                                         error='Beschreibung ist erforderlich.')
                else:
                    flash('Beschreibung ist erforderlich.', 'error')
                    return redirect(url_for('tickets.public_create_order'))
                
            # Kategorie ist optional, daher entfernen wir die Validierung
            # if not category:
            #     flash('Kategorie ist erforderlich.', 'error')
            #     return redirect(url_for('tickets.public_create_order'))
            
            # Erstelle das Ticket
            ticket_data = {
                'title': title,
                'description': description,
                'priority': priority,
                'created_by': auftraggeber_name or 'Gast',  # Verwende den eingegebenen Namen oder "Gast" als Fallback
                'category': category,
                'due_date': due_date,
                'estimated_time': estimated_time,
                'status': 'offen',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'ticket_number': get_next_ticket_number(),  # Neue Auftragsnummer
                'is_external': not current_user.is_authenticated  # Markiere externe Aufträge
            }
            
            result = mongodb.insert_one('tickets', ticket_data)
            ticket_id = str(result)
            
            # Erstelle auch die Auftragsdetails mit dem Namen des Auftraggebers
            auftrag_details_data = {
                'ticket_id': ticket_id,  # Verwende die String-ID direkt
                'bereich': bereich or category,  # Verwende bereich oder category als Fallback
                'auftraggeber_intern': auftraggeber_typ == 'intern',
                'auftraggeber_extern': auftraggeber_typ == 'extern',
                'auftraggeber_name': auftraggeber_name,
                'kontakt': kontakt,
                'auftragsbeschreibung': description,
                'fertigstellungstermin': due_date,
                'gesamtsumme': 0
            }
            
            mongodb.insert_one('auftrag_details', auftrag_details_data)
            
            # Sende Bestätigungs-E-Mail
            if kontakt:  # Nur wenn Kontaktdaten vorhanden sind
                try:
                    from app.utils.email_utils import send_auftrag_confirmation_email
                    # Datum formatieren für E-Mail
                    ticket_data_for_email = ticket_data.copy()
                    if ticket_data_for_email.get('created_at'):
                        ticket_data_for_email['created_at'] = ticket_data_for_email['created_at'].strftime('%d.%m.%Y %H:%M Uhr')
                    
                    send_auftrag_confirmation_email(
                        ticket_data=ticket_data_for_email,
                        auftrag_details=auftrag_details_data,
                        recipient_email=kontakt
                    )
                except Exception as email_error:
                    logger.error(f"Fehler beim Senden der Bestätigungs-E-Mail: {str(email_error)}")
                    # E-Mail-Fehler soll den Auftrag nicht verhindern
            
            # Für alle Benutzer zur Bestätigungsseite
            return render_template('auftrag_public_success.html', 
                                 ticket_number=ticket_data['ticket_number'],
                                 ticket=ticket_data)
            
        except Exception as e:
            logging.error(f"Fehler bei der öffentlichen Auftragserstellung: {str(e)}", exc_info=True)
            categories = get_ticket_categories_from_settings()
            if external or not current_user.is_authenticated:
                return render_template('tickets/auftrag_external_embed.html', 
                                     categories=categories,
                                     error='Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.')
            else:
                flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
                return redirect(url_for('tickets.public_create_order'))
    
    # Hole die Kategorien für das Formular
    categories = get_ticket_categories_from_settings()
    
    if external or not current_user.is_authenticated:
        return render_template('tickets/auftrag_external_embed.html', 
                             categories=categories,
                             error=None)
    return render_template('tickets/create_auftrag.html', 
                         categories=categories,
                         priority_colors={
                             'niedrig': 'secondary',
                             'normal': 'primary',
                             'hoch': 'error',
                             'dringend': 'error'
                         })

@bp.route('/<id>/auftrag-details')
@login_required
def auftrag_details_page(id):
    # Robuste ID-Behandlung für verschiedene ID-Typen
    ticket = find_document_by_id('tickets', id)
    
    if not ticket:
        return render_template('404.html'), 404
    
    # Prüfe Berechtigungen: Admins/Mitarbeiter können alle Tickets sehen, normale User nur ihre eigenen oder zugewiesenen
    if current_user.role not in ['admin', 'mitarbeiter'] and ticket.get('created_by') != current_user.username and ticket.get('assigned_to') != current_user.username:
        flash('Sie haben keine Berechtigung, dieses Ticket zu sehen.', 'error')
        return redirect(url_for('tickets.index'))
    
    # Füge id-Feld hinzu (für Template-Kompatibilität)
    ticket['id'] = str(ticket['_id'])
    
    # Konvertiere alle Datumsfelder zu datetime-Objekten
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
    
    # Verwende die Ticket-ID für alle Abfragen
    ticket_id_for_query = convert_id_for_query(id)
        
    # Hole die Notizen für das Ticket
    notes = mongodb.find('ticket_notes', {'ticket_id': ticket_id_for_query})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id_for_query})

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query})
    
    # Hole Materialliste
    material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query}))
    
    # Hole Arbeitsliste
    arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': ticket_id_for_query}))
    
    # Verarbeite die ausgeführten Arbeiten aus den Auftragsdetails
    arbeit_list = []
    if auftrag_details and auftrag_details.get('ausgefuehrte_arbeiten'):
        arbeit_zeilen = auftrag_details['ausgefuehrte_arbeiten'].split('\n')
        for zeile in arbeit_zeilen:
            if zeile.strip():
                teile = zeile.split('|')
                arbeit_list.append({
                    'arbeit': teile[0] if len(teile) > 0 else '',
                    'arbeitsstunden': float(teile[1]) if len(teile) > 1 and teile[1] else 0,
                    'leistungskategorie': teile[2] if len(teile) > 2 else ''
                })
    
    logging.info(f"DEBUG: arbeit_list für Ticket {id}: {arbeit_list}")
    
    # Füge die Auftragsdetails zum Ticket hinzu, damit das Template darauf zugreifen kann
    if auftrag_details:
        ticket['auftrag_details'] = auftrag_details
        # Füge die Material- und Arbeitslisten hinzu
        ticket['auftrag_details']['material_list'] = material_list
        ticket['auftrag_details']['arbeit_list'] = arbeit_list
    else:
        # Falls keine Auftragsdetails vorhanden sind, verwende die Ticket-Daten als Fallback
        ticket['auftrag_details'] = {
            'bereich': ticket.get('category', ''),
            'auftraggeber_name': ticket.get('created_by', ''),
            'auftragsbeschreibung': ticket.get('description', ''),
            'material_list': material_list,
            'arbeit_list': arbeit_list
        }

    return render_template('tickets/auftrag_details_page.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         auftrag_details=auftrag_details,
                         material_list=material_list,
                         arbeit_list=arbeit_list)

@bp.route('/<id>/update-ticket', methods=['POST'])
@login_required
def update_ticket(id):
    """Aktualisiert die grundlegenden Ticket-Details wie estimated_time, category, due_date"""
    try:
        logging.info(f"DEBUG: update_ticket aufgerufen für ID: {id}")
        
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            logging.error(f"DEBUG: Ticket nicht gefunden für ID: {id}")
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
        
        logging.info(f"DEBUG: Ticket gefunden: {ticket.get('title', 'No Title')}")
        
        # Prüfe Berechtigungen: Normale User können nur ihre eigenen oder zugewiesenen Tickets bearbeiten
        if current_user.role not in ['admin', 'mitarbeiter'] and ticket.get('created_by') != current_user.username and ticket.get('assigned_to') != current_user.username:
            logging.error(f"DEBUG: Keine Berechtigung für User {current_user.username}")
            return jsonify({'success': False, 'message': 'Sie haben keine Berechtigung, dieses Ticket zu bearbeiten'}), 403
        
        logging.info(f"DEBUG: Berechtigung OK")
        
        # Hole die Daten aus dem Request
        if not request.is_json:
            logging.error(f"DEBUG: Request ist kein JSON")
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat. JSON erwartet.'}), 400
        
        data = request.get_json()
        logging.info(f"DEBUG: Request-Daten: {data}")
        
        # Bereite die Update-Daten vor
        update_data = {
            'updated_at': datetime.now()
        }
        logging.info(f"DEBUG: Basis-Update-Daten: {update_data}")
        
        # Verarbeite estimated_time (wird in Minuten gespeichert)
        if 'estimated_time' in data:
            estimated_time = data['estimated_time']
            if estimated_time is not None and estimated_time != '':
                update_data['estimated_time'] = float(estimated_time)
                logging.info(f"DEBUG: estimated_time gesetzt: {update_data['estimated_time']}")
            else:
                update_data['estimated_time'] = None
                logging.info(f"DEBUG: estimated_time auf None gesetzt")
        
        # Verarbeite category
        if 'category' in data:
            update_data['category'] = data['category']
            logging.info(f"DEBUG: category gesetzt: {update_data['category']}")
        
        # Verarbeite due_date
        if 'due_date' in data:
            due_date = data['due_date']
            if due_date:
                try:
                    # Versuche verschiedene Datumsformate zu parsen
                    if 'T' in due_date:
                        due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                    else:
                        due_date = datetime.strptime(due_date, '%Y-%m-%d')
                    update_data['due_date'] = due_date
                    logging.info(f"DEBUG: due_date gesetzt: {update_data['due_date']}")
                except ValueError as e:
                    logging.error(f"DEBUG: Fehler beim Parsen von due_date: {e}")
                    return jsonify({'success': False, 'message': 'Ungültiges Datumsformat'}), 400
            else:
                update_data['due_date'] = None
                logging.info(f"DEBUG: due_date auf None gesetzt")
        
        # Verarbeite priority
        if 'priority' in data:
            update_data['priority'] = data['priority']
            logging.info(f"DEBUG: priority gesetzt: {update_data['priority']}")
        
        logging.info(f"DEBUG: Finale Update-Daten: {update_data}")
        
        # Debug-Logs hinzufügen
        logging.info(f"DEBUG: Aktualisiere Ticket {id} mit ticket_id_for_update: {ticket_id_for_update}")
        logging.info(f"DEBUG: Update-Daten: {update_data}")
        logging.info(f"DEBUG: ticket_id_for_update Typ: {type(ticket_id_for_update).__name__}")
        logging.info(f"DEBUG: ticket_id_for_update Wert: {ticket_id_for_update}")
        
        try:
            # Verwende die bewährte mongodb-Wrapper-Klasse
            logging.info(f"DEBUG: Führe Update aus mit Filter: {{'_id': {ticket_id_for_update}}}")
            logging.info(f"DEBUG: Update-Daten: {update_data}")
            
            result = mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': update_data})
            logging.info(f"DEBUG: Update-Ergebnis: {result}")
            
            # Betrachte als erfolgreich, wenn die Operation erfolgreich war
            if result:
                logging.info(f"DEBUG: Update erfolgreich")
                return jsonify({'success': True, 'message': 'Ticket erfolgreich aktualisiert'})
            else:
                logging.error(f"DEBUG: Update fehlgeschlagen - Kein Dokument gefunden")
                return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
                
        except Exception as db_error:
            logging.error(f"DEBUG: Datenbankfehler beim Update: {db_error}")
            return jsonify({'success': False, 'message': f'Datenbankfehler: {str(db_error)}'}), 500
            
    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets {id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Interner Fehler: {str(e)}'}), 500 

@bp.route('/debug/unassigned-tickets')
@login_required
def debug_unassigned_tickets():
    """Debug-Route um nicht zugewiesene Tickets anzuzeigen"""
    try:
        # Hole alle nicht zugewiesenen Tickets
        unassigned_tickets = mongodb.find('tickets', {
            '$and': [
                {
                    '$or': [
                        {'assigned_to': None},
                        {'assigned_to': ''},
                        {'assigned_to': {'$exists': False}}
                    ]
                },
                {'status': 'offen'},
                {'deleted': {'$ne': True}}
            ]
        })
        
        # Konvertiere zu Liste für bessere Darstellung
        tickets_list = list(unassigned_tickets)
        
        # Debug-Informationen
        debug_info = {
            'total_unassigned': len(tickets_list),
            'tickets': []
        }
        
        for ticket in tickets_list:
            debug_info['tickets'].append({
                'id': str(ticket.get('_id')),
                'title': ticket.get('title', 'No Title'),
                'status': ticket.get('status', 'No Status'),
                'assigned_to': ticket.get('assigned_to', 'None'),
                'created_by': ticket.get('created_by', 'Unknown'),
                'created_at': ticket.get('created_at', 'Unknown'),
                'deleted': ticket.get('deleted', False)
            })
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500