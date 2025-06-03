import os
import logging
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

def allowed_file(filename):
    """Prüft, ob die Dateiendung erlaubt ist"""
    ALLOWED_EXTENSIONS = {'docx', 'pdf', 'doc'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_user_directories(username):
    """Erstellt die notwendigen Verzeichnisse für einen Benutzer"""
    try:
        # Basis-Upload-Verzeichnis
        base_path = os.path.join('app', 'uploads', 'users')
        os.makedirs(base_path, exist_ok=True)
        
        # Benutzer-spezifisches Verzeichnis
        user_path = os.path.join(base_path, username)
        os.makedirs(user_path, exist_ok=True)
        
        # Unterverzeichnisse
        directories = [
            os.path.join(user_path, 'templates'),
            os.path.join(user_path, 'documents', 'cv'),
            os.path.join(user_path, 'documents', 'certificates'),
            os.path.join(user_path, 'applications')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Verzeichnis erstellt/überprüft: {directory}")
            
        return user_path
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Verzeichnisse: {str(e)}")
        raise 