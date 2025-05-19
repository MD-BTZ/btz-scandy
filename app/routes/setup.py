from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.db_schema import SchemaManager
from app.config import config
from werkzeug.security import generate_password_hash
from app.models.ticket_db import TicketDatabase
import logging
from app.models.database import Database

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('setup', __name__)

@bp.route('/setup/admin', methods=['GET', 'POST'])
def setup_admin():
    current_config = config['default']()
    db_path = current_config.DATABASE
    schema_manager = SchemaManager(db_path)
    
    # Prüfe ob bereits ein Admin-Benutzer existiert
    if is_admin_user_present():
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
        success, message = create_admin_user(username, password, 'admin')
        if success:
            return redirect(url_for('setup.setup_settings'))
        else:
            return render_template('setup_admin.html', error=message)
                
    return render_template('setup_admin.html')

@bp.route('/setup/settings', methods=['GET', 'POST'])
def setup_settings():
    if request.method == 'POST':
        label_tools_name = request.form.get('label_tools_name', '').strip()
        label_tools_icon = request.form.get('label_tools_icon', '').strip()
        label_consumables_name = request.form.get('label_consumables_name', '').strip()
        label_consumables_icon = request.form.get('label_consumables_icon', '').strip()
        
        logger.info(f"[SETUP] Formulardaten: label_tools_name={label_tools_name}, label_tools_icon={label_tools_icon}, label_consumables_name={label_consumables_name}, label_consumables_icon={label_consumables_icon}")
        
        try:
            ticket_db = TicketDatabase()
            
            # Lösche zuerst die alten Einträge
            ticket_db.query('DELETE FROM settings WHERE key IN (?, ?, ?, ?)', 
                          ['label_tools_name', 'label_tools_icon', 'label_consumables_name', 'label_consumables_icon'])
            
            # Füge die neuen Einträge ein
            ticket_db.query('''INSERT INTO settings (key, value, description) VALUES (?, ?, ?)''', 
                          ['label_tools_name', label_tools_name or 'Werkzeuge', 'Anzeigename für Werkzeuge'])
            ticket_db.query('''INSERT INTO settings (key, value, description) VALUES (?, ?, ?)''', 
                          ['label_tools_icon', label_tools_icon or 'fas fa-tools', 'Icon für Werkzeuge'])
            ticket_db.query('''INSERT INTO settings (key, value, description) VALUES (?, ?, ?)''', 
                          ['label_consumables_name', label_consumables_name or 'Verbrauchsmaterial', 'Anzeigename für Verbrauchsmaterial'])
            ticket_db.query('''INSERT INTO settings (key, value, description) VALUES (?, ?, ?)''', 
                          ['label_consumables_icon', label_consumables_icon or 'fas fa-box-open', 'Icon für Verbrauchsmaterial'])
            
            return redirect(url_for('setup.setup_optional'))
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Grundeinstellungen: {e}")
            return render_template('setup_settings.html', error='Fehler beim Speichern der Einstellungen',
                label_tools_name=label_tools_name,
                label_tools_icon=label_tools_icon,
                label_consumables_name=label_consumables_name,
                label_consumables_icon=label_consumables_icon)
    
    # Lade vorhandene Einstellungen für die Anzeige
    try:
        ticket_db = TicketDatabase()
        settings = {}
        
        # Hole alle relevanten Einstellungen
        results = ticket_db.query('''
            SELECT key, value 
            FROM settings 
            WHERE key IN ('label_tools_name', 'label_tools_icon', 'label_consumables_name', 'label_consumables_icon')
        ''')
        
        for row in results:
            settings[row['key']] = row['value']
        
        return render_template('setup_settings.html',
            label_tools_name=settings.get('label_tools_name', 'Werkzeuge'),
            label_tools_icon=settings.get('label_tools_icon', 'fas fa-tools'),
            label_consumables_name=settings.get('label_consumables_name', 'Verbrauchsmaterial'),
            label_consumables_icon=settings.get('label_consumables_icon', 'fas fa-box-open'))
    except Exception as e:
        logger.error(f"Fehler beim Laden der Einstellungen: {e}")
        return render_template('setup_settings.html', error='Fehler beim Laden der Einstellungen')

@bp.route('/setup/optional', methods=['GET', 'POST'])
def setup_optional():
    if request.method == 'POST':
        categories = request.form.getlist('categories[]')
        locations = request.form.getlist('locations[]')
        departments = request.form.getlist('departments[]')
        
        try:
            with Database.get_db() as conn:
                # Kategorien
                for category in categories:
                    if category.strip():
                        conn.execute('''
                            INSERT INTO categories (name, description)
                            VALUES (?, ?)
                        ''', (category.strip(), f'Kategorie: {category.strip()}'))
                
                # Standorte
                for location in locations:
                    if location.strip():
                        conn.execute('''
                            INSERT INTO locations (name, description)
                            VALUES (?, ?)
                        ''', (location.strip(), f'Standort: {location.strip()}'))
                
                # Abteilungen
                for department in departments:
                    if department.strip():
                        conn.execute('''
                            INSERT INTO departments (name, description)
                            VALUES (?, ?)
                        ''', (department.strip(), f'Abteilung: {department.strip()}'))
                
                conn.commit()
                flash('Einrichtung erfolgreich abgeschlossen!', 'success')
                return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error(f"Fehler beim Speichern der optionalen Einstellungen: {e}")
            return render_template('setup_optional.html', error='Fehler beim Speichern der Einstellungen')
    
    # Lade vorhandene Einstellungen für die Anzeige
    try:
        with Database.get_db() as conn:
            # Hole alle Kategorien
            categories = conn.execute('''
                SELECT name FROM categories 
                WHERE deleted = 0 
                ORDER BY name
            ''').fetchall()
            
            # Hole alle Standorte
            locations = conn.execute('''
                SELECT name FROM locations 
                WHERE deleted = 0 
                ORDER BY name
            ''').fetchall()
            
            # Hole alle Abteilungen
            departments = conn.execute('''
                SELECT name FROM departments 
                WHERE deleted = 0 
                ORDER BY name
            ''').fetchall()
            
            return render_template('setup_optional.html', 
                                 categories=[c['name'] for c in categories],
                                 locations=[l['name'] for l in locations],
                                 departments=[d['name'] for d in departments])
    except Exception as e:
        logger.error(f"Fehler beim Laden der optionalen Einstellungen: {e}")
        return render_template('setup_optional.html', error='Fehler beim Laden der Einstellungen')

def is_admin_user_present():
    ticket_db = TicketDatabase()
    with ticket_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
    return count > 0

def create_admin_user(username, password, role):
    ticket_db = TicketDatabase()
    hashed_password = generate_password_hash(password)
    try:
        ticket_db.query('''INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)''', [username, hashed_password, role])
        return True, "Admin-Benutzer erfolgreich erstellt"
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}")
        return False, f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}" 