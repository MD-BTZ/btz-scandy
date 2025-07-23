"""
Authentifizierung und Benutzerverwaltung

Dieses Modul enthält alle Routen für die Benutzerauthentifizierung:
- Login/Logout
- Setup für die Ersteinrichtung
- Profilverwaltung (E-Mail und Passwort ändern)

Alle Routen verwenden Flask-Login für die Session-Verwaltung
und MongoDB für die Benutzerdaten.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app.models.mongodb_models import MongoDBUser
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.mongodb_database import MongoDB
from app.utils.auth_utils import needs_setup
from datetime import datetime
from bson import ObjectId
from typing import Union
import logging

bp = Blueprint('auth', __name__, url_prefix='/auth')
mongodb = MongoDB()
logger = logging.getLogger(__name__)

def convert_id_for_query(id_value: str) -> Union[str, ObjectId]:
    """
    Konvertiert eine ID für Datenbankabfragen.
    Versucht zuerst mit String-ID, dann mit ObjectId.
    """
    try:
        # Versuche zuerst mit String-ID (für importierte Daten)
        return id_value
    except:
        # Falls das fehlschlägt, versuche ObjectId
        try:
            return ObjectId(id_value)
        except:
            # Falls auch das fehlschlägt, gib die ursprüngliche ID zurück
            return id_value

def get_objectid_if_possible(id_value):
    if isinstance(id_value, str) and len(id_value) == 24:
        try:
            return ObjectId(id_value)
        except Exception:
            return id_value
    return id_value

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Benutzeranmeldung.
    
    GET: Zeigt das Login-Formular
    POST: Verarbeitet die Anmeldedaten
    
    Validierung:
    - Benutzername und Passwort müssen korrekt sein
    - Benutzerkonto muss aktiv sein
    
    Redirects:
    - Bei erfolgreicher Anmeldung: Zur ursprünglich gewünschten Seite oder Dashboard
    - Bei bereits angemeldeten Benutzern: Direkt zum Dashboard
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) 
    
    if request.method == 'POST':
        # ===== FORMULARDATEN HOLEN =====
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        # ===== BENUTZER VALIDIEREN =====
        user_data = MongoDBUser.get_by_username(username)
            
        from app.utils.auth_utils import check_password_compatible
        if user_data and check_password_compatible(user_data['password_hash'], password):
            if user_data.get('is_active', True):
                # Konvertiere alte Hash-Formate zu werkzeug-Hash bei erfolgreicher Anmeldung
                if (user_data['password_hash'].startswith('scrypt:') or 
                    user_data['password_hash'].startswith('$2b$')):
                    try:
                        from werkzeug.security import generate_password_hash
                        from bson import ObjectId
                        new_hash = generate_password_hash(password)
                        mongodb.update_one('users', 
                                         {'_id': user_data['_id']}, 
                                         {'$set': {'password_hash': new_hash, 'updated_at': datetime.now()}})
                        # Aktualisiere user_data für die Session
                        user_data['password_hash'] = new_hash
                        print(f"Passwort-Hash für Benutzer {user_data['username']} erfolgreich konvertiert")
                    except Exception as e:
                        print(f"Fehler bei der Passwort-Konvertierung: {e}")
                        # Fahre trotz Fehler fort - der Login war erfolgreich
                
                # Erstelle ein User-Objekt für Flask-Login
                from app.models.user import User
                user = User(user_data)
                print(f"User-Objekt erstellt: {user.username}, ID: {user.id}, Role: {user.role}")
                
                login_user(user, remember=remember) 
                print(f"login_user aufgerufen für: {user.username}")
                
                flash('Anmeldung erfolgreich!', 'success')
                
                # ===== REDIRECT LOGIK =====
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '' and urlparse(next_page).netloc != request.host:
                    next_page = url_for('main.index') 
                return redirect(next_page)
            else:
                 flash('Ihr Benutzerkonto ist deaktiviert.', 'error')
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/debug/users')
def debug_users():
    """Debug-Route um alle Benutzer anzuzeigen"""
    try:
        from app.models.mongodb_models import MongoDBUser
        users = MongoDBUser.get_all()
        user_info = []
        for user in users:
            user_info.append({
                'id': user.get('_id'),
                'username': user.get('username'),
                'role': user.get('role'),
                'password_hash_start': user.get('password_hash', '')[:20] + '...' if user.get('password_hash') else 'None'
            })
        return jsonify(user_info)
    except Exception as e:
        return jsonify({'error': str(e)})

@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """
    Ersteinrichtung des Systems.
    
    GET: Zeigt das Setup-Formular
    POST: Erstellt den ersten Admin-Benutzer und Systemeinstellungen
    
    Erstellt:
    - Admin-Benutzer mit gewähltem Passwort
    - Standard-Systemeinstellungen (Labels für Tickets, Tools, etc.)
    
    Zugriff nur möglich wenn noch kein Admin-Benutzer existiert.
    """
    if not needs_setup():
        flash('Das System wurde bereits eingerichtet.', 'info')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # ===== PASSWORT VALIDIERUNG =====
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Die Passwörter stimmen nicht überein.', 'error')
            return render_template('auth/setup.html')
        
        # ===== ADMIN-BENUTZER ERSTELLEN =====
        admin_data = {
            'username': 'Admin',
            'password_hash': generate_password_hash(password),
            'role': 'admin',
            'is_active': True,
            'timesheet_enabled': False,  # Admin standardmäßig deaktiviert
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        try:
            mongodb.insert_one('users', admin_data)
            
            # ===== SYSTEMEINSTELLUNGEN SPEICHERN =====
            settings = [
                {'key': 'label_tickets_name', 'value': request.form.get('label_tickets_name', 'Tickets')},
                {'key': 'label_tickets_icon', 'value': request.form.get('label_tickets_icon', 'fas fa-ticket-alt')},
                {'key': 'label_tools_name', 'value': request.form.get('label_tools_name', 'Werkzeuge')},
                {'key': 'label_tools_icon', 'value': request.form.get('label_tools_icon', 'fas fa-tools')},
                {'key': 'label_consumables_name', 'value': request.form.get('label_consumables_name', 'Verbrauchsmaterial')},
                {'key': 'label_consumables_icon', 'value': request.form.get('label_consumables_icon', 'fas fa-box-open')}
            ]
            
            for setting in settings:
                mongodb.update_one('settings', 
                                 {'key': setting['key']}, 
                                 {'$set': setting}, 
                                 upsert=True)
            
            flash('Setup erfolgreich abgeschlossen! Sie können sich jetzt anmelden.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            flash(f'Fehler beim Setup: {str(e)}', 'error')
            return render_template('auth/setup.html')
    
    return render_template('auth/setup.html')

@bp.route('/logout')
@login_required
def logout():
    """
    Benutzer abmelden.
    
    Beendet die aktuelle Session und leitet zur Login-Seite weiter.
    """
    logout_user()
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Benutzerprofil bearbeiten.
    
    GET: Zeigt das Profilformular mit aktuellen Benutzerdaten
    POST: Aktualisiert E-Mail und/oder Passwort
    
    Validierung:
    - E-Mail darf nicht bereits von anderem Benutzer verwendet werden
    - Aktuelles Passwort muss korrekt sein (bei Passwortänderung)
    - Neues Passwort muss mindestens 8 Zeichen lang sein
    - Neue Passwörter müssen übereinstimmen
    """
    if request.method == 'POST':
        try:
            # ===== DEBUG: Formulardaten loggen =====
            logger.info(f"DEBUG: Profile-Update für User: {current_user.username}")
            logger.info(f"DEBUG: Formulardaten: {dict(request.form)}")
            
            # ===== AKTUELLE BENUTZERDATEN HOLEN =====
            user = mongodb.find_one('users', {'username': current_user.username})
            if not user:
                flash('Benutzer nicht gefunden', 'error')
                return redirect(url_for('auth.profile'))
            
            logger.info(f"DEBUG: Aktueller User aus DB: {user.get('username')}, ID: {user.get('_id')}, Email: {user.get('email')}")
            
            # ===== FORMULARDATEN HOLEN UND VALIDIEREN =====
            from app.services.validation_service import ValidationService
            from app.services.utility_service import UtilityService
            
            form_data = UtilityService.get_form_data_dict(request.form)
            logger.info(f"DEBUG: Verarbeitete Formulardaten: {form_data}")
            
            # Validierung für Profil-Update
            email = form_data.get('email', '').strip()
            current_password = form_data.get('current_password', '').strip()
            new_password = form_data.get('new_password', '').strip()
            new_password_confirm = form_data.get('new_password_confirm', '').strip()
            timesheet_enabled = form_data.get('timesheet_enabled') == 'on'
            
            logger.info(f"DEBUG: Extrahierte Werte - Email: '{email}', Timesheet: {timesheet_enabled}")
            
            # ===== E-MAIL ÄNDERN =====
            if email and email != user.get('email', ''):
                logger.info(f"DEBUG: E-Mail-Update wird durchgeführt - von '{user.get('email')}' zu '{email}'")
                
                # Prüfe ob E-Mail bereits von anderem Benutzer verwendet wird
                existing_user = mongodb.find_one('users', {
                    'email': email,
                    'username': {'$ne': current_user.username}
                })
                if existing_user:
                    flash('Diese E-Mail-Adresse wird bereits von einem anderen Benutzer verwendet.', 'error')
                    return render_template('auth/profile.html', user=user)
                
                # E-Mail validieren
                if not ValidationService._is_valid_email(email):
                    flash('Ungültige E-Mail-Adresse.', 'error')
                    return render_template('auth/profile.html', user=user)
                
                # E-Mail aktualisieren
                logger.info(f"DEBUG: Führe E-Mail-Update aus mit ID: {get_objectid_if_possible(user['_id'])}")
                update_result = mongodb.update_one('users', 
                                 {'_id': get_objectid_if_possible(user['_id'])}, 
                                 {'$set': {'email': email, 'updated_at': datetime.now()}})
                logger.info(f"DEBUG: E-Mail-Update-Ergebnis: {update_result}")
                
                flash('E-Mail-Adresse erfolgreich aktualisiert.', 'success')
            else:
                logger.info(f"DEBUG: Kein E-Mail-Update - Email: '{email}', DB-Email: '{user.get('email')}'")
            
            # ===== PASSWORT ÄNDERN =====
            if new_password:
                if not current_password:
                    flash('Bitte geben Sie Ihr aktuelles Passwort ein, um das Passwort zu ändern.', 'error')
                    return render_template('auth/profile.html', user=user)
                
                # Prüfe aktuelles Passwort
                from app.utils.auth_utils import check_password_compatible
                if not check_password_compatible(current_password, user.get('password_hash', '')):
                    flash('Aktuelles Passwort ist falsch.', 'error')
                    return render_template('auth/profile.html', user=user)
                
                # Validierung mit ValidationService
                validation_data = {
                    'password': new_password,
                    'password_confirm': new_password_confirm
                }
                is_valid, errors = ValidationService.validate_user_form(validation_data, is_edit=True)
                
                if not is_valid:
                    for error in errors:
                        flash(error, 'error')
                    return render_template('auth/profile.html', user=user)
                
                # Passwort aktualisieren
                from werkzeug.security import generate_password_hash
                password_hash = generate_password_hash(new_password)
                
                mongodb.update_one('users', 
                                 {'_id': get_objectid_if_possible(user['_id'])}, 
                                 {'$set': {'password_hash': password_hash, 'updated_at': datetime.now()}})
                flash('Passwort erfolgreich geändert.', 'success')
            
            # ===== WOCHENBERICHT-EINSTELLUNG ÄNDERN =====
            if timesheet_enabled != user.get('timesheet_enabled', False):
                mongodb.update_one('users', 
                                 {'_id': get_objectid_if_possible(user['_id'])}, 
                                 {'$set': {'timesheet_enabled': timesheet_enabled, 'updated_at': datetime.now()}})
                
                if timesheet_enabled:
                    flash('Wochenbericht-Feature wurde aktiviert.', 'success')
                else:
                    flash('Wochenbericht-Feature wurde deaktiviert.', 'success')
            
            # Aktualisiere user für Template
            user = mongodb.find_one('users', {'username': current_user.username})
            logger.info(f"DEBUG: User nach Update - Email: {user.get('email')}")
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Benutzerprofils: {e}")
            flash('Fehler beim Aktualisieren des Profils.', 'error')
    
    # ===== BENUTZERDATEN FÜR TEMPLATE VORBEREITEN =====
    user = mongodb.find_one('users', {'username': current_user.username})
    
    # Stelle sicher, dass alle erforderlichen Felder vorhanden sind
    if user:
        user.setdefault('firstname', '')
        user.setdefault('lastname', '')
        user.setdefault('email', '')
        user.setdefault('role', 'anwender')
    
    return render_template('auth/profile.html', user=user)