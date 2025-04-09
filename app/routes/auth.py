from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
import sqlite3
import os
from app.config import Config
from app.models.init_db import init_users

bp = Blueprint('auth', __name__, url_prefix='/auth')

def get_user_db():
    """Verbindung zur Benutzerdatenbank herstellen"""
    db_path = os.path.join(Config.DATABASE_DIR, 'users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login-Seite"""
    # Initialisiere Benutzerdatenbank falls nicht vorhanden
    init_users()
    
    # Wenn bereits eingeloggt, direkt zur Hauptseite
    if session.get('user_id'):
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        with get_user_db() as conn:
            user = conn.execute(
                'SELECT * FROM users WHERE username = ?', 
                [username]
            ).fetchone()
            
            if user and check_password_hash(user['password'], password):
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = True  # Alle Benutzer sind vorerst Admin
                return redirect(url_for('main.index'))
            
            flash('Ungültiger Benutzername oder Passwort', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))