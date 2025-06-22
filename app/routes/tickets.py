from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, render_template_string
from app.models.mongodb_models import MongoDBTicket
from app.models.mongodb_database import mongodb
from app.utils.decorators import login_required, admin_required
from app.utils.database_helpers import get_ticket_categories_from_settings
import logging
from datetime import datetime
from flask_login import current_user
from docxtpl import DocxTemplate
import os
from bson import ObjectId

bp = Blueprint('tickets', __name__, url_prefix='/tickets')

@bp.route('/')
@login_required
def index():
    """Zeigt die Ticket-Übersicht für den Benutzer."""
    # Hole die eigenen Tickets für die Anzeige (nur nicht geschlossene)
    my_tickets = mongodb.find('tickets', {
        'created_by': current_user.username,
        'status': {'$ne': 'geschlossen'}
    })
    my_tickets = list(my_tickets)
    
    # Füge Nachrichtenanzahl hinzu
    for ticket in my_tickets:
        message_count = mongodb.count_documents('ticket_messages', {'ticket_id': ticket['_id']})
        ticket['message_count'] = message_count
    
    # Sortiere nach Erstellungsdatum (neueste zuerst)
    my_tickets.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
            
    # Füge id-Feld zu allen Tickets hinzu (für Template-Kompatibilität)
    for ticket in my_tickets:
        ticket['id'] = str(ticket['_id'])
    
    return render_template('tickets/index.html', tickets=my_tickets)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Erstellt ein neues Ticket."""
    if request.method == 'POST':
        try:
            # Prüfe ob die Anfrage JSON enthält
            if request.is_json:
                data = request.get_json()
                title = data.get('title')
                description = data.get('description')
                priority = data.get('priority', 'normal')
                category = data.get('category')
                new_category = data.get('new_category')
            else:
                title = request.form.get('title')
                description = request.form.get('description')
                priority = request.form.get('priority', 'normal')
                category = request.form.get('category')
                new_category = request.form.get('new_category')

            # Wenn eine neue Kategorie eingegeben wurde, prüfe und füge sie ggf. hinzu
            if category:
                # Prüfe ob die Kategorie bereits in den Settings existiert
                ticket_categories = get_ticket_categories_from_settings()
                if category not in ticket_categories:
                    # Füge die neue Kategorie zu den Settings hinzu
                    mongodb.update_one(
                        'settings',
                        {'key': 'ticket_categories'},
                        {'$push': {'value': category}},
                        upsert=True
                    )

            due_date = data.get('due_date') if request.is_json else request.form.get('due_date')
            estimated_time = data.get('estimated_time') if request.is_json else request.form.get('estimated_time')

            # Formatiere das Fälligkeitsdatum
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    due_date = None

            if not title:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Titel ist erforderlich'}), 400
                flash('Titel ist erforderlich.', 'error')
                return redirect(url_for('tickets.create'))

            # Erstelle das Ticket
            ticket_data = {
                'title': title,
                'description': description,
                'priority': priority,
                'created_by': current_user.username,
                'category': category,
                'due_date': due_date,
                'estimated_time': estimated_time,
                'status': 'offen',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            result = mongodb.insert_one('tickets', ticket_data)
            ticket_id = str(result)

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Ticket wurde erfolgreich erstellt',
                    'ticket_id': ticket_id
                })
            
            flash('Ticket wurde erfolgreich erstellt.', 'success')
            return redirect(url_for('tickets.create'))
        except Exception as e:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': f'Fehler beim Erstellen des Tickets: {str(e)}'
                }), 500
            flash(f'Fehler beim Erstellen des Tickets: {str(e)}', 'error')
            return redirect(url_for('tickets.create'))
    
    # Hole die eigenen Tickets für die Anzeige (nur nicht geschlossene)
    my_tickets = mongodb.find('tickets', {
        'created_by': current_user.username,
        'status': {'$ne': 'geschlossen'}
    })
    my_tickets = list(my_tickets)
    
    # Füge Nachrichtenanzahl hinzu
    for ticket in my_tickets:
        message_count = mongodb.count_documents('ticket_messages', {'ticket_id': ticket['_id']})
        ticket['message_count'] = message_count

    # Hole die zugewiesenen Tickets (nur nicht geschlossene)
    assigned_tickets = mongodb.find('tickets', {
        'assigned_to': current_user.username,
        'status': {'$ne': 'geschlossen'}
    })
    assigned_tickets = list(assigned_tickets)
    
    # Füge Nachrichtenanzahl hinzu
    for ticket in assigned_tickets:
        message_count = mongodb.count_documents('ticket_messages', {'ticket_id': ticket['_id']})
        ticket['message_count'] = message_count

    # Hole offene Tickets (nur nicht geschlossene)
    open_tickets = mongodb.find('tickets', {
        '$or': [
            {'assigned_to': None},
            {'assigned_to': ''}
        ],
        'status': 'offen'
    })
    open_tickets = list(open_tickets)
    
    # Füge Nachrichtenanzahl hinzu
    for ticket in open_tickets:
        message_count = mongodb.count_documents('ticket_messages', {'ticket_id': ticket['_id']})
        ticket['message_count'] = message_count
    
    # Hole alle Kategorien aus der settings Collection
    categories = get_ticket_categories_from_settings()
    
    # Sortiere alle Listen nach Erstellungsdatum (neueste zuerst)
    my_tickets.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    assigned_tickets.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    open_tickets.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    
    # Füge id-Feld zu allen Tickets hinzu (für Template-Kompatibilität)
    for ticket in my_tickets:
        ticket['id'] = str(ticket['_id'])
    for ticket in assigned_tickets:
        ticket['id'] = str(ticket['_id'])
    for ticket in open_tickets:
        ticket['id'] = str(ticket['_id'])
            
    return render_template('tickets/create.html', 
                         my_tickets=my_tickets,
                         assigned_tickets=assigned_tickets,
                         open_tickets=open_tickets,
                         categories=categories,
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
    
    # Konvertiere ticket_id zu ObjectId
    try:
        object_id = ObjectId(ticket_id)
    except:
        flash('Ungültige Ticket-ID.', 'error')
        return redirect(url_for('tickets.create'))
    
    ticket = mongodb.find_one('tickets', {'_id': object_id})
    
    if not ticket:
        logging.error(f"Ticket {ticket_id} nicht gefunden")
        flash('Ticket nicht gefunden.', 'error')
        return redirect(url_for('tickets.create'))
        
    # Prüfe ob der Benutzer berechtigt ist, das Ticket zu sehen
    if ticket['created_by'] != current_user.username and not current_user.is_admin:
        logging.error(f"Benutzer {current_user.username} hat keine Berechtigung für Ticket {ticket_id}")
        flash('Sie haben keine Berechtigung, dieses Ticket zu sehen.', 'error')
        return redirect(url_for('tickets.create'))
    
    # Hole die Nachrichten für das Ticket
    logging.info(f"Hole Nachrichten für Ticket {ticket_id}")
    
    try:
        messages = mongodb.find('ticket_messages', {'ticket_id': object_id})
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
        
        return render_template('tickets/view.html', 
                             ticket=ticket, 
                             messages=messages)
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Nachrichten: {str(e)}")
        flash('Fehler beim Laden der Nachrichten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/<ticket_id>/message', methods=['POST'])
@login_required
def add_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu"""
    try:
        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
        if not ticket:
            logging.error(f"Ticket {ticket_id} nicht gefunden")
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
        
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
            'ticket_id': ObjectId(ticket_id),
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
@admin_required
def detail(id):
    """Zeigt die Details eines Tickets für Administratoren."""
    ticket = mongodb.find_one('tickets', {'_id': ObjectId(id)})
    
    if not ticket:
        return render_template('404.html'), 404
    
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
    notes = mongodb.find('ticket_notes', {'ticket_id': ObjectId(id)})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': ObjectId(id)})

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ObjectId(id)})
    logging.info(f"DEBUG: auftrag_details für Ticket {id}: {auftrag_details}")
    
    # Hole die Materialliste
    material_list = mongodb.find('auftrag_material', {'ticket_id': ObjectId(id)})

    # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
    with mongodb.get_connection() as db:
        users = db.find('users', {'is_active': True})
        users = [dict(user) for user in users]

    # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
    assigned_users = mongodb.find('ticket_assignments', {'ticket_id': ObjectId(id)})

    # Hole alle Kategorien aus der ticket_categories Tabelle
    categories = mongodb.find('ticket_categories', {})
    categories = [c['name'] for c in categories]

    return render_template('tickets/detail.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         users=users,
                         assigned_users=assigned_users,
                         auftrag_details=auftrag_details,
                         material_list=material_list,
                         categories=categories,
                         now=datetime.now())

@bp.route('/<id>/update', methods=['POST'])
@login_required
def update(id):
    """Aktualisiert ein Ticket"""
    try:
        data = request.get_json()
        logging.info(f"Empfangene Daten für Ticket {id}: {data}")
        
        # Verarbeite ausgeführte Arbeiten
        arbeit_list = data.get('arbeit_list', [])
        ausgefuehrte_arbeiten = '\n'.join([
            f"{arbeit['arbeit']}|{arbeit['arbeitsstunden']}|{arbeit['leistungskategorie']}"
            for arbeit in arbeit_list
        ])
        logging.info(f"Verarbeitete ausgeführte Arbeiten: {ausgefuehrte_arbeiten}")
        
        # Bereite die Auftragsdetails vor
        auftrag_details = {
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': bool(data.get('auftraggeber_intern', False)),
            'auftraggeber_extern': bool(data.get('auftraggeber_extern', False)),
            'auftraggeber_name': data.get('auftraggeber_name', ''),
            'kontakt': data.get('kontakt', ''),
            'auftragsbeschreibung': data.get('auftragsbeschreibung', ''),
            'ausgefuehrte_arbeiten': ausgefuehrte_arbeiten,
            'arbeitsstunden': data.get('arbeitsstunden', ''),
            'leistungskategorie': data.get('leistungskategorie', ''),
            'fertigstellungstermin': data.get('fertigstellungstermin', ''),
            'gesamtsumme': data.get('gesamtsumme', 0)
        }
        
        # Aktualisiere die Auftragsdetails
        if not mongodb.update_one('auftrag_details', {'_id': ObjectId(id)}, {'$set': auftrag_details}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Auftragsdetails'})
        
        # Aktualisiere die Materialliste
        material_list = data.get('material_list', [])
        if not mongodb.update_many('auftrag_material', {'_id': {'$in': [ObjectId(m['_id']) for m in material_list]}}, {'$set': {'menge': m['menge'], 'einzelpreis': m['einzelpreis']} for m in material_list}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Materialliste'})
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets {id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/<id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Löscht ein Ticket."""
    try:
        # Prüfe ob Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(id)})
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404
            
        # Lösche das Ticket
        if not mongodb.delete_one('tickets', {'_id': ObjectId(id)}):
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
    ticket = mongodb.find_one('tickets', {'_id': ObjectId(id)})
    
    if not ticket:
        return render_template('404.html'), 404
    
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
    notes = mongodb.find('ticket_notes', {'ticket_id': ObjectId(id)})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': ObjectId(id)})

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ObjectId(id)})
    logging.info(f"DEBUG: auftrag_details für Ticket {id}: {auftrag_details}")
    
    # Hole die Materialliste
    material_list = mongodb.find('auftrag_material', {'ticket_id': ObjectId(id)})

    return render_template('tickets/auftrag_details_modal.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         auftrag_details=auftrag_details,
                         material_list=material_list)

@bp.route('/<id>/update-status', methods=['POST'])
@login_required
def update_status(id):
    """Aktualisiert den Status eines Tickets"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status ist erforderlich'}), 400

        # Aktualisiere den Status
        if not mongodb.update_one('tickets', {'_id': ObjectId(id)}, {'$set': {'status': new_status, 'updated_at': datetime.now()}}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren des Status'})

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
        if isinstance(assigned_to, str):
            # Falls nur ein Nutzer ausgewählt wurde, kommt ein String, sonst Liste
            assigned_to = [assigned_to] if assigned_to else []
        elif assigned_to is None:
            assigned_to = []

        # Aktualisiere die Zuweisungen in ticket_assignments
        if not mongodb.update_many('ticket_assignments', {'ticket_id': ObjectId(id)}, {'$set': {'assigned_to': {'$in': [ObjectId(t) for t in assigned_to]}}} if isinstance(assigned_to, list) else {'$set': {'assigned_to': assigned_to}}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Zuweisung'})

        return jsonify({'success': True, 'message': 'Zuweisung erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Zuweisung: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<id>/update-details', methods=['POST'])
@login_required
def update_details(id):
    """Aktualisiert die Details eines Tickets (Kategorie, Fälligkeitsdatum, geschätzte Zeit)"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        
        # Hole das aktuelle Ticket
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(id)})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Formatiere das Fälligkeitsdatum
        due_date = data.get('due_date')
        if due_date:
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                due_date = None

        # Aktualisiere die Ticket-Details, behalte bestehende Werte bei wenn nicht im Request
        if not mongodb.update_one('tickets', {'_id': ObjectId(id)}, {'$set': {
            'status': ticket['status'],  # Behalte den aktuellen Status bei
            'assigned_to': ticket['assigned_to'],  # Behalte die aktuelle Zuweisung bei
            'category': data.get('category', ticket['category']),  # Behalte bestehende Kategorie wenn nicht im Request
            'due_date': due_date if due_date else ticket['due_date'],  # Behalte bestehendes Datum wenn nicht im Request
            'estimated_time': data.get('estimated_time', ticket['estimated_time']),  # Behalte bestehende Zeit wenn nicht im Request
            'updated_at': datetime.now()
        }}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Ticket-Details'})

        return jsonify({'success': True, 'message': 'Ticket-Details erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Ticket-Details: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<id>/export')
@login_required
def export_ticket(id):
    """Exportiert das Ticket als ausgefülltes Word-Dokument."""
    ticket = mongodb.find_one('tickets', {'_id': ObjectId(id)})
    if not ticket:
        return abort(404)
    auftrag_details = mongodb.find_one('auftrag_details', {'_id': ObjectId(id)}) or {}
    material_list = mongodb.find('auftrag_material', {'_id': {'$in': [ObjectId(m['_id']) for m in material_list]}}) or []

    # --- Auftragnehmer (Vorname Nachname) ---
    auftragnehmer_user = None
    if ticket.get('assigned_to'):
        auftragnehmer_user = User.get_by_username(ticket['assigned_to'])
    if auftragnehmer_user:
        auftragnehmer_name = f"{auftragnehmer_user.firstname or ''} {auftragnehmer_user.lastname or ''}".strip()
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
        'intern_checkbox': intern_checkbox,
        'extern_checkbox': extern_checkbox,
        'auftraggeber_name': auftrag_details.get('auftraggeber_name', ''),
        'kontakt': auftrag_details.get('kontakt', ''),
        'auftragsbeschreibung': auftrag_details.get('auftragsbeschreibung', ''),
        'arbeiten_1': arbeiten_zeilen[0]['arbeiten'],
        'arbeitsstunden_1': arbeiten_zeilen[0]['arbeitsstunden'],
        'leistungskategorie_1': arbeiten_zeilen[0]['leistungskategorie'],
        'arbeiten_2': arbeiten_zeilen[1]['arbeiten'],
        'arbeitsstunden_2': arbeiten_zeilen[1]['arbeitsstunden'],
        'leistungskategorie_2': arbeiten_zeilen[1]['leistungskategorie'],
        'arbeiten_3': arbeiten_zeilen[2]['arbeiten'],
        'arbeitsstunden_3': arbeiten_zeilen[2]['arbeitsstunden'],
        'leistungskategorie_3': arbeiten_zeilen[2]['leistungskategorie'],
        'arbeiten_4': arbeiten_zeilen[3]['arbeiten'],
        'arbeitsstunden_4': arbeiten_zeilen[3]['arbeitsstunden'],
        'leistungskategorie_4': arbeiten_zeilen[3]['leistungskategorie'],
        'arbeiten_5': arbeiten_zeilen[4]['arbeiten'],
        'arbeitsstunden_5': arbeiten_zeilen[4]['arbeitsstunden'],
        'leistungskategorie_5': arbeiten_zeilen[4]['leistungskategorie'],
        'material_1': material_rows[0]['material'],
        'materialmenge_1': material_rows[0]['materialmenge'],
        'materialpreis_1': material_rows[0]['materialpreis'],
        'materialpreisges_1': material_rows[0]['materialpreisges'],
        'material_2': material_rows[1]['material'],
        'materialmenge_2': material_rows[1]['materialmenge'],
        'materialpreis_2': material_rows[1]['materialpreis'],
        'materialpreisges_2': material_rows[1]['materialpreisges'],
        'material_3': material_rows[2]['material'],
        'materialmenge_3': material_rows[2]['materialmenge'],
        'materialpreis_3': material_rows[2]['materialpreis'],
        'materialpreisges_3': material_rows[2]['materialpreisges'],
        'material_4': material_rows[3]['material'],
        'materialmenge_4': material_rows[3]['materialmenge'],
        'materialpreis_4': material_rows[3]['materialpreis'],
        'materialpreisges_4': material_rows[3]['materialpreisges'],
        'material_5': material_rows[4]['material'],
        'materialmenge_5': material_rows[4]['materialmenge'],
        'materialpreis_5': material_rows[4]['materialpreis'],
        'materialpreisges_5': material_rows[4]['materialpreisges'],
        'summe_material': f"{summe_material:.2f}".replace('.', ','),
        'arbeitspausch': f"{arbeitspausch:.2f}".replace('.', ','),
        'ubertrag': f"{ubertrag:.2f}".replace('.', ','),
        'zwischensumme': f"{zwischensumme:.2f}".replace('.', ','),
        'mwst': f"{mwst:.2f}".replace('.', ','),
        'gesamtsumme': f"{gesamtsumme:.2f}".replace('.', ',')
    }

    # --- Word-Dokument generieren ---
    try:
        # Lade das Template
        template_path = os.path.join(app.static_folder, 'word', 'btzauftrag.docx')
        doc = DocxTemplate(template_path)
        
        # Rendere das Dokument
        doc.render(context)
        
        # Speichere das generierte Dokument
        output_path = os.path.join(app.static_folder, 'uploads', f'ticket_{id}_export.docx')
        doc.save(output_path)
        
        # Sende das Dokument
        return send_file(output_path, as_attachment=True, download_name=f'ticket_{id}_export.docx')
        
    except Exception as e:
        logging.error(f"Fehler beim Generieren des Word-Dokuments: {str(e)}")
        flash('Fehler beim Generieren des Dokuments.', 'error')
        return redirect(url_for('tickets.detail', id=id))

@bp.route('/debug-auftrag-details/<ticket_id>')
@login_required
def debug_auftrag_details(ticket_id):
    """Debug-Route für Auftragsdetails"""
    ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
    if not ticket:
        return jsonify({'error': 'Ticket nicht gefunden'}), 404
    
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ObjectId(ticket_id)})
    material_list = list(mongodb.find('auftrag_material', {'ticket_id': ObjectId(ticket_id)}))
    
    return jsonify({
        'ticket': ticket,
        'auftrag_details': auftrag_details,
        'material_list': material_list
    })

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

        # Erstelle die Notiz
        note_data = {
            'ticket_id': ObjectId(id),
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
        '$or': [
            {'assigned_to': {'$exists': False}},
            {'assigned_to': None},
            {'assigned_to': ''}
        ]
    })
    return count

# Kontextprozessor für alle Templates
@bp.app_context_processor
def inject_unread_tickets_count():
    count = get_unassigned_ticket_count()
    return dict(unread_tickets_count=count)

@bp.route('/auftrag-neu', methods=['GET', 'POST'])
def public_create_order():
    """Öffentliche Auftragserstellung ohne Login."""
    if request.method == 'POST':
        try:
            # Hole die Formulardaten
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            priority = request.form.get('priority', 'normal')
            due_date = request.form.get('due_date')
            estimated_time = request.form.get('estimated_time')
            
            # Validiere die Pflichtfelder
            if not title:
                flash('Titel ist erforderlich.', 'error')
                return redirect(url_for('tickets.public_create_order'))
                
            if not description:
                flash('Beschreibung ist erforderlich.', 'error')
                return redirect(url_for('tickets.public_create_order'))
                
            if not category:
                flash('Kategorie ist erforderlich.', 'error')
                return redirect(url_for('tickets.public_create_order'))
            
            # Erstelle das Ticket
            ticket_data = {
                'title': title,
                'description': description,
                'priority': priority,
                'created_by': 'Gast',  # Öffentliche Tickets werden als "Gast" erstellt
                'category': category,
                'due_date': due_date,
                'estimated_time': estimated_time,
                'status': 'offen',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            result = mongodb.insert_one('tickets', ticket_data)
            ticket_id = str(result)
            
            flash('Ihr Auftrag wurde erfolgreich erstellt. Wir werden uns schnellstmöglich bei Ihnen melden.', 'success')
            return redirect(url_for('tickets.public_create_order'))
            
        except Exception as e:
            logging.error(f"Fehler bei der öffentlichen Auftragserstellung: {str(e)}", exc_info=True)
            flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
            return redirect(url_for('tickets.public_create_order'))
    
    # Hole die Kategorien für das Formular
    categories = mongodb.find('categories', {})
    categories = [c['name'] for c in categories]  # Extrahiere nur die Namen aus den Tupeln
    
    return render_template('auftrag_public.html', 
                         categories=categories,
                         priority_colors={
                             'niedrig': 'secondary',
                             'normal': 'primary',
                             'hoch': 'error',
                             'dringend': 'error'
                         }) 