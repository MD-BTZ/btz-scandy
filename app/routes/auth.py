from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from app.models.mongodb_models import MongoDBUser
from werkzeug.security import check_password_hash, generate_password_hash
from app.models.mongodb_database import MongoDB
from app.utils.auth_utils import needs_setup
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/auth')
mongodb = MongoDB()

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) 
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        # MongoDB User-Logik
        user_data = MongoDBUser.get_by_username(username)
            
        if user_data and check_password_hash(user_data['password_hash'], password):
            if user_data.get('is_active', True):
                # Erstelle ein User-Objekt für Flask-Login
                from app.models.user import User
                user = User(user_data)
                
                login_user(user, remember=remember) 
                
                flash('Anmeldung erfolgreich!', 'success')
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '' and urlparse(next_page).netloc != request.host:
                    next_page = url_for('main.index') 
                return redirect(next_page)
            else:
                 flash('Ihr Benutzerkonto ist deaktiviert.', 'error')
        else:
            flash('Ungültiger Benutzername oder Passwort.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """Setup-Seite für die Ersteinrichtung"""
    if not needs_setup():
        flash('Das System wurde bereits eingerichtet.', 'info')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Die Passwörter stimmen nicht überein.', 'error')
            return render_template('auth/setup.html')
        
        # Admin-Benutzer erstellen
        admin_data = {
            'username': 'Admin',
            'password_hash': generate_password_hash(password),
            'role': 'admin',
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        try:
            mongodb.insert_one('users', admin_data)
            
            # Label-Einstellungen speichern
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
    logout_user()
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))