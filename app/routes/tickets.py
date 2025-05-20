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
    
    # Konvertiere Datumsfelder
    for ticket in my_tickets:
        date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
        for field in date_fields:
            if ticket.get(field):
                try:
                    if isinstance(ticket[field], str):
                        ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError) as e:
                    logging.error(f"Fehler beim Konvertieren des Datums {field} für Ticket {ticket['id']}: {str(e)}")
                    ticket[field] = None
            
    return render_template('tickets/index.html', tickets=my_tickets, now=datetime.now())

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Erstellt ein neues Ticket."""
    if request.method == 'POST':
        try:
            # Prüfe ob die Daten als JSON oder Formular gesendet wurden
            if request.is_json:
                data = request.get_json()
                title = data.get('title')
                description = data.get('description')
                priority = data.get('priority', 'normal')
                category = data.get('category', '').strip()
                due_date = data.get('due_date')
                estimated_time = data.get('estimated_time')
            else:
                title = request.form.get('title')
                description = request.form.get('description')
                priority = request.form.get('priority', 'normal')
                category = request.form.get('category', '').strip()
                due_date = request.form.get('due_date')
                estimated_time = request.form.get('estimated_time', type=int)

            # Validiere die erforderlichen Felder
            if not title:
                raise ValueError("Titel ist erforderlich")
            if not description:
                raise ValueError("Beschreibung ist erforderlich")
            
            # Erstelle das Ticket mit der korrekten Datenbankverbindung
            with ticket_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Prüfe ob die Kategorie bereits existiert
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM tickets 
                    WHERE category = ?
                """, [category])
                category_exists = cursor.fetchone()['count'] > 0
                
                # Wenn es eine neue Kategorie ist, füge sie zur Kategorieliste hinzu
                if not category_exists and category:  # Nur wenn Kategorie nicht leer ist
                    cursor.execute("""
                        INSERT INTO categories (name, created_at)
                        VALUES (?, datetime('now'))
                    """, [category])
                
                # Erstelle das Ticket
                cursor.execute("""
                    INSERT INTO tickets 
                    (title, description, status, priority, category, due_date, estimated_time, created_by, created_at, updated_at)
                    VALUES (?, ?, 'offen', ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """, [title, description, priority, category, due_date, estimated_time, current_user.username])
                
                ticket_id = cursor.lastrowid
                conn.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Ticket wurde erfolgreich erstellt',
                    'ticket_id': ticket_id
                })
            
            flash('Ticket wurde erfolgreich erstellt', 'success')
            return redirect(url_for('tickets.create'))
            
        except ValueError as e:
            error_message = str(e)
            logging.error(f"Validierungsfehler beim Erstellen des Tickets: {error_message}")
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 400
            flash(error_message, 'error')
            return redirect(url_for('tickets.create'))
        except Exception as e:
            error_message = f"Fehler beim Erstellen des Tickets: {str(e)}"
            logging.error(error_message)
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 500
            flash(error_message, 'error')
            return redirect(url_for('tickets.create'))
    
    # Hole die Kategorien für das Dropdown
    categories = ticket_db.query("""
        SELECT DISTINCT category 
        FROM tickets 
        WHERE category IS NOT NULL 
        ORDER BY category
    """)
    
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
    
    # Konvertiere Datumsfelder
    for ticket in my_tickets:
        date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
        for field in date_fields:
            if ticket.get(field):
                try:
                    if isinstance(ticket[field], str):
                        ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError) as e:
                    logging.error(f"Fehler beim Konvertieren des Datums {field} für Ticket {ticket['id']}: {str(e)}")
                    ticket[field] = None
            
    return render_template('tickets/create.html', 
                         my_tickets=my_tickets,
                         categories=[c['category'] for c in categories],
                         now=datetime.now())

@bp.route('/view/<int:ticket_id>')
@login_required
def view(ticket_id):
    """Zeigt die Details eines Tickets an."""
    logging.info(f"Lade Ticket {ticket_id} für Benutzer {current_user.username}")
    
    # Hole das Ticket
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
        abort(404)
    
    logging.info("Hole Nachrichten für Ticket {ticket_id}")
    
    # Hole die Nachrichten mit der richtigen Datenbankverbindung
    messages = ticket_db.get_ticket_messages(ticket_id)
    
    # Formatiere die Datumsangaben
    for message in messages:
        if message['created_at']:
            try:
                created_at = datetime.strptime(message['created_at'], '%Y-%m-%d %H:%M:%S')
                message['created_at'] = created_at.strftime('%d.%m.%Y, %H:%M')
            except ValueError as e:
                logging.error(f"Fehler beim Formatieren des Datums für Nachricht {message['id']}: {str(e)}")
    
    message_count = len(messages)
    logging.info(f"Nachrichtenanzahl: {message_count}")
    
    # Hole die Notizen für das Ticket
    notes = ticket_db.get_ticket_notes(ticket_id)
    
    # Konvertiere Datumsfelder des Tickets
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                if isinstance(ticket[field], str):
                    ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError) as e:
                logging.error(f"Fehler beim Konvertieren des Datums {field} für Ticket {ticket_id}: {str(e)}")
                ticket[field] = None
    
    return render_template('tickets/view.html',
                         ticket=ticket,
                         messages=messages,
                         notes=notes,
                         message_count=message_count,
                         now=datetime.now())

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
            logging.error(f"Ticket {ticket_id} nicht gefunden für Benutzer {current_user.username}")
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Nachricht aus dem Request extrahieren
        data = request.get_json()
        if not data or 'message' not in data:
            logging.error("Keine Nachricht im Request gefunden")
            return jsonify({'success': False, 'message': 'Keine Nachricht angegeben'}), 400

        message = data['message'].strip()
        if not message:
            logging.error("Leere Nachricht")
            return jsonify({'success': False, 'message': 'Nachricht darf nicht leer sein'}), 400

        logging.info(f"Versuche Nachricht zu speichern: Ticket {ticket_id}, Benutzer {current_user.username}, Nachricht: {message}")

        # Nachricht zur Datenbank hinzufügen
        with ticket_db.get_connection() as conn:
            cursor = conn.cursor()
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
            
            conn.commit()
            logging.info(f"Nachricht erfolgreich gespeichert mit ID {cursor.lastrowid}")

            # Hole die eingefügte Nachricht
            cursor.execute(
                """
                SELECT id, message, sender, is_admin, created_at
                FROM ticket_messages
                WHERE id = ?
                """,
                [cursor.lastrowid]
            )
            new_message = cursor.fetchone()

            if not new_message:
                logging.error("Konnte die neue Nachricht nicht abrufen")
                return jsonify({'success': False, 'message': 'Fehler beim Abrufen der Nachricht'}), 500

            # Formatiere das Datum
            created_at = datetime.strptime(new_message['created_at'], '%Y-%m-%d %H:%M:%S')
            formatted_date = created_at.strftime('%d.%m.%Y, %H:%M')

            return jsonify({
                'success': True,
                'message': {
                    'text': new_message['message'],
                    'sender': new_message['sender'],
                    'created_at': formatted_date,
                    'is_admin': new_message['is_admin']
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