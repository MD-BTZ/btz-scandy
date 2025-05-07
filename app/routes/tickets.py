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
    
    return render_template('tickets/detail.html', ticket=ticket, notes=notes, workers=workers)

@bp.route('/<int:id>/update', methods=['POST'])
@login_required
def update(id):
    """Aktualisiert ein Ticket"""
    try:
        # Hole das Ticket
        ticket = ticket_db.get_ticket(id)
        if not ticket:
            flash('Ticket nicht gefunden', 'error')
            return redirect(url_for('tickets.index'))

        # Hole die Formulardaten
        status = request.form.get('status')
        assigned_to = request.form.get('assigned_to')
        resolution_notes = request.form.get('resolution_notes')
        author_name = current_user.username  # Benutzername aus current_user
        category = request.form.get('category')
        due_date = request.form.get('due_date')
        estimated_time = request.form.get('estimated_time')
        actual_time = request.form.get('actual_time')
        is_private = request.form.get('is_private') == 'on'

        # Validiere die Eingaben
        if not status:
            flash('Status ist erforderlich', 'error')
            return redirect(url_for('tickets.detail', id=id))

        if not author_name:
            flash('Sie müssen eingeloggt sein, um Tickets zu bearbeiten', 'error')
            return redirect(url_for('tickets.detail', id=id))

        # Aktualisiere das Ticket
        ticket_db.update_ticket(
            id=id,
            status=status,
            assigned_to=assigned_to,
            category=category,
            due_date=due_date,
            estimated_time=estimated_time,
            actual_time=actual_time,
            last_modified_by=author_name
        )

        # Füge eine Notiz hinzu, wenn vorhanden
        if resolution_notes:
            ticket_db.add_note(
                ticket_id=id,
                note=resolution_notes,
                author_name=author_name,
                is_private=is_private
            )

        flash('Ticket erfolgreich aktualisiert', 'success')
        return redirect(url_for('tickets.detail', id=id))

    except Exception as e:
        flash(f'Fehler beim Aktualisieren des Tickets: {str(e)}', 'error')
        return redirect(url_for('tickets.detail', id=id))

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