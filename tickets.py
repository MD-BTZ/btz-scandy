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
from docx import Document
from werkzeug.utils import secure_filename

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
            if category:
                with ticket_db.get_connection() as db:
                    exists = db.execute("SELECT 1 FROM ticket_categories WHERE name = ?", (category,)).fetchone()
                    if not exists:
                        db.execute("INSERT INTO ticket_categories (name) VALUES (?)", (category,))
                        db.commit()

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
    with Database.get_db() as conn:
        categories = conn.execute('''
            SELECT name 
            FROM categories 
            WHERE deleted = 0 
            ORDER BY name
        ''').fetchall()
        categories = [c[0] for c in categories]  # Verwende den ersten Wert des Tupels
            
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

    def safe(val):
        return val if val is not None else ''

    # Formatiere das Datum
    def format_date(date_val):
        if not date_val:
            return ''
        if isinstance(date_val, datetime):
            return date_val.strftime('%d.%m.%Y')
        if isinstance(date_val, str):
            # Versuche verschiedene Formate
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(date_val, fmt).strftime('%d.%m.%Y')
                except ValueError:
                    continue
            return date_val  # Fallback: gib den String zurück
        return str(date_val)

    context = {
        'auftragnehmer': auftragnehmer_name,
        'auftragnummer': safe(ticket.get('id', '')),
        'datum': format_date(ticket.get('created_at', '')),
        'bereich': safe(auftrag_details.get('bereich', '')),
        'auftraggebername': safe(auftrag_details.get('auftraggeber_name', '')),
        'auftraggebermail': safe(auftrag_details.get('kontakt', '')),
        'auftragsbeschreibung': safe(auftrag_details.get('auftragsbeschreibung', ticket.get('description', ''))),
        'summematerial': f"{summe_material:.2f}".replace('.', ',') if summe_material else '',
        'ubertrag': f"{ubertrag:.2f}".replace('.', ',') if ubertrag else '',
        'arbeitspausch': f"{arbeitspausch:.2f}".replace('.', ',') if arbeitspausch else '',
        'zwischensumme': f"{zwischensumme:.2f}".replace('.', ',') if zwischensumme else '',
        'mwst': f"{mwst:.2f}".replace('.', ',') if mwst else '',
        'gesamtsumme': f"{gesamtsumme:.2f}".replace('.', ',') if gesamtsumme else '',
        'duedate': format_date(auftrag_details.get('fertigstellungstermin', '')),
        'internchk': intern_checkbox,
        'externchk': extern_checkbox
    }
    # Arbeiten (ausgefarbeiten1, arst1, lstkat1, ...)
    for i in range(1, 9):
        context[f'ausgefarbeiten{i}'] = arbeiten_zeilen[i-1]['arbeiten'] if i-1 < len(arbeiten_zeilen) else ''
        context[f'arst{i}'] = arbeiten_zeilen[i-1]['arbeitsstunden'] if i-1 < len(arbeiten_zeilen) else ''
        context[f'lstkat{i}'] = arbeiten_zeilen[i-1]['leistungskategorie'] if i-1 < len(arbeiten_zeilen) else ''

    # Material (material1, mmeng1, mpreis1, mgesp1, ...)
    for i in range(1, 9):
        context[f'material{i}'] = material_rows[i-1]['material'] if i-1 < len(material_rows) else ''
        context[f'mmeng{i}'] = material_rows[i-1]['materialmenge'] if i-1 < len(material_rows) else ''
        context[f'mpreis{i}'] = material_rows[i-1]['materialpreis'] if i-1 < len(material_rows) else ''
        context[f'mgesp{i}'] = material_rows[i-1]['materialpreisges'] if i-1 < len(material_rows) else ''

    # Summen
    context['matsum'] = f"{summe_material:.2f}".replace('.', ',') if summe_material else ''
    context['utrag'] = f"{ubertrag:.2f}".replace('.', ',') if ubertrag else ''
    context['arpausch'] = f"{arbeitspausch:.2f}".replace('.', ',') if arbeitspausch else ''
    context['zwsum'] = f"{zwischensumme:.2f}".replace('.', ',') if zwischensumme else ''
    context['mwst'] = f"{mwst:.2f}".replace('.', ',') if mwst else ''
    context['gesamtsumme'] = f"{gesamtsumme:.2f}".replace('.', ',') if gesamtsumme else ''

    # Arbeiten-Block
    context['arbeitenblock'] = '\n'.join([a['arbeiten'] for a in arbeiten_zeilen])
    context['stundenblock'] = '\n'.join([a['arbeitsstunden'] for a in arbeiten_zeilen])
    context['kategorieblock'] = '\n'.join([a['leistungskategorie'] for a in arbeiten_zeilen])

    # Material-Block
    context['materialblock'] = '\n'.join([m['material'] for m in material_rows])
    context['mengenblock'] = '\n'.join([m['materialmenge'] for m in material_rows])
    context['preisblock'] = '\n'.join([m['materialpreis'] for m in material_rows])
    context['gesamtblock'] = '\n'.join([m['materialpreisges'] for m in material_rows])

    template_path = os.path.join('app', 'static', 'word', 'btzauftrag.docx')
    doc = DocxTemplate(template_path)
    doc.render(context)
    
    # Verwende tempfile für plattformunabhängige temporäre Dateien
    import tempfile
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f'auftrag_{id}.docx')
    doc.save(output_path)
    return send_file(output_path, as_attachment=True, download_name=f"auftrag_{id}.docx")

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
            ticket_id = ticket_db.create_ticket(
                title=title,
                description=description,
                priority=priority,
                created_by='Gast',  # Öffentliche Tickets werden als "Gast" erstellt
                category=category,
                due_date=due_date,
                estimated_time=estimated_time
            )
            
            flash('Ihr Auftrag wurde erfolgreich erstellt. Wir werden uns schnellstmöglich bei Ihnen melden.', 'success')
            return redirect(url_for('tickets.public_create_order'))
            
        except Exception as e:
            logging.error(f"Fehler bei der öffentlichen Auftragserstellung: {str(e)}", exc_info=True)
            flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
            return redirect(url_for('tickets.public_create_order'))
    
    # Hole die Kategorien für das Formular
    categories = ticket_db.query("SELECT name FROM categories")
    categories = [c[0] for c in categories]  # Extrahiere nur die Namen aus den Tupeln
    
    return render_template('auftrag_public.html', 
                         categories=categories,
                         priority_colors={
                             'niedrig': 'secondary',
                             'normal': 'primary',
                             'hoch': 'error',
                             'dringend': 'error'
                         })

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

# Bewerbungsfeature Routen
@bp.route('/applications')
@login_required
def applications():
    templates = ticket_db.query("SELECT * FROM bewerbungsvorlagen WHERE erstellt_von = ? AND ist_aktiv = 1", 
                         (current_user.username,)).fetchall()
    applications = ticket_db.query('''
        SELECT a.*, t.name as vorlagen_name 
        FROM bewerbungen a 
        JOIN bewerbungsvorlagen t ON a.vorlagen_id = t.id 
        WHERE a.erstellt_von = ?
        ORDER BY a.erstellt_am DESC
    ''', (current_user.username,)).fetchall()
    return render_template('applications.html', templates=templates, applications=applications)

@bp.route('/applications/template/upload', methods=['POST'])
@login_required
def upload_template():
    if 'template' not in request.files:
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('applications'))
        
    file = request.files['template']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('applications'))
        
    if not allowed_file(file.filename):
        flash('Nur .docx Dateien sind erlaubt', 'error')
        return redirect(url_for('applications'))
        
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)
        
        ticket_db.query('''
            INSERT INTO bewerbungsvorlagen (name, dateiname, kategorie, erstellt_von)
            VALUES (?, ?, ?, ?)
        ''', (request.form.get('name'), filename, request.form.get('category'), current_user.username))
        
        flash('Vorlage erfolgreich hochgeladen', 'success')
    except Exception as e:
        flash(f'Fehler beim Hochladen: {str(e)}', 'error')
        
    return redirect(url_for('applications'))

@bp.route('/applications/create', methods=['POST'])
@login_required
def create_application():
    template_id = request.form.get('template_id')
    if not template_id:
        flash('Keine Vorlage ausgewählt', 'error')
        return redirect(url_for('applications'))
        
    template = ticket_db.query('SELECT * FROM bewerbungsvorlagen WHERE id = ?', (template_id,)).fetchone()
    if not template:
        flash('Vorlage nicht gefunden', 'error')
        return redirect(url_for('applications'))
        
    try:
        ticket_db.query('''
            INSERT INTO bewerbungen (
                vorlagen_id, bewerber, status, erstellt_am, aktualisiert_am
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (template_id, current_user.username, 'in_bearbeitung'))
        
        flash('Bewerbung erfolgreich erstellt', 'success')
    except Exception as e:
        flash(f'Fehler beim Erstellen: {str(e)}', 'error')
        
    return redirect(url_for('applications'))

@bp.route('/applications/<int:id>/update_status', methods=['POST'])
@login_required
def update_application_status(id):
    new_status = request.form.get('status')
    if not new_status:
        flash('Kein Status angegeben', 'error')
        return redirect(url_for('applications'))
        
    try:
        ticket_db.query('''
            UPDATE bewerbungen
            SET status = ?, aktualisiert_am = CURRENT_TIMESTAMP
            WHERE id = ? AND bewerber = ?
        ''', (new_status, id, current_user.username))
        
        flash('Status erfolgreich aktualisiert', 'success')
    except Exception as e:
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'error')
        
    return redirect(url_for('applications'))

@bp.route('/applications/<int:id>/add_response', methods=['POST'])
@login_required
def add_application_response(id):
    response_type = request.form.get('response_type')
    response_date = request.form.get('response_date')
    content = request.form.get('content')
    next_steps = request.form.get('next_steps')
    
    if not all([response_type, response_date]):
        flash('Bitte füllen Sie alle erforderlichen Felder aus', 'error')
        return redirect(url_for('applications'))
        
    try:
        ticket_db.query('''
            INSERT INTO bewerbungsantworten (
                bewerbung_id, antworttyp, antwortdatum, inhalt, naechste_schritte
            ) VALUES (?, ?, ?, ?, ?)
        ''', (id, response_type, response_date, content, next_steps))
        
        flash('Antwort erfolgreich hinzugefügt', 'success')
    except Exception as e:
        flash(f'Fehler beim Hinzufügen: {str(e)}', 'error')
        
    return redirect(url_for('applications')) 