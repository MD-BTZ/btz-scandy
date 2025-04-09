from flask import Blueprint, render_template, request, jsonify, session
from app.models.database import Database
from app.utils.decorators import login_required, admin_required
import logging
from datetime import datetime

bp = Blueprint('tickets', __name__, url_prefix='/tickets')
db = Database()

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
        SELECT 
            t.*,
            creator.username as creator_name,
            assignee.username as assignee_name
        FROM tickets t
        LEFT JOIN users creator ON t.created_by = creator.username
        LEFT JOIN users assignee ON t.assigned_to = assignee.username
        WHERE 1=1
    """
    params = []
    
    # Filter anwenden
    if status and status != 'alle':
        query += " AND t.status = ?"
        params.append(status)
    if priority and priority != 'alle':
        query += " AND t.priority = ?"
        params.append(priority)
    if assigned_to:
        query += " AND t.assigned_to = ?"
        params.append(assigned_to)
    if created_by:
        query += " AND t.created_by = ?"
        params.append(created_by)
    
    query += " ORDER BY t.created_at DESC"
    
    tickets = db.query(query, params)
    return render_template('tickets/index.html', tickets=tickets)

@bp.route('/create', methods=['GET', 'POST'])
def create():
    """Erstellt ein neues Ticket."""
    if request.method == 'POST':
        try:
            data = request.get_json()
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
            
            db.query(
                """
                INSERT INTO tickets (title, description, priority, created_by, assigned_to)
                VALUES (?, ?, ?, ?, ?)
                """,
                [title, description, priority, created_by, assigned_to]
            )
            
            return jsonify({
                'success': True,
                'message': 'Ticket wurde erstellt'
            })
            
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Fehler beim Erstellen des Tickets'
            }), 500
            
    return render_template('tickets/create.html')

@bp.route('/<int:id>')
@admin_required
def detail(id):
    """Zeigt die Details eines Tickets."""
    ticket = db.query(
        """
        SELECT t.*,
               creator.username as creator_name
        FROM tickets t
        LEFT JOIN users creator ON t.created_by = creator.username
        WHERE t.id = ?
        """,
        [id],
        one=True
    )
    
    if not ticket:
        return render_template('404.html'), 404
        
    # Hole die Notizen für das Ticket
    notes = db.query(
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
        
        logging.info(f"Verarbeite Daten: status={status}, assigned_to={assigned_to}, has_notes={'ja' if resolution_notes else 'nein'}")

        if not status:
            logging.error("Status fehlt in den Daten")
            return jsonify({
                'success': False,
                'message': 'Status ist erforderlich'
            }), 400

        if status not in ['offen', 'in_bearbeitung', 'gelöst']:
            logging.error(f"Ungültiger Status: {status}")
            return jsonify({
                'success': False,
                'message': 'Ungültiger Status'
            }), 400

        # Update ticket status and assigned_to
        logging.info("Führe Ticket-Update durch...")
        db.query(
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
            db.query(
                """
                INSERT INTO ticket_notes (ticket_id, note, created_by)
                VALUES (?, ?, ?)
                """,
                [id, resolution_notes.strip(), session.get('username')]
            )
            logging.info("Notiz erfolgreich hinzugefügt")

        logging.info("Update erfolgreich abgeschlossen")
        return jsonify({
            'success': True, 
            'message': 'Ticket wurde erfolgreich aktualisiert'
        })

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets #{id}: {str(e)}")
        logging.exception(e)  # Dies gibt den kompletten Stacktrace aus
        return jsonify({
            'success': False,
            'message': f'Ein Fehler ist aufgetreten: {str(e)}'
        }), 500 