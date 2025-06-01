from flask import render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from app.models.applications import ApplicationTemplate, ApplicationDocumentTemplate
import shutil

db = SQLAlchemy()

def get_user_document_path(username):
    """Gibt den Pfad für die Dokumente eines Benutzers zurück"""
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents', username)

def delete_user_documents(username):
    """Löscht alle Dokumente eines Benutzers"""
    user_path = get_user_document_path(username)
    if os.path.exists(user_path):
        shutil.rmtree(user_path)

@bp.route('/placeholders')
@login_required
def placeholders():
    """Zeigt die Dokumentation der verfügbaren Platzhalter an."""
    return render_template('applications/placeholders.html')

@bp.route('/templates/create', methods=['GET', 'POST'])
@login_required
def create_template():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        template_content = request.form.get('template_content')
        
        # Verarbeite hochgeladene Dokumente
        cv = request.files.get('cv')
        certificates = request.files.getlist('certificates')
        
        # Speichere die Vorlage
        template = ApplicationTemplate(
            name=name,
            category=category,
            template_content=template_content,
            created_by=current_user.username,
            is_active=True
        )
        db.session.add(template)
        db.session.flush()  # Um die ID zu erhalten
        
        # Erstelle Benutzer-spezifischen Dokumentenpfad
        user_doc_path = get_user_document_path(current_user.username)
        
        # Speichere den Lebenslauf
        if cv and cv.filename:
            filename = secure_filename(cv.filename)
            file_path = os.path.join(user_doc_path, 'cv', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            cv.save(file_path)
            
            document = ApplicationDocumentTemplate(
                name=f"Lebenslauf für {name}",
                document_type='cv',
                file_name=filename,
                file_path=file_path,
                created_by=current_user.username,
                is_active=True
            )
            db.session.add(document)
        
        # Speichere die Zeugnisse
        for cert in certificates:
            if cert and cert.filename:
                filename = secure_filename(cert.filename)
                file_path = os.path.join(user_doc_path, 'certificates', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                cert.save(file_path)
                
                document = ApplicationDocumentTemplate(
                    name=f"Zeugnis für {name}",
                    document_type='certificate',
                    file_name=filename,
                    file_path=file_path,
                    created_by=current_user.username,
                    is_active=True
                )
                db.session.add(document)
        
        db.session.commit()
        flash('Vorlage wurde erfolgreich erstellt.', 'success')
        return redirect(url_for('applications.templates'))
        
    return render_template('applications/create_template.html') 