from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, render_template_string
from app.models.ticket_db import TicketDatabase
from app.models.database import Database
from app.utils.decorators import login_required, admin_required
import logging
from datetime import datetime
from flask_login import current_user
from docxtpl import DocxTemplate
import os
from app.models.user import User

bp = Blueprint('tickets', __name__, url_prefix='/tickets')
ticket_db = TicketDatabase()

@bp.route('/')
@login_required
def index():
    """Zeigt die Ticket-Übersicht für den Benutzer."""
    # Hole die eigenen Tickets für die Anzeige (nur nicht geschlossene)
    my_tickets = ticket_db.query(
        """
        SELECT t.*, COUNT(tm.id) as message_count
        FROM tickets t
        LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
        WHERE t.created_by = ? AND t.status != 'geschlossen'
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """,
        [current_user.username]
    )
            
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
                # Kategorie-Logik
                category = data.get('category')
                new_category = data.get('new_category')
            else:
                title = request.form.get('title')
                description = request.form.get('description')
                priority = request.form.get('priority', 'normal')
                category = request.form.get('category')
                new_category = request.form.get('new_category')

            # Wenn eine neue Kategorie eingegeben wurde, prüfe und füge sie ggf. hinzu
            if new_category:
                with Database.get_db() as db:
                    exists = db.execute("SELECT 1 FROM categories WHERE name = ?", (new_category,)).fetchone()
                    if not exists:
                        db.execute("INSERT INTO categories (name) VALUES (?)", (new_category,))
                        db.commit()
                category = new_category

            due_date = data.get('due_date') if request.is_json else request.form.get('due_date')
            estimated_time = data.get('estimated_time') if request.is_json else request.form.get('estimated_time')

            # Formatiere das Fälligkeitsdatum
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                    due_date = due_date.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    due_date = None

            if not title:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Titel ist erforderlich'}), 400
                flash('Titel ist erforderlich.', 'error')
                return redirect(url_for('tickets.create'))

            # Erstelle das Ticket mit der korrekten Datenbankverbindung
            ticket_id = ticket_db.create_ticket(
                title=title,
                description=description,
                priority=priority,
                created_by=current_user.username,
                category=category,
                due_date=due_date,
                estimated_time=estimated_time
            )

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
    my_tickets = ticket_db.query(
        """
        SELECT t.*, COUNT(tm.id) as message_count
        FROM tickets t
        LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
        WHERE t.created_by = ? AND t.status != 'geschlossen'
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """,
        [current_user.username]
    )

    # Hole die zugewiesenen Tickets (nur nicht geschlossene)
    assigned_tickets = ticket_db.query(
        """
        SELECT t.*, COUNT(tm.id) as message_count
        FROM tickets t
        LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
        WHERE t.assigned_to = ? AND t.status != 'geschlossen'
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """,
        [current_user.username]
    )

    # Hole offene Tickets (nur nicht geschlossene)
    open_tickets = ticket_db.query(
        """
        SELECT t.*, COUNT(tm.id) as message_count
        FROM tickets t
        LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
        WHERE (t.assigned_to IS NULL OR t.assigned_to = '') AND t.status != 'geschlossen'
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """
    )
    
    # Hole alle Kategorien aus der Tabelle 'categories'
    categories = ticket_db.query(
        """
        SELECT name FROM categories ORDER BY name
        """
    )
    categories = [c['name'] for c in categories]
            
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

@bp.route('/view/<int:ticket_id>')
@login_required
def view(ticket_id):
    """Zeigt die Details eines Tickets für den Benutzer."""
    logging.info(f"Lade Ticket {ticket_id} für Benutzer {current_user.username}")
    
    ticket = ticket_db.get_ticket(ticket_id)
    
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
        # Verwende ticket_db für die Nachrichtenabfrage
        messages = ticket_db.get_ticket_messages(ticket_id)
        logging.info(f"Nachrichtenabfrage ergab {len(messages)} Nachrichten")
        
        # Formatiere Datum für jede Nachricht
        for msg in messages:
            if msg['created_at']:
                try:
                    created_at = datetime.strptime(msg['created_at'], '%Y-%m-%d %H:%M:%S')
                    msg['created_at'] = created_at.strftime('%d.%m.%Y, %H:%M')
                    logging.info(f"Nachricht {msg['id']} formatiert: {msg['created_at']}")
                except ValueError as e:
                    logging.error(f"Fehler beim Formatieren des Datums für Nachricht {msg['id']}: {str(e)}")
    except Exception as e:
        logging.error(f"Fehler beim Laden der Nachrichten: {str(e)}")
        messages = []
    
    message_count = len(messages)
    logging.info(f"Nachrichtenanzahl: {message_count}")
    
    # Hole die Notizen für das Ticket
    notes = ticket_db.get_ticket_notes(ticket_id)

    # Hole die Liste der verfügbaren Mitarbeiter
    try:
        workers = ticket_db.query(
            """
            SELECT username, username as name
            FROM users
            WHERE is_active = 1
            ORDER BY username
            """
        )
        logging.info(f"Gefundene Mitarbeiter: {workers}")
    except Exception as e:
        logging.error(f"Fehler beim Laden der Mitarbeiter: {str(e)}")
        workers = []

    return render_template('tickets/view.html',
                         ticket=ticket,
                         messages=messages,
                         notes=notes,
                         message_count=message_count,
                         workers=workers,
                         now=datetime.now())

@bp.route('/<int:ticket_id>/message', methods=['POST'])
@login_required
def add_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu"""
    try:
        # Prüfe ob das Ticket existiert
        ticket = ticket_db.get_ticket(ticket_id)
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

        # Verwende ticket_db.add_ticket_message statt direkter SQL-Abfragen
        is_admin = current_user.is_admin if hasattr(current_user, 'is_admin') else False
        ticket_db.add_ticket_message(
            ticket_id=ticket_id, 
            message=message, 
            sender=current_user.username, 
            is_admin=is_admin
        )
        
        logging.info(f"Nachricht erfolgreich gespeichert")

        # Hole die aktuelle Zeit für die Antwort
        created_at = datetime.now()
        formatted_date = created_at.strftime('%d.%m.%Y, %H:%M')

        return jsonify({
            'success': True,
            'message': {
                'text': message,
                'sender': current_user.username,
                'created_at': formatted_date,
                'is_admin': is_admin
            }
        })

    except Exception as e:
        logging.error(f"Fehler beim Hinzufügen der Nachricht: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Ein Fehler ist aufgetreten'}), 500

@bp.route('/<int:id>')
@admin_required
def detail(id):
    """Zeigt die Details eines Tickets für Administratoren."""
    ticket = ticket_db.query(
        """
        SELECT *
        FROM tickets
        WHERE id = ?
        """,
        [id],
        one=True
    )
    
    if not ticket:
        return render_template('404.html'), 404
        
    # Konvertiere alle Datumsfelder zu datetime-Objekten
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
        
    # Hole die Notizen für das Ticket
    notes = ticket_db.get_ticket_notes(id)

    # Hole die Nachrichten für das Ticket
    messages = ticket_db.get_ticket_messages(id)

    # Hole die Auftragsdetails
    auftrag_details = ticket_db.get_auftrag_details(id)
    logging.info(f"DEBUG: auftrag_details für Ticket {id}: {auftrag_details}")
    
    # Hole die Materialliste
    material_list = ticket_db.get_auftrag_material(id)

    # Hole alle Mitarbeiter aus der Hauptdatenbank
    with Database.get_db() as db:
        workers = db.execute(
            """
            SELECT username, username as name
            FROM users
            WHERE is_active = 1
            ORDER BY username
            """
        ).fetchall()

    return render_template('tickets/detail.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         workers=workers,
                         auftrag_details=auftrag_details,
                         material_list=material_list,
                         now=datetime.now())

@bp.route('/<int:id>/update', methods=['POST'])
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
        if not ticket_db.update_auftrag_details(id, **auftrag_details):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Auftragsdetails'})
        
        # Aktualisiere die Materialliste
        material_list = data.get('material_list', [])
        if not ticket_db.update_auftrag_material(id, material_list):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Materialliste'})
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets {id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/<int:id>/delete', methods=['POST'])
@admin_required
def delete(id):
    """Löscht ein Ticket."""
    try:
        # Prüfe ob Ticket existiert
        ticket = ticket_db.query(
            """
            SELECT * FROM tickets WHERE id = ?
            """,
            [id],
            one=True
        )
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404
            
        # Lösche das Ticket
        ticket_db.query(
            """
            DELETE FROM tickets WHERE id = ?
            """,
            [id]
        )
        
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

@bp.route('/<int:id>/auftrag-details-modal')
@login_required
def auftrag_details_modal(id):
    ticket = ticket_db.query(
        """
        SELECT *
        FROM tickets
        WHERE id = ?
        """,
        [id],
        one=True
    )
    
    if not ticket:
        return render_template('404.html'), 404
        
    # Konvertiere alle Datumsfelder zu datetime-Objekten
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
        
    # Hole die Notizen für das Ticket
    notes = ticket_db.get_ticket_notes(id)

    # Hole die Nachrichten für das Ticket
    messages = ticket_db.get_ticket_messages(id)

    # Hole die Auftragsdetails
    auftrag_details = ticket_db.get_auftrag_details(id)
    logging.info(f"DEBUG: auftrag_details für Ticket {id}: {auftrag_details}")
    
    # Hole die Materialliste
    material_list = ticket_db.get_auftrag_material(id)

    return render_template('tickets/auftrag_details_modal.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         auftrag_details=auftrag_details,
                         material_list=material_list)

@bp.route('/<int:id>/update-status', methods=['POST'])
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
        ticket_db.update_ticket(
            id=id,
            status=new_status,
            last_modified_by=current_user.username
        )

        return jsonify({'success': True, 'message': 'Status erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<int:id>/update-assignment', methods=['POST'])
@login_required
def update_assignment(id):
    """Aktualisiert die Zuweisung eines Tickets"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        assigned_to = data.get('assigned_to')
        
        # Hole das aktuelle Ticket
        ticket = ticket_db.get_ticket(id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Aktualisiere die Zuweisung
        ticket_db.update_ticket(
            id=id,
            status=ticket['status'],  # Behalte den aktuellen Status bei
            assigned_to=assigned_to,
            last_modified_by=current_user.username
        )

        return jsonify({'success': True, 'message': 'Zuweisung erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Zuweisung: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<int:id>/update-details', methods=['POST'])
@login_required
def update_details(id):
    """Aktualisiert die Details eines Tickets (Kategorie, Fälligkeitsdatum, geschätzte Zeit)"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        
        # Hole das aktuelle Ticket
        ticket = ticket_db.get_ticket(id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Formatiere das Fälligkeitsdatum
        due_date = data.get('due_date')
        if due_date:
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                due_date = due_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                due_date = None

        # Aktualisiere die Ticket-Details, behalte bestehende Werte bei wenn nicht im Request
        ticket_db.update_ticket(
            id=id,
            status=ticket['status'],  # Behalte den aktuellen Status bei
            assigned_to=ticket['assigned_to'],  # Behalte die aktuelle Zuweisung bei
            category=data.get('category', ticket['category']),  # Behalte bestehende Kategorie wenn nicht im Request
            due_date=due_date if due_date else ticket['due_date'],  # Behalte bestehendes Datum wenn nicht im Request
            estimated_time=data.get('estimated_time', ticket['estimated_time']),  # Behalte bestehende Zeit wenn nicht im Request
            last_modified_by=current_user.username
        )

        return jsonify({'success': True, 'message': 'Ticket-Details erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Ticket-Details: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<int:id>/export')
@login_required
def export_ticket(id):
    """Exportiert das Ticket als ausgefülltes Word-Dokument."""
    ticket = ticket_db.get_ticket(id)
    if not ticket:
        return abort(404)
    auftrag_details = ticket_db.get_auftrag_details(id) or {}
    material_list = ticket_db.get_auftrag_material(id) or []

    # --- Auftragnehmer (Vorname Nachname) ---
    auftragnehmer_user = None
    if ticket.get('assigned_to'):
        auftragnehmer_user = User.get_by_username(ticket['assigned_to'])
    if auftragnehmer_user:
        auftragnehmer_name = f"{auftragnehmer_user.firstname or ''} {auftragnehmer_user.lastname or ''}".strip()
    else:
        auftragnehmer_name = ''

    # --- Checkboxen für Auftraggeber intern/extern ---
    intern_checkbox = '✓' if auftrag_details.get('auftraggeber_intern') else '☐'
    extern_checkbox = '✓' if auftrag_details.get('auftraggeber_extern') else '☐'

    # --- Ausgeführte Arbeiten (bis zu 5) ---
    arbeiten_liste = auftrag_details.get('ausgefuehrte_arbeiten', '')
    # Annahme: Arbeiten werden als Zeilenumbruch-getrennte Einträge gespeichert, ggf. mit | getrennt für Stunden/Kategorie
    arbeiten_zeilen = []
    if arbeiten_liste:
        for zeile in arbeiten_liste.split('\n'):
            teile = [t.strip() for t in zeile.split('|')]
            # [Arbeit, Stunden, Kategorie]
            eintrag = {
                'arbeiten': teile[0] if len(teile) > 0 else '',
                'arbeitsstunden': teile[1] if len(teile) > 1 else '',
                'leistungskategorie': teile[2] if len(teile) > 2 else ''
            }
            arbeiten_zeilen.append(eintrag)
    # Fülle auf 5 Zeilen auf
    while len(arbeiten_zeilen) < 5:
        arbeiten_zeilen.append({'arbeiten':'','arbeitsstunden':'','leistungskategorie':''})

    # Materialdaten aufbereiten (wie gehabt)
    material_rows = []
    summe_material = 0
    for m in material_list:
        menge = m.get('menge') or 0
        einzelpreis = m.get('einzelpreis') or 0
        gesamtpreis = menge * einzelpreis
        summe_material += gesamtpreis
        material_rows.append({
            'material': m.get('material', '') or '',
            'materialmenge': menge or '',
            'materialpreis': einzelpreis or '',
            'materialpreisges': f"{gesamtpreis:.2f}" if gesamtpreis else ''
        })
    while len(material_rows) < 5:
        material_rows.append({'material':'','materialmenge':'','materialpreis':'','materialpreisges':''})

    arbeitspausch = 0
    ubertrag = 0
    zwischensumme = summe_material + arbeitspausch + ubertrag
    mwst = zwischensumme * 0.07
    gesamtsumme = zwischensumme + mwst

    def safe(val):
        return val if val is not None else ''

    context = {
        'auftragnehmer': auftragnehmer_name,
        'auftragnummer': safe(ticket.get('id', '')),
        'datum': safe(ticket.get('created_at', '')),
        'bereich': safe(auftrag_details.get('bereich', '')),
        'auftraggebername': safe(auftrag_details.get('auftraggeber_name', '')),
        'auftraggebermail': safe(auftrag_details.get('kontakt', '')),
        'auftragsbeschreibung': safe(auftrag_details.get('auftragsbeschreibung', ticket.get('description', ''))),
        'summematerial': f"{summe_material:.2f}" if summe_material else '',
        'ubertrag': f"{ubertrag:.2f}" if ubertrag else '',
        'arbeitspausch': f"{arbeitspausch:.2f}" if arbeitspausch else '',
        'zwischensumme': f"{zwischensumme:.2f}" if zwischensumme else '',
        'mwst': f"{mwst:.2f}" if mwst else '',
        'gesamtsumme': f"{gesamtsumme:.2f}" if gesamtsumme else '',
        'duedate': safe(auftrag_details.get('fertigstellungstermin', '')),
        'intern_checkbox': intern_checkbox,
        'extern_checkbox': extern_checkbox
    }
    # Arbeiten (arbeiten1, arbeitsstunden1, leistungskategorie1, ...)
    for i in range(1, 6):
        context[f'arbeiten{i}'] = arbeiten_zeilen[i-1]['arbeiten']
        context[f'arbeitsstunden{i}'] = arbeiten_zeilen[i-1]['arbeitsstunden']
        context[f'leistungskategorie{i}'] = arbeiten_zeilen[i-1]['leistungskategorie']
    # Material (material1, ...)
    for i in range(1, 6):
        context[f'material{i}'] = material_rows[i-1]['material']
        context[f'materialmenge{i}'] = material_rows[i-1]['materialmenge']
        context[f'materialpreis{i}'] = material_rows[i-1]['materialpreis']
        context[f'materialpreisges{i}'] = material_rows[i-1]['materialpreisges']
    # Für Kompatibilität: erste Zeile auch als 'material', ...
    context['material'] = material_rows[0]['material']
    context['materialmenge'] = material_rows[0]['materialmenge']
    context['materialpreis'] = material_rows[0]['materialpreis']
    context['materialpreisges'] = material_rows[0]['materialpreisges']

    template_path = os.path.join('app', 'static', 'word', 'btzauftrag.docx')
    doc = DocxTemplate(template_path)
    doc.render(context)
    output_path = f"/tmp/auftrag_{id}.docx"
    doc.save(output_path)
    return send_file(output_path, as_attachment=True, download_name=f"auftrag_{id}.docx")

@bp.route('/auftrag-neu', methods=['GET', 'POST'])
def public_create_order():
    # Kategorien aus der Tabelle 'categories' laden
    categories = ticket_db.query(
        """
        SELECT name FROM categories ORDER BY name
        """
    )
    categories = [c['name'] for c in categories]
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        name = request.form.get('name')
        kontakt = request.form.get('kontakt')
        bereich = request.form.get('bereich')
        kategorie = request.form.get('kategorie')
        auftraggeber_typ = request.form.get('auftraggeber_typ')
        if not title or not description or not name or not kontakt or not auftraggeber_typ:
            return render_template('auftrag_public.html', error='Bitte alle Pflichtfelder ausfüllen!', categories=categories)
        # Ticket anlegen (ohne Zuweisung, Status offen)
        ticket_id = ticket_db.create_ticket(
            title=title,
            description=description,
            priority='normal',
            created_by=name,
            category=kategorie,
            due_date=None,
            estimated_time=None
        )
        # Auftragsdetails speichern
        auftragsdetails = {
            'bereich': bereich,
            'auftraggeber_intern': auftraggeber_typ == 'intern',
            'auftraggeber_extern': auftraggeber_typ == 'extern',
            'auftraggeber_name': name,
            'kontakt': kontakt,
            'auftragsbeschreibung': description,
            'ausgefuehrte_arbeiten': '',
            'arbeitsstunden': '',
            'leistungskategorie': '',
            'fertigstellungstermin': '',
            'gesamtsumme': 0
        }
        ticket_db.add_auftrag_details(ticket_id, **auftragsdetails)
        return render_template('auftrag_public_success.html')
    return render_template('auftrag_public.html', categories=categories)

def get_unassigned_ticket_count():
    result = ticket_db.query("SELECT COUNT(*) as cnt FROM tickets WHERE assigned_to IS NULL OR assigned_to = ''")
    return result[0]['cnt'] if result and len(result) > 0 else 0

# Kontextprozessor für alle Templates
@bp.app_context_processor
def inject_unread_tickets_count():
    count = get_unassigned_ticket_count()
    return dict(unread_tickets_count=count)

@bp.route('/debug-auftrag-details/<int:ticket_id>')
@login_required
def debug_auftrag_details(ticket_id):
    """Temporäre Debug-Route zum Anzeigen der Auftragsdetails"""
    auftrag_details = ticket_db.get_auftrag_details(ticket_id)
    return jsonify({
        'auftrag_details': auftrag_details,
        'raw_data': ticket_db.query(
            "SELECT * FROM auftrag_details WHERE ticket_id = ?",
            [ticket_id],
            one=True
        )
    }) 