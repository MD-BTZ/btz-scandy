from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.db_schema import SchemaManager
from app.config import config
from werkzeug.security import generate_password_hash
from app.models.database import Database
import logging

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('setup', __name__)

@bp.route('/setup/admin', methods=['GET', 'POST'])
def setup_admin():
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if not username or len(username) < 3:
            return render_template('setup_admin.html', error='Der Benutzername muss mindestens 3 Zeichen lang sein.')
        if len(username) > 50:
            return render_template('setup_admin.html', error='Der Benutzername darf maximal 50 Zeichen lang sein.')
        if len(password) < 8:
            return render_template('setup_admin.html', error='Das Passwort muss mindestens 8 Zeichen lang sein.')
        if password != password_confirm:
            return render_template('setup_admin.html', error='Die Passwörter stimmen nicht überein.')
        # Erstelle den Admin-Benutzer
        success, message = create_admin_user(username, password)
        if success:
            return redirect(url_for('setup.setup_settings'))
        else:
            return render_template('setup_admin.html', error=message)
                
    return render_template('setup_admin.html')

@bp.route('/setup/settings', methods=['GET', 'POST'])
def setup_settings():
    if request.method == 'POST':
        label_tools_name = request.form.get('label_tools_name', '').strip() or 'Werkzeuge'
        label_tools_icon = request.form.get('label_tools_icon', '').strip() or 'fas fa-tools'
        label_consumables_name = request.form.get('label_consumables_name', '').strip() or 'Material'
        label_consumables_icon = request.form.get('label_consumables_icon', '').strip() or 'fas fa-box-open'
        
        print("DEBUG: request.form:", dict(request.form))
        logger.info(f"[SETUP] Formulardaten: label_tools_name={label_tools_name}, label_tools_icon={label_tools_icon}, label_consumables_name={label_consumables_name}, label_consumables_icon={label_consumables_icon}")
        
        try:
            # Speichere die Einstellungen exakt wie im Dashboard/System-Menü
            Database.query('''INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', ['label_tools_name', label_tools_name])
            Database.query('''INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', ['label_tools_icon', label_tools_icon])
            Database.query('''INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', ['label_consumables_name', label_consumables_name])
            Database.query('''INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', ['label_consumables_icon', label_consumables_icon])
            return redirect(url_for('setup.setup_optional'))
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Grundeinstellungen: {e}")
            return render_template('setup_settings.html', error='Fehler beim Speichern der Einstellungen',
                label_tools_name=label_tools_name,
                label_tools_icon=label_tools_icon,
                label_consumables_name=label_consumables_name,
                label_consumables_icon=label_consumables_icon)
                
    return render_template('setup_settings.html')

@bp.route('/setup/optional', methods=['GET', 'POST'])
def setup_optional():
    if request.method == 'POST':
        categories = request.form.getlist('categories[]')
        locations = request.form.getlist('locations[]')
        departments = request.form.getlist('departments[]')
        
        try:
            # Speichere die optionalen Einstellungen
            with Database.get_db() as conn:
                cursor = conn.cursor()
                # Kategorien
                for i, category in enumerate(categories):
                    if category.strip():
                        cursor.execute('''
                            INSERT OR REPLACE INTO settings (key, value, description)
                            VALUES (?, ?, ?)
                        ''', (f'category_{i+1}', category.strip(), 'Kategorie'))
                # Standorte
                for i, location in enumerate(locations):
                    if location.strip():
                        cursor.execute('''
                            INSERT OR REPLACE INTO settings (key, value, description)
                            VALUES (?, ?, ?)
                        ''', (f'location_{i+1}', location.strip(), 'Standort'))
                # Abteilungen
                for i, department in enumerate(departments):
                    if department.strip():
                        cursor.execute('''
                            INSERT OR REPLACE INTO settings (key, value, description)
                            VALUES (?, ?, ?)
                        ''', (f'department_{i+1}', department.strip(), 'Abteilung'))
                conn.commit()
            
            flash('Einrichtung erfolgreich abgeschlossen!', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error(f"Fehler beim Speichern der optionalen Einstellungen: {e}")
            return render_template('setup_optional.html', error='Fehler beim Speichern der Einstellungen')
    
    return render_template('setup_optional.html')

def create_admin_user(username, password):
    """Erstellt den Admin-Benutzer mit frei wählbarem Namen"""
    try:
        with Database.get_db() as conn:
            cursor = conn.cursor()
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?)
            ''', [username, password_hash, 'admin'])
            conn.commit()
        return True, 'Admin-Benutzer erfolgreich erstellt.'
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Admin-Benutzers: {e}")
        return False, f'Fehler beim Erstellen des Admin-Benutzers: {str(e)}' 