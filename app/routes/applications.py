from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from app.models.applications import ApplicationTemplate, ApplicationDocumentTemplate
import shutil
from app.utils.auth_utils import admin_required

bp = Blueprint('applications', __name__, url_prefix='/applications')

db = SQLAlchemy()

def get_user_document_path(username):
    """Gibt den Pfad für die Dokumente eines Benutzers zurück"""
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents', username)

def delete_user_documents(username):
    """Löscht alle Dokumente eines Benutzers"""
    user_path = get_user_document_path(username)
    if os.path.exists(user_path):
        shutil.rmtree(user_path)

@bp.route('/')
@login_required
def index():
    """Zeigt die Übersicht der Bewerbungsvorlagen"""
    templates = ApplicationTemplate.get_all()
    return render_template('applications/index.html', templates=templates)

@bp.route('/templates/<int:template_id>')
@login_required
def view_template(template_id):
    """Zeigt Details einer Bewerbungsvorlage"""
    template = ApplicationTemplate.get_by_id(template_id)
    if not template:
        return jsonify({'error': 'Vorlage nicht gefunden'}), 404
    
    documents = ApplicationDocumentTemplate.get_by_template_id(template_id)
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
            
        template_id = ApplicationTemplate.create(name, description)
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
    doc_id = ApplicationDocumentTemplate.create(
        template_id=template_id,
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