from flask import Blueprint, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.utils.decorators import mitarbeiter_required
from app.utils.logger import loggers
import os
# Temporärer Import-Fix
try:
    from app.utils.media_manager import MediaManager
except ImportError as e:
    print(f"MediaManager Import-Fehler: {e}")
    # Fallback: Einfache Implementierung
    class MediaManager:
        @staticmethod
        def upload_media(file, entity_type, entity_id):
            return None, "MediaManager nicht verfügbar"
        
        @staticmethod
        def delete_media(filename, entity_type, entity_id):
            return False
        
        @staticmethod
        def get_media_list(entity_type, entity_id):
            return []
        
        @staticmethod
        def get_media_count(entity_type, entity_id):
            return 0
from app.models.mongodb_database import get_mongodb
from bson import ObjectId

bp = Blueprint('media', __name__)

@bp.route('/<entity_type>/<entity_id>/upload', methods=['POST'])
@login_required
def upload_media(entity_type, entity_id):
    """Universeller Medien-Upload für alle Entitäten"""
    # Imports am Anfang
    from werkzeug.utils import secure_filename
    import uuid
    import os
    
    try:
        loggers['user_actions'].info(f"=== UPLOAD START === entity_type={entity_type}, entity_id={entity_id}")
        loggers['user_actions'].info(f"Request-Methode: {request.method}")
        loggers['user_actions'].info(f"Request-Files: {list(request.files.keys())}")
        loggers['user_actions'].info(f"Request-Form: {list(request.form.keys())}")
        
        # Validierung
        allowed_entities = ['jobs', 'tools', 'consumables', 'tickets']
        if entity_type not in allowed_entities:
            loggers['errors'].error(f"Ungültiger Entitätstyp: {entity_type}")
            return jsonify({'success': False, 'error': 'Ungültiger Entitätstyp'})
        
        # Berechtigungsprüfung
        if entity_type == 'tickets':
            # Für Tickets: Benutzer können Medien zu ihren eigenen Tickets hochladen
            from app.models.mongodb_database import mongodb
            ticket = mongodb.find_one('tickets', {'_id': entity_id})
            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket nicht gefunden'})
            
            # Prüfe ob Benutzer das Ticket erstellt hat oder Admin/Mitarbeiter ist
            if (current_user.role not in ['admin', 'mitarbeiter'] and 
                ticket.get('created_by') != current_user.username):
                return jsonify({'success': False, 'error': 'Keine Berechtigung für dieses Ticket'})
        else:
            # Für andere Entitäten: Nur Mitarbeiter und Admins
            if current_user.role not in ['admin', 'mitarbeiter']:
                return jsonify({'success': False, 'error': 'Keine Berechtigung'})
        
        # Datei prüfen
        file = None
        if 'file' in request.files:
            file = request.files['file']
            loggers['user_actions'].info("Datei unter 'file' gefunden")
        elif 'media' in request.files:
            file = request.files['media']
            loggers['user_actions'].info("Datei unter 'media' gefunden")
        else:
            loggers['errors'].error("Keine Datei in request.files gefunden")
            loggers['errors'].error(f"Verfügbare Keys: {list(request.files.keys())}")
            return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'})
        
        loggers['user_actions'].info(f"Datei gefunden: {file.filename}")
        loggers['user_actions'].info(f"Datei-Objekt: {type(file)}")
        loggers['user_actions'].info(f"Datei-Attribute: {dir(file)}")
        
        if file.filename == '':
            loggers['errors'].error("Datei hat leeren Namen")
            return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'})
        
        # Debug-Informationen
        loggers['user_actions'].info(f"Upload-Versuch: entity_type={entity_type}, entity_id={entity_id}")
        loggers['user_actions'].info(f"Datei: {file.filename}, Größe: {file.content_length if hasattr(file, 'content_length') else 'unbekannt'}")
        
        # Medien direkt hochladen (ohne MediaManager)
        loggers['user_actions'].info("Lade Datei direkt hoch...")
        
        # Sicheren Dateinamen erstellen
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        # Ordner erstellen
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', entity_type, str(entity_id))
        os.makedirs(upload_folder, exist_ok=True)
        
        # Aktuelle Anzahl prüfen
        current_count = len([f for f in os.listdir(upload_folder) if os.path.isfile(os.path.join(upload_folder, f))])
        max_files = 10
        
        loggers['user_actions'].info(f"Aktuelle Dateien: {current_count}, Maximum: {max_files}")
        
        if current_count >= max_files:
            loggers['errors'].error(f"Maximale Anzahl von {max_files} Dateien erreicht")
            return jsonify({'success': False, 'error': f'Maximale Anzahl von {max_files} Dateien erreicht'})
        
        # Datei speichern
        file_path = os.path.join(upload_folder, unique_filename)
        loggers['user_actions'].info(f"Speichere Datei: {file_path}")
        
        file.save(file_path)
        
        # Bild auf 1080p skalieren falls nötig
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                # Prüfen ob Bild größer als 1080p ist
                max_size = 1080
                if img.width > max_size or img.height > max_size:
                    # Seitenverhältnis beibehalten
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    img.save(file_path, quality=95, optimize=True)
                    loggers['user_actions'].info(f"Bild auf {img.width}x{img.height} skaliert")
                else:
                    loggers['user_actions'].info(f"Bild behält Originalgröße: {img.width}x{img.height}")
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Skalieren: {e}")
            # Datei trotzdem behalten, auch wenn Skalierung fehlschlägt
        
        loggers['user_actions'].info(f"Datei gespeichert: {os.path.exists(file_path)}")
        loggers['user_actions'].info(f"Dateigröße: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'} bytes")
        
        loggers['user_actions'].info("=== UPLOAD ENDE ===")
        return jsonify({
            'success': True,
            'message': 'Medien erfolgreich hochgeladen!',
            'filename': unique_filename
        })
        
    except Exception as e:
        loggers['errors'].error(f"Upload-Fehler: {e}")
        import traceback
        loggers['errors'].error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Fehler beim Hochladen: {str(e)}'})

@bp.route('/<entity_type>/<entity_id>/delete/<filename>', methods=['POST'])
@login_required
def delete_media(entity_type, entity_id, filename):
    """Löscht eine Mediendatei"""
    try:
        loggers['user_actions'].info(f"=== DELETE START === entity_type={entity_type}, entity_id={entity_id}, filename={filename}")
        
        # Validierung
        allowed_entities = ['jobs', 'tools', 'consumables', 'tickets']
        if entity_type not in allowed_entities:
            return jsonify({'success': False, 'error': 'Ungültiger Entitätstyp'})
        
        # Berechtigungsprüfung
        if entity_type == 'tickets':
            # Für Tickets: Benutzer können Medien von ihren eigenen Tickets löschen
            from app.models.mongodb_database import mongodb
            ticket = mongodb.find_one('tickets', {'_id': entity_id})
            if not ticket:
                return jsonify({'success': False, 'error': 'Ticket nicht gefunden'})
            
            # Prüfe ob Benutzer das Ticket erstellt hat oder Admin/Mitarbeiter ist
            if (current_user.role not in ['admin', 'mitarbeiter'] and 
                ticket.get('created_by') != current_user.username):
                return jsonify({'success': False, 'error': 'Keine Berechtigung für dieses Ticket'})
        else:
            # Für andere Entitäten: Nur Mitarbeiter und Admins
            if current_user.role not in ['admin', 'mitarbeiter']:
                return jsonify({'success': False, 'error': 'Keine Berechtigung'})
        
        # Datei löschen
        file_path = os.path.join(current_app.root_path, 'static', 'uploads', entity_type, str(entity_id), filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            loggers['user_actions'].info(f"Datei gelöscht: {file_path}")
            return jsonify({'success': True, 'message': 'Medium erfolgreich gelöscht!'})
        else:
            loggers['errors'].error(f"Datei nicht gefunden: {file_path}")
            return jsonify({'success': False, 'error': 'Datei nicht gefunden'})
            
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Löschen: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<entity_type>/<entity_id>/list')
def get_media_list(entity_type, entity_id):
    """Listet alle Medien für eine Entität auf"""
    try:
        loggers['user_actions'].info(f"=== LIST START === entity_type={entity_type}, entity_id={entity_id}")
        
        # Validierung
        allowed_entities = ['jobs', 'tools', 'consumables', 'tickets']
        if entity_type not in allowed_entities:
            return jsonify({'success': False, 'error': 'Ungültiger Entitätstyp'})
        
        # Ordner-Pfad
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', entity_type, str(entity_id))
        loggers['user_actions'].info(f"Suche Medien in: {upload_folder}")
        
        # Prüfe ob Ordner existiert
        if not os.path.exists(upload_folder):
            loggers['user_actions'].info(f"Ordner existiert: {os.path.exists(upload_folder)}")
            os.makedirs(upload_folder, exist_ok=True)
            loggers['user_actions'].info(f"Ordner erstellt: {os.path.exists(upload_folder)}")
        
        # Alle Dateien im Ordner
        all_files = os.listdir(upload_folder)
        loggers['user_actions'].info(f"Alle Dateien im Ordner: {all_files}")
        
        # Medien-Liste erstellen
        media_list = []
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'pdf'}
        
        for filename in all_files:
            file_path = os.path.join(upload_folder, filename)
            if os.path.isfile(file_path):
                # Dateiendung prüfen
                file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                is_allowed = file_ext in allowed_extensions
                
                loggers['user_actions'].info(f"Datei übersprungen: {filename} (ist_datei={os.path.isfile(file_path)}, erlaubt={is_allowed})")
                
                if is_allowed:
                    # Relative URL für Frontend
                    relative_url = f"/static/uploads/{entity_type}/{entity_id}/{filename}"
                    media_list.append({
                        'filename': filename,
                        'url': relative_url,
                        'size': os.path.getsize(file_path)
                    })
        
        loggers['user_actions'].info(f"Medien-Liste: {media_list}")
        
        return jsonify({
            'success': True,
            'media_list': media_list,
            'count': len(media_list)
        })
        
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Laden der Medien: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<entity_type>/<entity_id>/count')
def get_media_count(entity_type, entity_id):
    """Anzahl der Medien einer Entität"""
    try:
        count = MediaManager.get_media_count(entity_type, entity_id)
        return jsonify({
            'success': True,
            'count': count,
            'max_count': MediaManager.MAX_IMAGES_PER_ENTITY
        })
        
    except Exception as e:
        loggers['errors'].error(f"Count-Fehler: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0
        })

@bp.route('/test-upload/<entity_type>/<entity_id>')
def test_upload_route(entity_type, entity_id):
    """Test-Route für Upload-Debugging"""
    try:
        loggers['user_actions'].info(f"Test-Upload-Route aufgerufen: {entity_type}/{entity_id}")
        return jsonify({
            'success': True,
            'message': f'Upload-Route erreichbar für {entity_type}/{entity_id}',
            'entity_type': entity_type,
            'entity_id': entity_id
        })
    except Exception as e:
        loggers['errors'].error(f"Test-Upload-Fehler: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@bp.route('/simple-upload/<entity_type>/<entity_id>', methods=['GET', 'POST'])
def simple_upload_test(entity_type, entity_id):
    """Einfache Upload-Test-Seite"""
    if request.method == 'POST':
        loggers['user_actions'].info(f"Simple Upload POST: {entity_type}/{entity_id}")
        loggers['user_actions'].info(f"Files: {list(request.files.keys())}")
        loggers['user_actions'].info(f"Form: {list(request.form.keys())}")
        
        if 'media' in request.files:
            file = request.files['media']
            loggers['user_actions'].info(f"Datei gefunden: {file.filename}")
            
            # Datei speichern
            from werkzeug.utils import secure_filename
            import uuid
            import os
            
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            
            # Ordner erstellen
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', entity_type, str(entity_id))
            os.makedirs(upload_folder, exist_ok=True)
            
            # Datei speichern
            file_path = os.path.join(upload_folder, unique_filename)
            loggers['user_actions'].info(f"Speichere Datei: {file_path}")
            
            file.save(file_path)
            
            loggers['user_actions'].info(f"Datei gespeichert: {os.path.exists(file_path)}")
            loggers['user_actions'].info(f"Dateigröße: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'} bytes")
            
            flash('Datei erfolgreich gespeichert!', 'success')
        else:
            loggers['user_actions'].info("Keine Datei gefunden")
            flash('Keine Datei gefunden', 'error')
        
        return redirect(url_for('media.simple_upload_test', entity_type=entity_type, entity_id=entity_id))
    
    return f'''
    <html>
    <head><title>Upload Test</title></head>
    <body>
        <h1>Upload Test für {entity_type}/{entity_id}</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="media" accept="image/*,.svg,image/svg+xml,.pdf,application/pdf">
            <button type="submit">Upload</button>
        </form>
        <a href="/jobs/{entity_id}/edit">Zurück zur Bearbeitung</a>
    </body>
    </html>
    '''

@bp.route('/<entity_type>/<entity_id>/set_preview/<filename>', methods=['POST'])
@login_required
@mitarbeiter_required
def set_preview_image(entity_type, entity_id, filename):
    """Preview-Bild für eine Entität setzen"""
    import os
    from bson import ObjectId
    
    try:
        loggers['user_actions'].info(f"=== SET PREVIEW START === entity_type={entity_type}, entity_id={entity_id}, filename={filename}")
        
        # Validierung
        allowed_entities = ['jobs', 'tools', 'consumables']
        if entity_type not in allowed_entities:
            loggers['errors'].error(f"Ungültiger Entitätstyp: {entity_type}")
            return jsonify({'success': False, 'error': 'Ungültiger Entitätstyp'})
        
        # Medien-Ordner prüfen
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', entity_type, str(entity_id))
        
        if not os.path.exists(upload_folder):
            loggers['errors'].error(f"Medien-Ordner existiert nicht: {upload_folder}")
            return jsonify({'success': False, 'error': 'Medien-Ordner existiert nicht'})
        
        # Datei prüfen
        file_path = os.path.join(upload_folder, filename)
        if not os.path.exists(file_path):
            loggers['errors'].error(f"Datei existiert nicht: {file_path}")
            return jsonify({'success': False, 'error': 'Datei existiert nicht'})
        
        # Preview-Bild in Datenbank speichern
        db = get_mongodb()
        
        # Entität finden und Preview-Bild setzen
        if entity_type == 'tools':
            result = db.update_one(
                'tools',
                {'barcode': entity_id},
                {'$set': {'preview_image': filename}}
            )
        elif entity_type == 'jobs':
            result = db.update_one(
                'jobs',
                {'_id': ObjectId(entity_id)},
                {'$set': {'preview_image': filename}}
            )
        elif entity_type == 'consumables':
            result = db.update_one(
                'consumables',
                {'barcode': entity_id},
                {'$set': {'preview_image': filename}}
            )
        else:
            return jsonify({'success': False, 'error': 'Unbekannter Entitätstyp'})
        
        if result:
            loggers['user_actions'].info(f"Preview-Bild erfolgreich gesetzt: {filename}")
            return jsonify({'success': True, 'message': 'Preview-Bild erfolgreich gesetzt'})
        else:
            loggers['errors'].error(f"Entität nicht gefunden: {entity_id}")
            return jsonify({'success': False, 'error': 'Entität nicht gefunden'})
        
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Setzen des Preview-Bildes: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}) 