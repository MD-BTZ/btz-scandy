from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from app.config import Config
from app.utils.decorators import login_required, not_teilnehmer_required
from flask_login import current_user

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    """Dashboard-Hauptseite"""
    # Für Teilnehmer: Weiterleitung zu Wochenberichten
    if current_user.role == 'teilnehmer':
        return redirect(url_for('workers.teilnehmer_timesheet_list'))
    
    # Statistiken laden
    stats = MongoDBTool.get_statistics()
    
    # Bestandsprognose laden
    consumables_forecast = MongoDBTool.get_consumables_forecast()
    
    # Duplikat-Barcodes prüfen
    duplicate_barcodes = MongoDBTool.get_duplicate_barcodes()
    
    return render_template('dashboard/index.html',
                         stats=stats,
                         consumables_forecast=consumables_forecast,
                         duplicate_barcodes=duplicate_barcodes) 