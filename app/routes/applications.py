from flask import Blueprint, render_template, request, jsonify, current_app, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from app.models.database import Database
from app.utils.auth_utils import admin_required
from app.models.ticket_db import TicketDatabase
from flask_sqlalchemy import SQLAlchemy
from app.models.applications import Bewerbungsvorlage, Bewerbungsdokument
import shutil

bp = Blueprint('applications', __name__, url_prefix='/applications')

db = SQLAlchemy()

logger = logging.getLogger(__name__)

def allowed_file(filename):
    """Überprüft, ob die Datei einen erlaubten Dateityp hat"""
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_user_document_path(username):
    """Gibt den Pfad für die Dokumente eines Benutzers zurück"""
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents', username)

def delete_user_documents(username):
    """Löscht alle Dokumente eines Benutzers."""
    try:
        # Hole alle Dokumente des Benutzers
        documents = Database.query("""
            SELECT * FROM bewerbungsdokumente_uploads
            WHERE bewerbung_id IN (
                SELECT id FROM bewerbungen WHERE erstellt_von = ?
            )
        """, [username])
        
        # Lösche Dateien
        for doc in documents:
            if os.path.exists(doc['dateipfad']):
                os.remove(doc['dateipfad'])
                
        # Lösche Datenbankeinträge
        Database.query("""
            DELETE FROM bewerbungsdokumente_uploads
            WHERE bewerbung_id IN (
                SELECT id FROM bewerbungen WHERE erstellt_von = ?
            )
        """, [username])
        
        return True
    except Exception as e:
        logging.error(f"Fehler beim Löschen der Benutzerdokumente: {str(e)}")
        return False

@bp.route('/')
@login_required
def index():
    """Zeigt die Bewerbungsübersicht für den eingeloggten Benutzer an."""
    try:
        # Hole alle Vorlagen
        templates = Database.query("SELECT * FROM bewerbungsvorlagen WHERE ist_aktiv = 1")
        
        # Hole alle Bewerbungen des Benutzers
        applications = Database.query("""
            SELECT b.*, v.name as vorlagen_name 
            FROM bewerbungen b
            JOIN bewerbungsvorlagen v ON b.vorlagen_id = v.id
            WHERE b.erstellt_von = ?
            ORDER BY b.erstellt_am DESC
        """, [current_user.username])
        
        # Hole alle Dokumente des Benutzers
        documents = Database.query("""
            SELECT * FROM bewerbungsdokumente_uploads
            WHERE bewerbung_id IN (
                SELECT id FROM bewerbungen WHERE erstellt_von = ?
            )
        """, [current_user.username])
        
        return render_template('tickets/applications.html', 
                             templates=templates,
                             applications=applications,
                             documents=documents)
    except Exception as e:
        logging.error(f"Fehler beim Laden der Bewerbungsseite: {str(e)}")
        flash('Fehler beim Laden der Bewerbungsseite', 'error')
        return redirect(url_for('main.index'))

@bp.route('/templates/<int:template_id>')
@login_required
def view_template(template_id):
    """Zeigt Details einer Bewerbungsvorlage"""
    template = Bewerbungsvorlage.get_by_id(template_id)
    if not template:
        return jsonify({'error': 'Vorlage nicht gefunden'}), 404
    
    documents = Bewerbungsdokument.get_by_vorlagen_id(template_id)
    return render_template('applications/template.html', template=template, documents=documents)

@bp.route('/templates/create', methods=['GET', 'POST'])
@admin_required
def create_template():
    """Erstellt eine neue Bewerbungsvorlage"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            return jsonify({'error': 'Name ist erforderlich'}), 400
            
        template_id = Bewerbungsvorlage.create(name, description)
        return jsonify({'success': True, 'template_id': template_id})
        
    return render_template('applications/create_template.html')

@bp.route('/templates/<int:template_id>/documents', methods=['POST'])
@admin_required
def add_document(template_id):
    """Fügt ein Dokument zur Vorlage hinzu"""
    if not request.files.get('document'):
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400
        
    file = request.files['document']
    name = request.form.get('name')
    description = request.form.get('description')
    is_required = request.form.get('is_required', 'true').lower() == 'true'
    
    if not name:
        return jsonify({'error': 'Name ist erforderlich'}), 400
        
    # Speichere die Datei
    filename = f"{template_id}_{file.filename}"
    file_path = current_app.config['UPLOAD_FOLDER'] / 'templates' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file.save(str(file_path))
    
    # Erstelle den Dokumenteneintrag
    doc_id = Bewerbungsdokument.create(
        vorlagen_id=template_id,
        name=name,
        description=description,
        file_path=str(file_path),
        is_required=is_required
    )
    
    return jsonify({'success': True, 'document_id': doc_id})

@bp.route('/placeholders')
@login_required
def placeholders():
    """Zeigt die Dokumentation der verfügbaren Platzhalter an."""
    return render_template('applications/placeholders.html')

@bp.route('/document/upload', methods=['POST'])
@login_required
def upload_document():
    """Lädt ein persönliches Dokument hoch und speichert es in der Tabelle 'benutzerdokumente'."""
    try:
        if 'document' not in request.files:
            return jsonify({'success': False, 'message': 'Keine Datei ausgewählt'})
        file = request.files['document']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Keine Datei ausgewählt'})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            document_type = request.form.get('document_type', 'sonstiges')
            # Erstelle Verzeichnis für Benutzer, falls nicht vorhanden
            user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], current_user.username)
            os.makedirs(user_dir, exist_ok=True)
            # Speichere Datei
            file_path = os.path.join(user_dir, filename)
            file.save(file_path)
            # Speichere Metadaten in der neuen Tabelle benutzerdokumente
            Database.query(
                """
                INSERT INTO benutzerdokumente (benutzername, dokumenttyp, dateiname, dateipfad, hochgeladen_am)
                VALUES (?, ?, ?, ?, ?)
                """,
                [current_user.username, document_type, filename, file_path, datetime.now()]
            )
            return jsonify({'success': True, 'message': 'Dokument erfolgreich hochgeladen'})
        else:
            return jsonify({'success': False, 'message': 'Ungültiger Dateityp'})
    except Exception as e:
        logging.error(f"Fehler beim Hochladen des Dokuments: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/document/<int:id>/download')
@login_required
def download_document(id):
    """Lädt ein Dokument herunter."""
    try:
        document = Database.query("""
            SELECT * FROM bewerbungsdokumente_uploads
            WHERE id = ? AND bewerbung_id IN (
                SELECT id FROM bewerbungen WHERE erstellt_von = ?
            )
        """, [id, current_user.username], one=True)
        
        if not document:
            flash('Dokument nicht gefunden', 'error')
            return redirect(url_for('applications.index'))
            
        return send_file(document['dateipfad'], as_attachment=True)
        
    except Exception as e:
        logging.error(f"Fehler beim Herunterladen des Dokuments: {str(e)}")
        flash('Fehler beim Herunterladen des Dokuments', 'error')
        return redirect(url_for('applications.index'))

@bp.route('/document/<int:id>/delete', methods=['POST'])
@login_required
def delete_document(id):
    """Löscht ein Dokument."""
    try:
        document = Database.query("""
            SELECT * FROM bewerbungsdokumente_uploads
            WHERE id = ? AND bewerbung_id IN (
                SELECT id FROM bewerbungen WHERE erstellt_von = ?
            )
        """, [id, current_user.username], one=True)
        
        if not document:
            return jsonify({'success': False, 'message': 'Dokument nicht gefunden'})
            
        # Lösche Datei
        if os.path.exists(document['dateipfad']):
            os.remove(document['dateipfad'])
            
        # Lösche Datenbankeintrag
        Database.query("DELETE FROM bewerbungsdokumente_uploads WHERE id = ?", [id])
        
        return jsonify({'success': True, 'message': 'Dokument erfolgreich gelöscht'})
        
    except Exception as e:
        logging.error(f"Fehler beim Löschen des Dokuments: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/create', methods=['POST'])
@login_required
def create_application():
    """Erstellt eine neue Bewerbung."""
    try:
        template_id = request.form.get('template_id')
        firmenname = request.form.get('firmenname')
        position = request.form.get('position')
        
        if not all([template_id, firmenname, position]):
            return jsonify({'success': False, 'message': 'Bitte füllen Sie alle Pflichtfelder aus'})
            
        # Erstelle Bewerbung
        Database.query("""
            INSERT INTO bewerbungen 
            (vorlagen_id, bewerber, firmenname, position, ansprechpartner, anrede, 
             email, telefon, adresse, eigener_text, status, erstellt_von, erstellt_am)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            template_id, current_user.username, firmenname, position,
            request.form.get('ansprechpartner'), request.form.get('anrede'),
            request.form.get('email'), request.form.get('telefon'),
            request.form.get('adresse'), request.form.get('eigener_text'),
            'in_bearbeitung', current_user.username, datetime.now()
        ])
        
        return jsonify({'success': True, 'message': 'Bewerbung erfolgreich erstellt'})
        
    except Exception as e:
        logging.error(f"Fehler beim Erstellen der Bewerbung: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_application(id):
    """Löscht eine Bewerbung."""
    try:
        application = Database.query("""
            SELECT * FROM bewerbungen
            WHERE id = ? AND erstellt_von = ?
        """, [id, current_user.username], one=True)
        
        if not application:
            return jsonify({'success': False, 'message': 'Bewerbung nicht gefunden'})
            
        # Lösche zugehörige Dokumente
        documents = Database.query("""
            SELECT * FROM bewerbungsdokumente_uploads
            WHERE bewerbung_id = ?
        """, [id])
        
        for doc in documents:
            if os.path.exists(doc['dateipfad']):
                os.remove(doc['dateipfad'])
                
        Database.query("DELETE FROM bewerbungsdokumente_uploads WHERE bewerbung_id = ?", [id])
        
        # Lösche Bewerbung
        Database.query("DELETE FROM bewerbungen WHERE id = ?", [id])
        
        return jsonify({'success': True, 'message': 'Bewerbung erfolgreich gelöscht'})
        
    except Exception as e:
        logging.error(f"Fehler beim Löschen der Bewerbung: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/<int:id>/details')
@login_required
def application_details(id):
    """Zeigt die Details einer Bewerbung an."""
    try:
        application = Database.query("""
            SELECT b.*, v.name as vorlagen_name
            FROM bewerbungen b
            JOIN bewerbungsvorlagen v ON b.vorlagen_id = v.id
            WHERE b.id = ? AND b.erstellt_von = ?
        """, [id, current_user.username], one=True)
        
        if not application:
            flash('Bewerbung nicht gefunden', 'error')
            return redirect(url_for('applications.index'))
            
        documents = Database.query("""
            SELECT * FROM bewerbungsdokumente_uploads
            WHERE bewerbung_id = ?
        """, [id])
        
        return render_template('tickets/application_details.html',
                             application=application,
                             documents=documents)
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Bewerbungsdetails: {str(e)}")
        flash('Fehler beim Laden der Bewerbungsdetails', 'error')
        return redirect(url_for('applications.index'))

@bp.route('/<int:id>/download')
@login_required
def download_application(id):
    """Lädt eine Bewerbung als PDF herunter."""
    try:
        application = Database.query("""
            SELECT * FROM bewerbungen
            WHERE id = ? AND erstellt_von = ?
        """, [id, current_user.username], one=True)
        
        if not application:
            flash('Bewerbung nicht gefunden', 'error')
            return redirect(url_for('applications.index'))
            
        # TODO: PDF-Generierung implementieren
        flash('PDF-Generierung noch nicht implementiert', 'warning')
        return redirect(url_for('applications.application_details', id=id))
        
    except Exception as e:
        logging.error(f"Fehler beim Herunterladen der Bewerbung: {str(e)}")
        flash('Fehler beim Herunterladen der Bewerbung', 'error')
        return redirect(url_for('applications.index')) 