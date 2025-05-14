from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, abort
from app.models.ticket_db import TicketDatabase
from app.models.database import Database
from app.utils.decorators import login_required, admin_required
import logging
from datetime import datetime
from flask_login import current_user

bp = Blueprint('tickets', __name__, url_prefix='/tickets')
ticket_db = TicketDatabase()

@bp.route('/')
@login_required
def index():
    """Zeigt die Ticket-Übersicht für den Benutzer."""
    # Hole die eigenen Tickets für die Anzeige
    my_tickets = ticket_db.query(
        """
        SELECT t.*, COUNT(tm.id) as message_count
        FROM tickets t
        LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
        WHERE t.created_by = ?
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
            title = request.form.get('title')
            description = request.form.get('description')
            priority = request.form.get('priority', 'normal')
            
            # Erstelle das Ticket mit der korrekten Datenbankverbindung
            with ticket_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tickets 
                    (title, description, status, priority, created_by, created_at, updated_at)
                    VALUES (?, ?, 'offen', ?, ?, datetime('now'), datetime('now'))
                """, [title, description, priority, current_user.username])
                
                ticket_id = cursor.lastrowid
                conn.commit()
            
            flash('Ticket wurde erfolgreich erstellt', 'success')
            return redirect(url_for('tickets.create'))
            
        except Exception as e:
            logging.error(f"Fehler beim Erstellen des Tickets: {str(e)}")
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': f'Fehler beim Erstellen des Tickets: {str(e)}'
                }), 500
            flash(f'Fehler beim Erstellen des Tickets: {str(e)}', 'error')
            return redirect(url_for('tickets.create'))
    
    # Hole die eigenen Tickets für die Anzeige
    my_tickets = ticket_db.query(
        """
        SELECT t.*, COUNT(tm.id) as message_count
        FROM tickets t
        LEFT JOIN ticket_messages tm ON t.id = tm.ticket_id
        WHERE t.created_by = ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """,
        [current_user.username]
    )
            
    return render_template('tickets/create.html', my_tickets=my_tickets)

@bp.route('/view/<int:id>')
@login_required
def view(id):
    """Zeigt die Detailansicht eines Tickets für den Benutzer."""
    # Hole das Ticket
    ticket = ticket_db.query(
        """
        SELECT *
        FROM tickets
        WHERE id = ? AND created_by = ?
        """,
        [id, current_user.username],
        one=True
    )
    
    if not ticket:
        abort(404)
    
    # Konvertiere Datumsfelder
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket[field]:
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
    
    # Hole die Nachrichten für dieses Ticket
    messages = ticket_db.query(
        """
        SELECT *
        FROM ticket_messages
        WHERE ticket_id = ?
        ORDER BY created_at ASC
        """,
        [id]
    )
    
    # Zähle die Anzahl der Nachrichten
    message_count = len(messages) if messages else 0
    
    return render_template('tickets/view.html', 
                         ticket=ticket, 
                         messages=messages,
                         message_count=message_count)

@bp.route('/<int:ticket_id>/message', methods=['POST'])
@login_required
def add_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu."""
    try:
        # Ticket aus der Datenbank abrufen
        ticket = ticket_db.query(
            """
            SELECT *
            FROM tickets
            WHERE id = ? AND created_by = ?
            """,
            [ticket_id, current_user.username],
            one=True
        )
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Nachricht aus dem Request extrahieren
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'message': 'Keine Nachricht angegeben'}), 400

        message = data['message'].strip()
        if not message:
            return jsonify({'success': False, 'message': 'Nachricht darf nicht leer sein'}), 400

        # Nachricht zur Datenbank hinzufügen
        with Database.get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                """
                INSERT INTO ticket_messages (ticket_id, message, sender, is_admin, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                [ticket_id, message, current_user.username, False]
            )
            
            # Ticket updated_at aktualisieren
            cursor.execute(
                """
                UPDATE tickets
                SET updated_at = datetime('now')
                WHERE id = ?
                """,
                [ticket_id]
            )
            
            db.commit()

            # Hole die eingefügte Nachricht
            cursor.execute(
                """
                SELECT id, message, sender, is_admin, created_at
                FROM ticket_messages
                WHERE ticket_id = ? AND sender = ? AND message = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                [ticket_id, current_user.username, message]
            )
            new_message = cursor.fetchone()

            if not new_message:
                return jsonify({'success': False, 'message': 'Fehler beim Abrufen der Nachricht'}), 500

            return jsonify({
                'success': True,
                'message': {
                    'id': new_message['id'],
                    'message': new_message['message'],
                    'sender': new_message['sender'],
                    'is_admin': new_message['is_admin'],
                    'created_at': new_message['created_at']
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
                         now=datetime.now())

@bp.route('/<int:id>/update', methods=['POST'])
@login_required
def update(id):
    """Aktualisiert ein Ticket"""
    try:
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
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Hole die Formulardaten
        data = request.get_json()
        status = data.get('status')
        assigned_to = data.get('assigned_to')
        resolution_notes = data.get('resolution_notes')
        response = data.get('response')
        author_name = current_user.username
        priority = data.get('priority')
        due_date = data.get('due_date')
        is_private = data.get('is_private', False)

        # Konvertiere due_date zu SQLite-Format
        if due_date:
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                due_date = due_date.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                due_date = None

        # Aktualisiere das Ticket
        ticket_db.query(
            """
            UPDATE tickets
            SET status = ?,
                assigned_to = ?,
                priority = ?,
                due_date = ?,
                response = ?,
                last_modified_by = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            [status, assigned_to, priority, due_date, response, author_name, id]
        )

        # Füge eine Notiz hinzu, wenn vorhanden
        if resolution_notes:
            ticket_db.query(
                """
                INSERT INTO ticket_notes (ticket_id, note, created_by, is_private, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                [id, resolution_notes, author_name, is_private]
            )

        return jsonify({
            'success': True,
            'message': 'Ticket erfolgreich aktualisiert'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler: {str(e)}'
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