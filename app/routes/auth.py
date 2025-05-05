from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from urllib.parse import urlparse

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) 
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        user = User.get_by_username(username)
            
        if user and user.check_password(password):
            if user.is_active:
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

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))