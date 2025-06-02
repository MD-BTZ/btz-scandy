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
import tempfile
from werkzeug.utils import secure_filename
import pdfkit
import PyPDF2
import shutil

logger = logging.getLogger(__name__)

bp = Blueprint('tickets', __name__, url_prefix='/tickets')
ticket_db = TicketDatabase()

UPLOAD_FOLDER = os.path.join('app', 'uploads', 'users')
ALLOWED_EXTENSIONS = {'docx', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_upload_path(username):
    """Gibt den Upload-Pfad für einen bestimmten Benutzer zurück"""
    return os.path.join(UPLOAD_FOLDER, username)

def ensure_user_directories(username):
    """Erstellt die notwendigen Verzeichnisse für einen Benutzer"""
    user_path = get_user_upload_path(username)
    directories = [
        os.path.join(user_path, 'templates'),
        os.path.join(user_path, 'documents', 'cv'),
        os.path.join(user_path, 'documents', 'certificates')
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    return user_path

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
        WHERE (t.assigned_to IS NULL OR t.assigned_to = '') 
        AND t.status = 'offen'
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """
    )
    
    # Hole alle Kategorien aus der ticket_categories Tabelle
    categories = ticket_db.query('SELECT name FROM ticket_categories ORDER BY name')
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

    # Hole die Kategorien für das Formular
    categories = ticket_db.query('SELECT name FROM ticket_categories ORDER BY name')
    categories = [c['name'] for c in categories]

    return render_template('tickets/view.html',
                         ticket=ticket,
                         messages=messages,
                         notes=notes,
                         message_count=message_count,
                         workers=workers,
                         now=datetime.now(),
                         categories=categories)

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

    # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
    with Database.get_db() as db:
        users = db.execute(
            """
            SELECT username FROM users WHERE is_active = 1 ORDER BY username
            """
        ).fetchall()
        users = [dict(row) for row in users]

    # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
    assigned_users = ticket_db.get_ticket_assignments(id)

    # Hole alle Kategorien aus der ticket_categories Tabelle
    categories = ticket_db.query('SELECT name FROM ticket_categories ORDER BY name')
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
        if isinstance(assigned_to, str):
            # Falls nur ein Nutzer ausgewählt wurde, kommt ein String, sonst Liste
            assigned_to = [assigned_to] if assigned_to else []
        elif assigned_to is None:
            assigned_to = []

        # Aktualisiere die Zuweisungen in ticket_assignments
        ticket_db.set_ticket_assignments(id, assigned_to)

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

@bp.route('/<int:id>/note', methods=['POST'])
@login_required
@admin_required
def add_note(id):
    """Fügt eine neue Notiz zu einem Ticket hinzu"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        note = data.get('note')
        
        if not note or not note.strip():
            return jsonify({'success': False, 'message': 'Notiz ist erforderlich'}), 400

        # Füge die Notiz hinzu
        ticket_db.add_note(
            ticket_id=id,
            note=note.strip(),
            author_name=current_user.username,
            is_private=False  # Alle Notizen sind öffentlich
        )

        return jsonify({'success': True, 'message': 'Notiz wurde gespeichert'})

    except Exception as e:
        logging.error(f"Fehler beim Hinzufügen der Notiz: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/applications')
@login_required
def applications():
    # Korrigiere die Dateipfade in der Datenbank
    try:
        # Templates korrigieren
        templates = ticket_db.query('SELECT id, file_path FROM application_templates')
        for template in templates:
            if template['file_path'].startswith('app/app/'):
                new_path = template['file_path'].replace('app/app/', 'app/')
                ticket_db.query("""
                    UPDATE application_templates 
                    SET file_path = ? 
                    WHERE id = ?
                """, [new_path, template['id']])
        
        # Dokumente korrigieren
        documents = ticket_db.query('SELECT id, file_path FROM application_documents')
        for document in documents:
            if document['file_path'].startswith('app/app/'):
                new_path = document['file_path'].replace('app/app/', 'app/')
                ticket_db.query("""
                    UPDATE application_documents 
                    SET file_path = ? 
                    WHERE id = ?
                """, [new_path, document['id']])
    except Exception as e:
        logging.error(f"Fehler beim Korrigieren der Dateipfade: {str(e)}")

    # Verfügbare Platzhalter
    placeholders = {
        '{{company_name}}': 'Name des Unternehmens',
        '{{position}}': 'Bezeichnung der Position',
        '{{contact_person}}': 'Name der Kontaktperson',
        '{{contact_email}}': 'E-Mail der Kontaktperson',
        '{{contact_phone}}': 'Telefonnummer der Kontaktperson',
        '{{address}}': 'Adresse des Unternehmens'
    }

    # Templates abrufen
    templates = ticket_db.query(
            'SELECT * FROM application_templates WHERE is_active = 1'
    )

    # Gespeicherte Dokumente abrufen
    documents = ticket_db.query(
        'SELECT * FROM application_documents WHERE created_by = ?',
        [current_user.username]
    )

    # Bewerbungen abrufen
    applications = ticket_db.query(
        '''
        SELECT a.*, t.name as template_name 
        FROM applications a 
        JOIN application_templates t ON a.template_id = t.id 
        WHERE a.created_by = ? 
        ORDER BY a.created_at DESC
        ''',
        [current_user.username]
    )

    return render_template('tickets/applications.html',
                         placeholders=placeholders,
                         templates=templates,
                         documents=documents,
                         applications=applications)

@bp.route('/applications/template/upload', methods=['POST'])
@login_required
def upload_template():
    """Lädt ein neues Bewerbungstemplate hoch"""
    if 'template' not in request.files:
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('tickets.applications'))
        
    file = request.files['template']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('tickets.applications'))
        
    if not allowed_file(file.filename):
        flash('Nur .docx Dateien sind erlaubt', 'error')
        return redirect(url_for('tickets.applications'))
    
    try:
        # Erstelle Benutzerverzeichnisse
        user_path = ensure_user_directories(current_user.username)
        
        # Speichere die Datei
        filename = secure_filename(file.filename)
        filepath = os.path.join(user_path, 'templates', filename)
        file.save(filepath)
        
        # Speichere Template in der Datenbank
        ticket_db.query("""
            INSERT INTO application_templates (name, file_path, file_name, category, created_by, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, [filename, filepath, filename, request.form.get('category', ''), current_user.username])
        
        flash('Template erfolgreich hochgeladen', 'success')
        
    except Exception as e:
        logging.error(f"Fehler beim Hochladen des Templates: {str(e)}")
        flash('Fehler beim Hochladen des Templates', 'error')
        
    return redirect(url_for('tickets.applications'))

@bp.route('/applications/create', methods=['POST'])
@login_required
def create_application():
    try:
        # Erstelle Verzeichnisse für den Benutzer
        user_path = get_user_upload_path(current_user.username)
        ensure_user_directories(current_user.username)
        
        # Initialisiere Listen für Dokumente
        cv_path = None
        certificate_paths = []
        
        # Verarbeite Lebenslauf
        if 'cv' in request.files:
            cv_file = request.files['cv']
            if cv_file and allowed_file(cv_file.filename):
                filename = secure_filename(cv_file.filename)
                cv_path = os.path.join(user_path, 'cv', filename)
                os.makedirs(os.path.dirname(cv_path), exist_ok=True)
                cv_file.save(cv_path)
                
                # Speichere das Dokument in der Datenbank
                ticket_db.query("""
                    INSERT INTO application_documents (
                        file_name, file_path, document_type, created_by
                    ) VALUES (?, ?, 'cv', ?)
                """, [filename, cv_path, current_user.username])
        
        # Verarbeite Zeugnisse
        if 'certificates' in request.files:
            cert_files = request.files.getlist('certificates')
            for cert_file in cert_files:
                if cert_file and allowed_file(cert_file.filename):
                    filename = secure_filename(cert_file.filename)
                    cert_path = os.path.join(user_path, 'certificates', filename)
                    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
                    cert_file.save(cert_path)
                    certificate_paths.append(cert_path)
                    
                    # Speichere das Dokument in der Datenbank
                    ticket_db.query("""
                        INSERT INTO application_documents (
                            file_name, file_path, document_type, created_by
                        ) VALUES (?, ?, 'certificate', ?)
                    """, [filename, cert_path, current_user.username])
        
        # Verwende gespeicherte Zeugnisse
        saved_cert_ids = request.form.getlist('saved_certificate_ids[]')
        for cert_id in saved_cert_ids:
            saved_cert = ticket_db.query("""
                SELECT * FROM application_documents 
                WHERE id = ? AND document_type = 'certificate'
            """, [cert_id], one=True)
            if saved_cert:
                certificate_paths.append(saved_cert['file_path'])
        
        # Bewerbung erstellen
        template_id = request.form['template_id']
        template = ticket_db.query("""
            SELECT * FROM application_templates 
            WHERE id = ? AND is_active = 1
        """, [template_id], one=True)
        
        if not template:
            flash('Template nicht gefunden', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Lade das Template
        template_path = template['file_path']
        if not os.path.exists(template_path):
            flash('Template-Datei nicht gefunden', 'error')
            return redirect(url_for('tickets.applications'))
            
        doc = DocxTemplate(template_path)
            
        # Ersetze Platzhalter
        context = {
            'company_name': request.form['company_name'],
            'position': request.form['position'],
            'contact_person': request.form.get('contact_person', ''),
            'contact_email': request.form.get('contact_email', ''),
            'contact_phone': request.form.get('contact_phone', ''),
            'address': request.form.get('address', '')
        }
        
        # Rendere das Template
        doc.render(context)
        
        # Speichere die gerenderte Bewerbung
        output_path = os.path.join(user_path, 'applications', f'bewerbung_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        
        # Speichere in der Datenbank
        ticket_db.query("""
            INSERT INTO applications (
                template_id, company_name, position, contact_person,
                contact_email, contact_phone, address,
                generated_content, status, created_by,
                cv_path, certificate_paths, output_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'created', ?, ?, ?, ?)
        """, [
            template_id, 
            request.form['company_name'], 
            request.form['position'],
            request.form.get('contact_person'), 
            request.form.get('contact_email'),
            request.form.get('contact_phone'), 
            request.form.get('address'),
            str(context),  # Speichere den Kontext als String
            current_user.username, 
            cv_path, 
            ','.join(certificate_paths) if certificate_paths else None,
            output_path
        ])
        
        flash('Bewerbung erfolgreich erstellt', 'success')
        
    except Exception as e:
        logging.error(f"Fehler beim Erstellen der Bewerbung: {str(e)}")
        flash(f'Fehler beim Erstellen der Bewerbung: {str(e)}', 'error')
        
    return redirect(url_for('tickets.applications'))

@bp.route('/applications/<int:id>/update_status', methods=['POST'])
@login_required
def update_application_status(id):
    """Aktualisiert den Status einer Bewerbung"""
    try:
        status = request.form.get('status')
        notes = request.form.get('notes', '')
        
        ticket_db.query("""
            UPDATE applications 
            SET status = ?, notes = ?
            WHERE id = ? AND created_by = ?
        """, [status, notes, id, current_user.username])
        
        flash('Status erfolgreich aktualisiert', 'success')
        
    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Status: {str(e)}")
        flash('Fehler beim Aktualisieren des Status', 'error')
        
    return redirect(url_for('tickets.applications'))

@bp.route('/applications/<int:id>/add_response', methods=['POST'])
@login_required
def add_application_response(id):
    """Fügt eine Antwort zu einer Bewerbung hinzu"""
    try:
        response_type = request.form.get('response_type')
        response_date = request.form.get('response_date')
        content = request.form.get('content')
        next_steps = request.form.get('next_steps', '')
        
        ticket_db.query("""
            INSERT INTO application_responses (
                application_id, response_type, response_date,
                content, next_steps
            ) VALUES (?, ?, ?, ?, ?)
        """, [id, response_type, response_date, content, next_steps])
        
        flash('Antwort erfolgreich hinzugefügt', 'success')
        
    except Exception as e:
        logging.error(f"Fehler beim Hinzufügen der Antwort: {str(e)}")
        flash('Fehler beim Hinzufügen der Antwort', 'error')
        
    return redirect(url_for('tickets.applications'))

@bp.route('/applications/<int:id>/details')
def application_details(id):
    db = Database.get_db()
    application = db.execute('''
        SELECT a.*, t.name as template_name 
        FROM applications a 
        JOIN application_templates t ON a.template_id = t.id 
        WHERE a.id = ? AND a.created_by = ?
    ''', (id, current_user.username)).fetchone()
    
    if application is None:
        return jsonify({'error': 'Bewerbung nicht gefunden'}), 404
    
    return jsonify({
        'content': application['generated_content'],
        'custom_block': application['custom_block']
    })

@bp.route('/applications/<int:id>/download')
def download_application(id):
    db = Database.get_db()
    application = db.execute('''
        SELECT a.*, t.name as template_name 
        FROM applications a 
        JOIN application_templates t ON a.template_id = t.id 
        WHERE a.id = ? AND a.created_by = ?
    ''', (id, current_user.username)).fetchone()
    
    if application is None:
        return jsonify({'error': 'Bewerbung nicht gefunden'}), 404
    
    # Temporäres HTML erstellen
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; }}
                .content {{ margin: 20px 0; }}
                .custom-block {{ margin: 20px 0; padding: 10px; background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <h1>Bewerbung: {application['position']} bei {application['company_name']}</h1>
            <div class="content">
                {application['generated_content']}
            </div>
            <div class="custom-block">
                {application['custom_block']}
            </div>
        </body>
        </html>
        """
        temp_html.write(html_content.encode('utf-8'))
        temp_html_path = temp_html.name
    
    # PDF generieren
    pdf_path = temp_html_path.replace('.html', '.pdf')
    pdfkit.from_file(temp_html_path, pdf_path)
    
    # Temporäre HTML-Datei löschen
    os.unlink(temp_html_path)
    
    # PDF mit Dokumenten zusammenführen
    final_pdf_path = pdf_path.replace('.pdf', '_final.pdf')
    merger = PyPDF2.PdfMerger()
    
    # Haupt-PDF hinzufügen
    merger.append(pdf_path)
    
    # Dokumente hinzufügen
    documents = db.execute('''
        SELECT * FROM application_documents 
        WHERE application_id = ?
        ORDER BY document_type
    ''', (id,)).fetchall()
    
    for doc in documents:
        if os.path.exists(doc['file_path']):
            merger.append(doc['file_path'])
    
    merger.write(final_pdf_path)
    merger.close()
    
    # Temporäre PDF löschen
    os.unlink(pdf_path)
    
    return send_file(
        final_pdf_path,
        as_attachment=True,
        download_name=f'bewerbung_{application["company_name"]}.pdf'
    ) 

@bp.route('/templates/<int:id>/download')
@login_required
def download_template(id):
    """Template herunterladen"""
    try:
        # Template aus der Datenbank holen
        template = ticket_db.query("""
            SELECT * FROM application_templates 
            WHERE id = ? AND is_active = 1
        """, [id], one=True)
        
        if not template:
            flash('Template nicht gefunden', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Korrigiere den Dateipfad (entferne doppeltes app/)
        file_path = template['file_path'].replace('app/app/', 'app/')
            
        # Prüfen ob die Datei existiert
        if not os.path.exists(file_path):
            flash('Template-Datei nicht gefunden', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Datei zum Download senden
        return send_file(
            file_path,
            as_attachment=True,
            download_name=template['file_name']
        )
        
    except Exception as e:
        flash(f'Fehler beim Herunterladen des Templates: {str(e)}', 'error')
        return redirect(url_for('tickets.applications'))

@bp.route('/templates/<int:id>/delete', methods=['POST'])
@login_required
def delete_template(id):
    try:
        # Hole das Template aus der Datenbank
        template = ticket_db.query("""
            SELECT * FROM application_templates 
            WHERE id = ? AND is_active = 1
        """, [id], one=True)
        
        if not template:
            return jsonify({'success': False, 'message': 'Template nicht gefunden'}), 404
            
        # Korrigiere den Dateipfad (entferne doppeltes app/)
        file_path = template['file_path'].replace('app/app/', 'app/')
            
        # Template in der Datenbank als inaktiv markieren
        ticket_db.query("""
            UPDATE application_templates 
            SET is_active = 0 
            WHERE id = ?
        """, [id])
        
        # Datei physisch löschen
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"Fehler beim Löschen der Template-Datei: {str(e)}")
                return jsonify({'success': False, 'message': 'Fehler beim Löschen der Datei'})
            
        return jsonify({'success': True, 'message': 'Template erfolgreich gelöscht'})
        
    except Exception as e:
        logging.error(f"Fehler beim Löschen des Templates: {str(e)}")
        return jsonify({'success': False, 'message': f'Fehler beim Löschen des Templates: {str(e)}'})

@bp.route('/applications/document/upload', methods=['POST'])
@login_required
def upload_document():
    try:
        if 'document' not in request.files:
            return redirect(url_for('tickets.applications'))
        
        file = request.files['document']
        document_type = request.form.get('document_type')
        
        if file.filename == '':
            return redirect(url_for('tickets.applications'))
            
        if file and document_type:
            # Erstelle die Verzeichnisstruktur
            user_dir = os.path.join('app', 'uploads', 'users', current_user.username, 'documents', document_type)
            os.makedirs(user_dir, exist_ok=True)
            
            # Speichere die Datei
            filename = secure_filename(file.filename)
            file_path = os.path.join(user_dir, filename)
            file.save(file_path)
            
            # Speichere in der Datenbank
            ticket_db.query("""
                INSERT INTO application_documents 
                (file_name, file_path, document_type, created_by) 
                VALUES (?, ?, ?, ?)
            """, [filename, file_path, document_type, current_user.username])
            
            flash('Dokument erfolgreich hochgeladen', 'success')
        else:
            flash('Fehler beim Hochladen des Dokuments', 'error')
            
    except Exception as e:
        logging.error(f'Fehler beim Hochladen des Dokuments: {str(e)}')
        flash(f'Fehler beim Hochladen des Dokuments: {str(e)}', 'error')
        
    return redirect(url_for('tickets.applications'))

@bp.route('/documents/<int:id>/download')
@login_required
def download_document(id):
    """Lädt ein Dokument herunter"""
    try:
        # Dokument aus der Datenbank holen
        document = ticket_db.query("""
            SELECT * FROM application_documents 
            WHERE id = ? AND created_by = ?
        """, [id, current_user.username], one=True)
        
        if not document:
            flash('Dokument nicht gefunden', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Korrigiere den Dateipfad (entferne doppeltes app/)
        file_path = document['file_path'].replace('app/app/', 'app/')
            
        # Prüfen ob die Datei existiert
        if not os.path.exists(file_path):
            flash('Dokument-Datei nicht gefunden', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Datei zum Download senden
        return send_file(
            file_path,
            as_attachment=True,
            download_name=document['file_name']
        )
        
    except Exception as e:
        flash(f'Fehler beim Herunterladen des Dokuments: {str(e)}', 'error')
        return redirect(url_for('tickets.applications'))

@bp.route('/documents/<int:id>/delete', methods=['POST'])
@login_required
def delete_document(id):
    """Löscht ein Dokument"""
    try:
        # Dokument aus der Datenbank holen
        document = ticket_db.query("""
            SELECT * FROM application_documents 
            WHERE id = ? AND created_by = ?
        """, [id, current_user.username], one=True)
        
        if not document:
            return jsonify({'success': False, 'message': 'Dokument nicht gefunden'})
            
        # Korrigiere den Dateipfad (entferne doppeltes app/)
        file_path = document['file_path'].replace('app/app/', 'app/')
            
        # Dokument aus der Datenbank löschen
        ticket_db.query("""
            DELETE FROM application_documents 
            WHERE id = ?
        """, [id])
        
        # Optional: Datei physisch löschen
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return jsonify({'success': True, 'message': 'Dokument erfolgreich gelöscht'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Fehler beim Löschen des Dokuments: {str(e)}'})

def delete_user_files(username):
    """Löscht alle Dateien und Verzeichnisse eines Benutzers"""
    try:
        user_path = get_user_upload_path(username)
        if os.path.exists(user_path):
            shutil.rmtree(user_path)
            logging.info(f"Alle Dateien für Benutzer {username} wurden gelöscht")
        return True
    except Exception as e:
        logging.error(f"Fehler beim Löschen der Dateien für Benutzer {username}: {str(e)}")
        return False 