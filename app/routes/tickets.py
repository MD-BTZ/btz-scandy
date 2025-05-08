from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from app.models.ticket_db import TicketDatabase
from app.models.database import Database
from app.utils.decorators import login_required, admin_required
import logging
from datetime import datetime
from flask_login import current_user

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
            created_by = current_user.username
            
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
                         workers=workers,
                         now=datetime.now())

@bp.route('/<int:id>/update', methods=['POST'])
@login_required
def update(id):
    """Aktualisiert ein Ticket"""
    try:
        # Logging für Debugging
        logging.info(f"Update-Anfrage für Ticket {id}")
        logging.info(f"Form-Daten: {request.form}")
        
        # Hole das Ticket
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
            logging.error(f"Ticket {id} nicht gefunden")
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Hole die Formulardaten
        status = request.form.get('status')
        assigned_to = request.form.get('assigned_to')
        resolution_notes = request.form.get('resolution_notes')
        author_name = current_user.username
        priority = request.form.get('priority')
        due_date = request.form.get('due_date')
        estimated_time = request.form.get('estimated_time')
        actual_time = request.form.get('actual_time')
        is_private = request.form.get('is_private') == 'on'

        # Logging der verarbeiteten Daten
        logging.info(f"Verarbeitete Daten: status={status}, assigned_to={assigned_to}, priority={priority}, due_date={due_date}")

        # Validiere die Eingaben
        if not status:
            logging.error("Status fehlt in der Anfrage")
            return jsonify({
                'success': False,
                'message': 'Status ist erforderlich'
            }), 400

        if not author_name:
            logging.error("Kein Benutzername verfügbar")
            return jsonify({
                'success': False,
                'message': 'Sie müssen eingeloggt sein, um Tickets zu bearbeiten'
            }), 401

        try:
            # Aktualisiere das Ticket
            ticket_db.query(
                """
                UPDATE tickets
                SET status = ?,
                    assigned_to = ?,
                    priority = ?,
                    due_date = ?,
                    estimated_time = ?,
                    actual_time = ?,
                    last_modified_by = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                [status, assigned_to, priority, due_date, estimated_time, actual_time, author_name, id]
            )
            logging.info(f"Ticket {id} erfolgreich aktualisiert")

            # Füge eine Notiz hinzu, wenn vorhanden
            if resolution_notes:
                ticket_db.query(
                    """
                    INSERT INTO ticket_notes (ticket_id, note, created_by, is_private, created_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    """,
                    [id, resolution_notes, author_name, is_private]
                )
                logging.info(f"Notiz zu Ticket {id} hinzugefügt")

            return jsonify({
                'success': True,
                'message': 'Ticket erfolgreich aktualisiert'
            })

        except Exception as db_error:
            logging.error(f"Datenbankfehler bei Ticket {id}: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': f'Datenbankfehler: {str(db_error)}'
            }), 500

    except Exception as e:
        logging.error(f"Unerwarteter Fehler bei Ticket {id}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Unerwarteter Fehler: {str(e)}'
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