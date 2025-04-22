from flask import Blueprint, send_file, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from ..database import Database
import shutil
import logging

bp = Blueprint('backup', __name__, url_prefix='/backup')

# Logging einrichten
logger = logging.getLogger(__name__)

@bp.route('/download/db')
def download_database():
    """Lädt die aktuelle Datenbank herunter"""
    try:
        db_path = current_app.config['DATABASE']
        return send_file(
            db_path,
            as_attachment=True,
            download_name=f'scandy_db_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        )
    except Exception as e:
        logger.error(f"Fehler beim Download der Datenbank: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/download/backup/<filename>')
def download_backup(filename):
    """Lädt ein bestimmtes Backup herunter"""
    try:
        backup_path = os.path.join(current_app.config['BACKUP_DIR'], secure_filename(filename))
        if not os.path.exists(backup_path):
            return jsonify({'status': 'error', 'message': 'Backup nicht gefunden'}), 404
        return send_file(backup_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Fehler beim Download des Backups: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/upload', methods=['POST'])
def upload_backup():
    """Lädt ein Backup hoch und aktiviert es"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Keine Datei ausgewählt'}), 400
    
    if not file.filename.endswith('.db'):
        return jsonify({'status': 'error', 'message': 'Nur .db Dateien erlaubt'}), 400
    
    try:
        # Sicheren Dateinamen erstellen
        filename = secure_filename(f'scandy_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        upload_path = os.path.join(current_app.config['BACKUP_DIR'], filename)
        
        # Datei speichern
        file.save(upload_path)
        
        # Datenbank-Verbindung schließen
        db = Database()
        db.close()
        
        # Backup der aktuellen DB erstellen
        current_db = current_app.config['DATABASE']
        backup_name = f'scandy_backup_before_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        backup_path = os.path.join(current_app.config['BACKUP_DIR'], backup_name)
        shutil.copy2(current_db, backup_path)
        
        # Neue DB aktivieren
        shutil.copy2(upload_path, current_db)
        
        return jsonify({
            'status': 'success',
            'message': 'Backup erfolgreich aktiviert',
            'backup_name': backup_name
        })
    except Exception as e:
        logger.error(f"Fehler beim Hochladen des Backups: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/list')
def list_backups():
    """Listet alle verfügbaren Backups auf"""
    try:
        backup_dir = current_app.config['BACKUP_DIR']
        backups = []
        for filename in os.listdir(backup_dir):
            if filename.endswith('.db'):
                path = os.path.join(backup_dir, filename)
                backups.append({
                    'name': filename,
                    'size': os.path.getsize(path),
                    'created': datetime.fromtimestamp(os.path.getctime(path)).isoformat()
                })
        return jsonify({'status': 'success', 'backups': backups})
    except Exception as e:
        logger.error(f"Fehler beim Auflisten der Backups: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500 