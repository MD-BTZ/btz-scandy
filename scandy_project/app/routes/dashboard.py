from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from app.config import Config

bp = Blueprint('dashboard', __name__)

@bp.route('/')
def index():
    """Dashboard-Hauptseite"""
    # Statistiken laden
    stats = MongoDBTool.get_statistics()
    
    # Bestandsprognose laden
    consumables_forecast = MongoDBTool.get_consumables_forecast()
    
    return render_template('dashboard/index.html',
                         stats=stats,
                         consumables_forecast=consumables_forecast) 