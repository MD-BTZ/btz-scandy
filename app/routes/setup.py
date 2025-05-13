from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.utils.db_schema import SchemaManager
from app.config import config
from werkzeug.security import generate_password_hash
from app.models.database import Database
import logging

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('setup', __name__)

@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    current_config = config['default']()
    db_path = current_config.DATABASE
    schema_manager = SchemaManager(db_path)
    
    # Prüfe ob bereits ein Admin-Benutzer existiert
    with schema_manager._get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        if user_count > 0:
            return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if len(password) < 8:
            return render_template('setup.html', error='Das Passwort muss mindestens 8 Zeichen lang sein.')
        
        if password != confirm_password:
            return render_template('setup.html', error='Die Passwörter stimmen nicht überein.')
        
        # Erstelle den Admin-Benutzer
        success, message = create_admin_user(password)
        if success:
            flash(message, 'success')
            return redirect(url_for('auth.login'))
        else:
            return render_template('setup.html', error=message)
    
    return render_template('setup.html')

def create_admin_user(password):
    """Erstellt einen Admin-Benutzer mit dem angegebenen Passwort."""
    try:
        with Database.get_db() as db:
            # Prüfen, ob bereits ein Admin existiert
            admin = db.execute('SELECT * FROM users WHERE role = ?', ['admin']).fetchone()
            if admin:
                return False, "Ein Admin-Benutzer existiert bereits."
            
            # Passwort hashen
            password_hash = generate_password_hash(password)
            
            # Admin-Benutzer erstellen
            db.execute('''
                INSERT INTO users (username, password_hash, role, is_active)
                VALUES (?, ?, ?, ?)
            ''', ['Admin', password_hash, 'admin', True])
            db.commit()
            
            return True, "Admin-Benutzer wurde erfolgreich erstellt."
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Admin-Benutzers: {e}")
        return False, f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}" 