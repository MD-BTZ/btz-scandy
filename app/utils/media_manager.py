import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from app.utils.logger import loggers
from PIL import Image
import io

class MediaManager:
    """Universelles Medien-Management-System"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_IMAGES_PER_ENTITY = 10
    MAX_IMAGE_SIZE = (1920, 1080)  # 1080p
    
    @staticmethod
    def allowed_file(filename):
        """Prüft ob Dateityp erlaubt ist"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in MediaManager.ALLOWED_EXTENSIONS
    
    @staticmethod
    def get_upload_folder(entity_type, entity_id):
        """Erstellt und gibt Upload-Ordner zurück"""
        upload_path = os.path.join(current_app.root_path, 'static', 'uploads', entity_type, str(entity_id))
        
        loggers['user_actions'].info(f"Erstelle Ordner: {upload_path}")
        loggers['user_actions'].info(f"Root-Pfad: {current_app.root_path}")
        
        os.makedirs(upload_path, exist_ok=True)
        
        loggers['user_actions'].info(f"Ordner erstellt: {os.path.exists(upload_path)}")
        loggers['user_actions'].info(f"Ordner-Inhalt: {os.listdir(upload_path) if os.path.exists(upload_path) else 'N/A'}")
        
        return upload_path
    
    @staticmethod
    def get_media_folder_path(entity_type, entity_id):
        """Gibt relativen Pfad für Frontend zurück"""
        return f"uploads/{entity_type}/{entity_id}"
    
    @staticmethod
    def resize_image(image_path, max_size=MAX_IMAGE_SIZE):
        """Skaliert Bild auf maximale Größe"""
        try:
            with Image.open(image_path) as img:
                # Konvertiere zu RGB falls nötig
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Skaliere nur wenn nötig
                if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    img.save(image_path, quality=85, optimize=True)
                    loggers['user_actions'].info(f"Bild skaliert: {image_path}")
                
                return True
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Skalieren: {e}")
            return False
    
    @staticmethod
    def upload_media(file, entity_type, entity_id):
        """Lädt Medien für eine Entität hoch"""
        try:
            # Validierung
            if not file or not MediaManager.allowed_file(file.filename):
                return None, "Ungültiges Dateiformat. Nur Bilder (jpg, png, gif, webp) erlaubt."
            
            # Aktuelle Anzahl prüfen
            current_count = MediaManager.get_media_count(entity_type, entity_id)
            if current_count >= MediaManager.MAX_IMAGES_PER_ENTITY:
                return None, f"Maximal {MediaManager.MAX_IMAGES_PER_ENTITY} Bilder erlaubt."
            
            # Sicheren Dateinamen erstellen
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            
            # Ordner erstellen und Datei speichern
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            file_path = os.path.join(upload_folder, unique_filename)
            
            loggers['user_actions'].info(f"Upload-Pfad: {file_path}")
            loggers['user_actions'].info(f"Ordner existiert: {os.path.exists(upload_folder)}")
            
            file.save(file_path)
            
            loggers['user_actions'].info(f"Datei gespeichert: {os.path.exists(file_path)}")
            loggers['user_actions'].info(f"Dateigröße: {os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A'} bytes")
            
            # Bild skalieren
            if not MediaManager.resize_image(file_path):
                os.remove(file_path)
                return None, "Fehler beim Verarbeiten des Bildes."
            
            loggers['user_actions'].info(f"Medien hochgeladen: {entity_type}/{entity_id}/{unique_filename}")
            return unique_filename, None
            
        except Exception as e:
            loggers['errors'].error(f"Upload-Fehler: {e}")
            return None, f"Fehler beim Hochladen: {str(e)}"
    
    @staticmethod
    def delete_media(filename, entity_type, entity_id):
        """Löscht eine Mediendatei"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            file_path = os.path.join(upload_folder, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                loggers['user_actions'].info(f"Medien gelöscht: {file_path}")
                return True
            else:
                loggers['warnings'].warning(f"Datei nicht gefunden: {file_path}")
                return False
                
        except Exception as e:
            loggers['errors'].error(f"Delete-Fehler: {e}")
            return False
    
    @staticmethod
    def delete_all_media(entity_type, entity_id):
        """Löscht alle Medien einer Entität"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            
            if os.path.exists(upload_folder):
                for filename in os.listdir(upload_folder):
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                
                # Ordner löschen
                os.rmdir(upload_folder)
                loggers['user_actions'].info(f"Alle Medien gelöscht: {entity_type}/{entity_id}")
                return True
            else:
                loggers['info'].info(f"Kein Medien-Ordner gefunden: {upload_folder}")
                return True
                
        except Exception as e:
            loggers['errors'].error(f"Delete-All-Fehler: {e}")
            return False
    
    @staticmethod
    def get_media_count(entity_type, entity_id):
        """Gibt Anzahl der Medien zurück"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            if os.path.exists(upload_folder):
                return len([f for f in os.listdir(upload_folder) 
                          if os.path.isfile(os.path.join(upload_folder, f))])
            return 0
        except Exception as e:
            loggers['errors'].error(f"Count-Fehler: {e}")
            return 0
    
    @staticmethod
    def get_media_list(entity_type, entity_id):
        """Gibt Liste aller Medien zurück"""
        try:
            upload_folder = MediaManager.get_upload_folder(entity_type, entity_id)
            media_list = []
            
            loggers['user_actions'].info(f"Suche Medien in: {upload_folder}")
            loggers['user_actions'].info(f"Ordner existiert: {os.path.exists(upload_folder)}")
            
            if os.path.exists(upload_folder):
                all_files = os.listdir(upload_folder)
                loggers['user_actions'].info(f"Alle Dateien im Ordner: {all_files}")
                
                for filename in all_files:
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.isfile(file_path) and MediaManager.allowed_file(filename):
                        media_list.append(filename)
                        loggers['user_actions'].info(f"Medien-Datei gefunden: {filename}")
                    else:
                        loggers['user_actions'].info(f"Datei übersprungen: {filename} (ist_datei={os.path.isfile(file_path)}, erlaubt={MediaManager.allowed_file(filename)})")
            
            loggers['user_actions'].info(f"Medien-Liste: {media_list}")
            return sorted(media_list)
        except Exception as e:
            loggers['errors'].error(f"List-Fehler: {e}")
            return [] 