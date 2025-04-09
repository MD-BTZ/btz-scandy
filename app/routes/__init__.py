# app/routes/__init__.py
from flask import Flask
from app.routes.auth import bp as auth_bp
from app.routes.tools import bp as tools_bp
from app.routes.workers import bp as workers_bp
from app.routes.consumables import bp as consumables_bp
from app.routes.api import bp as api_bp
from app.routes.admin import bp as admin_bp
from app.routes.inventory import bp as inventory_bp
from app.routes.quick_scan import bp as quick_scan_bp
from app.routes.history import bp as history_bp
from app.routes.main import bp as main_bp

def init_app(app):
    """Registriert alle Blueprints mit ihren URL-Präfixen"""
    app.register_blueprint(main_bp)  # Kein Präfix für main
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(tools_bp, url_prefix='/tools')
    app.register_blueprint(workers_bp, url_prefix='/workers')
    app.register_blueprint(consumables_bp, url_prefix='/consumables')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(quick_scan_bp, url_prefix='/quick-scan')
    app.register_blueprint(history_bp, url_prefix='/history')

__all__ = [
    'auth_bp', 'tools_bp', 'workers_bp', 'consumables_bp',
    'api_bp', 'admin_bp', 'inventory_bp', 'quick_scan_bp', 'history_bp', 'main_bp'
]