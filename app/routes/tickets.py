from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, render_template_string, current_app
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
from app.utils.file_utils import allowed_file, ensure_user_directories
import uuid
import docx2pdf
from PyPDF2 import PdfMerger
import subprocess

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
    """Zeigt die Bewerbungsübersicht für den Benutzer."""
    try:
        # Hole die Templates des Benutzers
        templates = ticket_db.query("""
            SELECT id, name, file_name, category, created_at
            FROM application_templates
            WHERE created_by = ? AND is_active = 1
            ORDER BY created_at DESC
        """, [current_user.username])
        
        logging.info(f"Gefundene Templates für {current_user.username}: {templates}")
        
        # Hole die Dokumente des Benutzers
        documents = ticket_db.query("""
            SELECT id, file_name, document_type, created_at
            FROM application_documents
            WHERE created_by = ? AND is_active = 1
            ORDER BY created_at DESC
        """, [current_user.username])
        
        # Hole die Bewerbungen des Benutzers
        applications = ticket_db.query("""
            SELECT a.*, t.name as template_name
            FROM applications a
            LEFT JOIN application_templates t ON a.template_id = t.id
            WHERE a.erstellt_von = ?
            ORDER BY a.erstellt_am DESC
        """, [current_user.username])
        
        return render_template('tickets/applications.html',
                             templates=templates,
                             documents=documents,
                             applications=applications)
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Bewerbungsseite: {str(e)}")
        flash('Fehler beim Laden der Bewerbungsseite.', 'error')
        return redirect(url_for('tickets.index'))

@bp.route('/applications/template/upload', methods=['POST'])
@login_required
def upload_template():
    """Lädt ein neues Bewerbungstemplate hoch"""
    try:
        # Überprüfe die Datenbanktabelle
        tables = ticket_db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='application_templates'")
        if not tables:
            logger.error("Tabelle application_templates existiert nicht")
            # Erstelle die Tabelle
            ticket_db.query("""
                CREATE TABLE IF NOT EXISTS application_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    category TEXT,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            logger.info("Tabelle application_templates wurde erstellt")
        
        if 'template' not in request.files:
            logger.warning("Keine Datei im Request gefunden")
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('tickets.applications'))
            
        file = request.files['template']
        if file.filename == '':
            logger.warning("Leerer Dateiname")
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('tickets.applications'))
            
        if not allowed_file(file.filename):
            logger.warning(f"Ungültiger Dateityp: {file.filename}")
            flash('Nur .docx Dateien sind erlaubt', 'error')
            return redirect(url_for('tickets.applications'))
        
        # Erstelle Benutzerverzeichnisse
        try:
            user_path = ensure_user_directories(current_user.username)
            logger.info(f"Benutzerverzeichnisse erstellt für {current_user.username}")
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Verzeichnisse: {str(e)}")
            flash('Fehler beim Erstellen der Verzeichnisse', 'error')
            return redirect(url_for('tickets.applications'))
        
        # Speichere die Datei
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(user_path, 'templates', filename)
            file.save(filepath)
            logger.info(f"Template gespeichert unter: {filepath}")
            
            # Überprüfe, ob die Datei tatsächlich gespeichert wurde
            if not os.path.exists(filepath):
                raise Exception("Datei wurde nicht gespeichert")
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Datei: {str(e)}")
            flash('Fehler beim Speichern der Datei', 'error')
            return redirect(url_for('tickets.applications'))
        
        # Speichere Template in der Datenbank
        try:
            template_name = request.form.get('name', filename)
            category = request.form.get('category', '')
            
            # Überprüfe, ob das Template bereits existiert
            existing_template = ticket_db.query("""
                SELECT id FROM application_templates 
                WHERE file_name = ? AND created_by = ? AND is_active = 1
            """, [filename, current_user.username])
            
            if existing_template:
                logger.warning(f"Template {filename} existiert bereits")
                flash('Ein Template mit diesem Namen existiert bereits', 'error')
                return redirect(url_for('tickets.applications'))
            
            # Füge das Template hinzu
            ticket_db.query("""
                INSERT INTO application_templates (name, file_path, file_name, category, created_by, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, [template_name, filepath, filename, category, current_user.username])
            
            # Überprüfe, ob das Template gespeichert wurde
            saved_template = ticket_db.query("""
                SELECT * FROM application_templates 
                WHERE file_name = ? AND created_by = ? AND is_active = 1
            """, [filename, current_user.username])
            
            if not saved_template:
                raise Exception("Template wurde nicht in der Datenbank gespeichert")
            
            logger.info(f"Template in Datenbank gespeichert: {template_name}")
            flash('Template erfolgreich hochgeladen', 'success')
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern in der Datenbank: {str(e)}")
            # Lösche die Datei wieder, da die Datenbankoperation fehlgeschlagen ist
            try:
                os.remove(filepath)
            except:
                pass
            flash('Fehler beim Speichern in der Datenbank', 'error')
            return redirect(url_for('tickets.applications'))
        
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Hochladen des Templates: {str(e)}")
        flash(f'Unerwarteter Fehler: {str(e)}', 'error')
        
    return redirect(url_for('tickets.applications'))

@bp.route('/applications/create', methods=['POST'])
@login_required
def create_application():
    """Erstellt eine neue Bewerbung."""
    try:
        # Hole die Formulardaten
        template_id = request.form.get('template_id')
        firmenname = request.form.get('firmenname')
        position = request.form.get('position')
        ansprechpartner = request.form.get('ansprechpartner')
        anrede = request.form.get('anrede')
        email = request.form.get('email')
        telefon = request.form.get('telefon')
        adresse = request.form.get('adresse')
        eigener_text = request.form.get('eigener_text')
        
        # Validiere die Pflichtfelder
        if not all([template_id, firmenname, position]):
            flash('Bitte füllen Sie alle Pflichtfelder aus.', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Hole das Template
        template = ticket_db.query("""
            SELECT * FROM application_templates 
            WHERE id = ? AND created_by = ? AND is_active = 1
        """, [template_id, current_user.username], one=True)
        
        if not template:
            flash('Template nicht gefunden.', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Erstelle die Bewerbung
        ticket_db.query("""
            INSERT INTO applications (
                template_id, firmenname, position, ansprechpartner, 
                anrede, email, telefon, adresse, eigener_text,
                erstellt_von, erstellt_am, aktualisiert_am
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, [
            template_id, firmenname, position, ansprechpartner,
            anrede, email, telefon, adresse, eigener_text,
            current_user.username
        ])
        
        flash('Bewerbung wurde erfolgreich erstellt.', 'success')
        return redirect(url_for('tickets.applications'))
        
    except Exception as e:
        logging.error(f"Fehler beim Erstellen der Bewerbung: {str(e)}")
        flash('Fehler beim Erstellen der Bewerbung.', 'error')
        return redirect(url_for('tickets.applications'))

@bp.route('/applications/<int:id>/update_status', methods=['POST'])
@login_required
def update_application_status(id):
    """Aktualisiert den Status einer Bewerbung"""
    try:
        status = request.form.get('status')
        notes = request.form.get('notes', '')
        
        if not status:
            flash('Status ist erforderlich', 'error')
            return redirect(url_for('tickets.applications'))
        
        ticket_db.query("""
            UPDATE applications 
            SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
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
@login_required
def application_details(id):
    """Detailansicht einer Bewerbung"""
    try:
        # Hole die Bewerbung aus der Datenbank
        application = ticket_db.query("""
            SELECT a.*, t.name as template_name
            FROM applications a
            LEFT JOIN application_templates t ON a.template_id = t.id
            WHERE a.id = ? AND a.created_by = ?
        """, [id, current_user.username])
        
        if not application:
            flash('Bewerbung nicht gefunden', 'error')
            return redirect(url_for('tickets.applications'))
            
        application = application[0]
        
        # Konvertiere generated_content von String zu Dict
        if application.get('generated_content'):
            try:
                application['generated_content'] = eval(application['generated_content'])
            except:
                application['generated_content'] = {}
        
        return render_template('tickets/application_details.html', application=application)
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Bewerbungsdetails: {str(e)}")
        flash('Fehler beim Laden der Bewerbungsdetails', 'error')
        return redirect(url_for('tickets.applications'))

@bp.route('/applications/<int:id>/download')
@login_required
def download_application(id):
    """Lädt eine Bewerbung herunter."""
    try:
        # Hole die Bewerbung aus der Datenbank
        application = ticket_db.query("""
            SELECT a.*, t.name as template_name
            FROM applications a
            LEFT JOIN application_templates t ON a.template_id = t.id
            WHERE a.id = ? AND a.created_by = ?
        """, [id, current_user.username], one=True)
        
        if not application:
            flash('Bewerbung nicht gefunden.', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Prüfe ob PDF existiert
        pdf_path = application['pdf_path']
        if not pdf_path:
            flash('PDF-Datei nicht gefunden.', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Konstruiere den absoluten Pfad
        if not pdf_path.startswith('/'):
            pdf_path = os.path.join(os.getcwd(), pdf_path)
            
        if not os.path.exists(pdf_path):
            flash('PDF-Datei nicht gefunden.', 'error')
            return redirect(url_for('tickets.applications'))
            
        # Generiere Dateinamen
        filename = f"bewerbung_{application['company_name']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        # Sende Datei
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
            
    except Exception as e:
        current_app.logger.error(f"Fehler beim Herunterladen der Bewerbung: {str(e)}")
        flash('Fehler beim Herunterladen der Bewerbung.', 'error')
        return redirect(url_for('tickets.applications'))

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

@bp.route('/applications/debug')
@login_required
def debug_applications():
    """Debug-Route für die Bewerbungsverwaltung"""
    try:
        # Überprüfe die Tabellen
        tables = ticket_db.query("SELECT name FROM sqlite_master WHERE type='table'")
        result = {
            'tables': tables,
            'templates': ticket_db.query("SELECT * FROM application_templates"),
            'documents': ticket_db.query("SELECT * FROM application_documents"),
            'applications': ticket_db.query("SELECT * FROM applications")
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def convert_docx_to_pdf(input_path, output_path):
    """Konvertiert eine DOCX-Datei in PDF mit pandoc oder docx2pdf"""
    try:
        # Versuche zuerst mit pandoc und behalte die Formatierung bei
        logger.info(f"Versuche Konvertierung mit pandoc: {input_path} -> {output_path}")
        result = subprocess.run([
            'pandoc',
            input_path,
            '-o', output_path,
            '--pdf-engine=wkhtmltopdf',
            '--reference-doc=' + input_path  # Behalte die Formatierung des Original-Dokuments bei
        ], capture_output=True, text=True, check=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info("PDF-Konvertierung mit pandoc erfolgreich")
        return True
            
        # Wenn pandoc fehlschlägt, versuche docx2pdf mit Formatierungserhaltung
        logger.info("Pandoc-Konvertierung fehlgeschlagen, versuche docx2pdf")
        import docx2pdf
        docx2pdf.convert(input_path, output_path, keep_active=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info("PDF-Konvertierung mit docx2pdf erfolgreich")
            return True
            
        logger.error("Beide Konvertierungsmethoden sind fehlgeschlagen")
        return False
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler bei der PDF-Konvertierung mit pandoc: {e.stderr}")
        try:
            # Versuche docx2pdf als Fallback mit Formatierungserhaltung
            logger.info("Versuche Konvertierung mit docx2pdf")
            import docx2pdf
            docx2pdf.convert(input_path, output_path, keep_active=True)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info("PDF-Konvertierung mit docx2pdf erfolgreich")
                return True
        except Exception as e2:
            logger.error(f"Fehler bei der PDF-Konvertierung mit docx2pdf: {str(e2)}")
        return False 
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei der PDF-Konvertierung: {str(e)}")
        return False

@bp.route('/applications/<int:id>/delete', methods=['POST'])
@login_required
def delete_application(id):
    """Löscht eine Bewerbung"""
    try:
        # Bewerbung aus der Datenbank holen
        application = ticket_db.query("""
            SELECT * FROM applications 
            WHERE id = ? AND created_by = ?
        """, [id, current_user.username], one=True)
        
        if not application:
            return jsonify({'success': False, 'message': 'Bewerbung nicht gefunden'})
            
        # PDF-Datei löschen
        pdf_path = application['pdf_path']
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception as e:
                logging.error(f"Fehler beim Löschen der PDF-Datei: {str(e)}")
        
        # Bewerbung aus der Datenbank löschen
        ticket_db.query("""
            DELETE FROM applications 
            WHERE id = ?
        """, [id])
            
        return jsonify({'success': True, 'message': 'Bewerbung erfolgreich gelöscht'})
        
    except Exception as e:
        logging.error(f"Fehler beim Löschen der Bewerbung: {str(e)}")
        return jsonify({'success': False, 'message': f'Fehler beim Löschen der Bewerbung: {str(e)}'}) 