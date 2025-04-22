from flask import Blueprint, render_template
from app.models.database import Database

bp = Blueprint('index', __name__)

@bp.route('/')
def index():
    """Startseite anzeigen"""
    # Lade aktive Hinweise aus der Datenbank
    notices = Database.query('''
        SELECT * FROM homepage_notices 
        WHERE is_active = 1 
        ORDER BY priority DESC, created_at DESC
    ''')
    
    # Lade Statistiken für die Startseite
    stats = {
        'tools': Database.query('SELECT COUNT(*) as count FROM tools WHERE deleted = 0', one=True)['count'],
        'workers': Database.query('SELECT COUNT(*) as count FROM workers WHERE deleted = 0', one=True)['count'],
        'consumables': Database.query('SELECT COUNT(*) as count FROM consumables WHERE deleted = 0', one=True)['count'],
        'active_lendings': Database.query('''
            SELECT COUNT(*) as count 
            FROM lendings 
            WHERE returned_at IS NULL
        ''', one=True)['count']
    }
    
    return render_template('index.html', notices=notices, stats=stats) 