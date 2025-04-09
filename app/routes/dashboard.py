from flask import Blueprint, render_template, current_app
from app.models.database import Database
from app.config import Config

bp = Blueprint('dashboard', __name__)

@bp.route('/')
def index():
    """Dashboard-Hauptseite"""
    # Statistiken laden
    stats = Database.get_statistics()
    
    # Bestandsprognose laden
    consumables_forecast = Database.get_consumables_forecast()
    
    return render_template('dashboard/index.html',
                         stats=stats,
                         consumables_forecast=consumables_forecast) 