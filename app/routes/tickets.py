from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.models.ticket_db import TicketDatabase
from app.utils.decorators import login_required, admin_required
import logging
from datetime import datetime

bp = Blueprint('tickets', __name__, url_prefix='/tickets')
ticket_db = TicketDatabase()

@bp.route('/')
@admin_required
def index():
    """Zeigt die Übersicht aller Tickets."""
    # Filter aus Query-Parametern
    status = request.args.get('status')
    priority = request.args.get('priority')
    assigned_to = request.args.get('assigned_to')
    created_by = request.args.get('created_by')
    
    # Basis-Query
    query = """
        SELECT *
        FROM tickets
        WHERE 1=1
    """
    params = []
    
    # Filter anwenden
    if status and status != 'alle':
        query += " AND status = ?"
        params.append(status)
    if priority and priority != 'alle':
        query += " AND priority = ?"
        params.append(priority)
    if assigned_to:
        query += " AND assigned_to = ?"
        params.append(assigned_to)
    if created_by:
        query += " AND created_by = ?"
        params.append(created_by)
    
    query += " ORDER BY created_at DESC"
    
    tickets = ticket_db.query(query, params)
    return render_template('tickets/index.html', tickets=tickets)

@bp.route('/create', methods=['GET', 'POST'])
def create():
    """Erstellt ein neues Ticket."""
    if request.method == 'POST':
        try:
            # Logging für Debugging
            logging.info(f"Content-Type: {request.content_type}")
            logging.info(f"Request Data: {request.get_data()}")
            
            # Versuche zuerst JSON zu parsen
            if request.is_json:
                data = request.get_json()
            else:
                # Fallback auf Form-Daten
                data = request.form.to_dict()
            
            logging.info(f"Verarbeitete Daten: {data}")
            
            title = data.get('title')
            description = data.get('description')
            priority = data.get('priority', 'normal')
            assigned_to = data.get('assigned_to')
            
            if not title or not description:
                return jsonify({
                    'success': False,
                    'message': 'Titel und Beschreibung sind erforderlich'
                }), 400
            
            # Benutzer aus Session oder 'Anonym'
            created_by = session.get('username', 'Anonym')
            
            ticket_db.query(
                """
                INSERT INTO tickets (title, description, priority, created_by, assigned_to)
                VALUES (?, ?, ?, ?, ?)
                """,
                [title, description, priority, created_by, assigned_to]
            )
            
            # Wenn es eine AJAX-Anfrage ist, JSON zurückgeben
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Ticket wurde erstellt'
                })
            
            # Weiterleitung basierend auf Benutzerstatus
            if session.get('is_admin'):
                return redirect(url_for('tickets.index'))
            else:
                return redirect(url_for('main.index'))
            
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': f'Fehler beim Erstellen des Tickets: {str(e)}'
                }), 500
            return redirect(url_for('tickets.create'))
            
    return render_template('tickets/create.html')

@bp.route('/<int:id>')
@admin_required
def detail(id):
    """Zeigt die Details eines Tickets."""
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
        
    # Hole die Notizen für das Ticket
    notes = ticket_db.query(
        """
        SELECT *
        FROM ticket_notes
        WHERE ticket_id = ?
        ORDER BY created_at DESC
        """,
        [id]
    )
    
    return render_template('tickets/detail.html', ticket=ticket, notes=notes)

@bp.route('/<int:id>/update', methods=['POST'])
@admin_required
def update(id):
    try:
        logging.info(f"Update-Anfrage für Ticket #{id} empfangen")
        logging.info(f"Content-Type: {request.content_type}")
        logging.info(f"Request Data: {request.get_data()}")
        
        # Versuche zuerst JSON zu parsen, falls nicht möglich, verwende Form-Daten
        try:
            data = request.get_json()
        except:
            data = request.form.to_dict()
            
        logging.info(f"Verarbeitete Daten: {data}")
        
        if not data:
            logging.error("Keine Daten in der Anfrage")
            return jsonify({
                'success': False,
                'message': 'Keine Daten erhalten'
            }), 400
            
        status = data.get('status')
        assigned_to = data.get('assigned_to')
        resolution_notes = data.get('resolution_notes')
        author_name = data.get('author_name')
        
        logging.info(f"Verarbeite Daten: status={status}, assigned_to={assigned_to}, has_notes={'ja' if resolution_notes else 'nein'}, author={author_name}")

        if not status:
            logging.error("Status fehlt in den Daten")
            return jsonify({
                'success': False,
                'message': 'Status ist erforderlich'
            }), 400

        if not author_name:
            logging.error("Name fehlt in den Daten")
            return jsonify({
                'success': False,
                'message': 'Name ist erforderlich'
            }), 400

        if status not in ['offen', 'in_bearbeitung', 'gelöst']:
            logging.error(f"Ungültiger Status: {status}")
            return jsonify({
                'success': False,
                'message': 'Ungültiger Status'
            }), 400

        # Update ticket status and assigned_to
        logging.info("Führe Ticket-Update durch...")
        ticket_db.query(
            """
            UPDATE tickets 
            SET status = ?,
                assigned_to = ?,
                updated_at = CURRENT_TIMESTAMP,
                resolved_at = CASE 
                    WHEN ? = 'gelöst' THEN CURRENT_TIMESTAMP 
                    ELSE NULL 
                END
            WHERE id = ?
            """,
            [status, assigned_to, status, id]
        )
        logging.info("Ticket-Update erfolgreich")

        # Add note if provided
        if resolution_notes and resolution_notes.strip():
            logging.info("Füge neue Notiz hinzu...")
            ticket_db.query(
                """
                INSERT INTO ticket_notes (ticket_id, note, created_by)
                VALUES (?, ?, ?)
                """,
                [id, resolution_notes.strip(), author_name]
            )
            logging.info("Notiz erfolgreich hinzugefügt")

        logging.info("Update erfolgreich abgeschlossen")
        return redirect(url_for('tickets.index'))

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets #{id}: {str(e)}")
        logging.exception(e)  # Dies gibt den kompletten Stacktrace aus
        return jsonify({
            'success': False,
            'message': f'Ein Fehler ist aufgetreten: {str(e)}'
        }), 500 

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