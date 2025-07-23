from flask import Blueprint, render_template, current_app, redirect, url_for
from flask_login import current_user
from ..utils.auth_utils import needs_setup
from ..models.mongodb_database import MongoDB
from ..models.mongodb_models import MongoDBTool
from datetime import datetime

# Kein URL-Präfix für den Main-Blueprint
bp = Blueprint('main', __name__, url_prefix='')
mongodb = MongoDB()

@bp.route('/')
def index():
    """Zeigt die Hauptseite mit Statistiken"""
    # Prüfe ob Setup erforderlich ist
    if needs_setup():
        return redirect(url_for('setup.setup_admin'))
    
    # Für eingeloggte Teilnehmer: Keine Weiterleitung - sie können die Startseite sehen
    # if current_user.is_authenticated and current_user.role == 'teilnehmer':
    #     return redirect(url_for('workers.timesheet_list'))
        
    try:
        # Prüfe ob MongoDB verfügbar ist
        try:
            # Teste die Verbindung
            if mongodb._client is not None:
                mongodb._client.admin.command('ping')
            else:
                raise Exception("MongoDB-Verbindung nicht initialisiert")
        except Exception as db_error:
            current_app.logger.error(f"MongoDB-Verbindung nicht verfügbar: {str(db_error)}")
            # Wähle das Template basierend auf der Benutzerrolle
            if not current_user.is_authenticated:
                template_name = 'index_public.html'
            elif current_user.role == 'teilnehmer':
                template_name = 'index_teilnehmer.html'
            else:
                template_name = 'index_normal.html'
            
            return render_template(template_name,
                               tool_stats={'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                               consumable_stats={'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                               worker_stats={'total': 0, 'by_department': []},
                               ticket_stats={'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0},
                               duplicate_barcodes=[],
                               notices=[])
        
        # Verwende den zentralen Statistics Service
        try:
            from app.services.statistics_service import StatisticsService
            stats = StatisticsService.get_all_statistics()
            tool_stats = stats['tool_stats']
            consumable_stats = stats['consumable_stats']
            worker_stats = stats['worker_stats']
            ticket_stats = stats['ticket_stats']
            duplicate_barcodes = stats['duplicate_barcodes']
            notices = StatisticsService.get_notices()
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Statistiken: {str(e)}")
            import traceback
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            tool_stats = {'total': 0, 'available': 0, 'lent': 0, 'defect': 0}
            consumable_stats = {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0}
            worker_stats = {'total': 0, 'by_department': []}
            ticket_stats = {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
            duplicate_barcodes = []
            notices = []
        
        # Wähle das Template basierend auf der Benutzerrolle
        if not current_user.is_authenticated:
            template_name = 'index_public.html'
        elif current_user.role == 'teilnehmer':
            template_name = 'index_teilnehmer.html'
        else:
            template_name = 'index_normal.html'
        
        return render_template(template_name,
                           tool_stats=tool_stats,
                           consumable_stats=consumable_stats,
                           worker_stats=worker_stats,
                           ticket_stats=ticket_stats,
                           duplicate_barcodes=duplicate_barcodes,
                           notices=notices)
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Startseite: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template('index.html',
                           tool_stats={'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                           consumable_stats={'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                           worker_stats={'total': 0, 'by_department': []},
                           ticket_stats={'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0},
                           duplicate_barcodes=[],
                           notices=[])

@bp.route('/emergency-admin')
def emergency_admin():
    """
    Notfall-Route zur Erstellung eines Admin-Benutzers
    """
    try:
        from werkzeug.security import generate_password_hash
        from datetime import datetime
        
        # Prüfe ob Admin-Benutzer bereits existiert
        admin_user = mongodb.find_one('users', {'role': 'admin'})
        
        if admin_user:
                    return f"""
        <html>
        <head><title>Admin-Benutzer existiert</title></head>
        <body>
            <h1>✅ Admin-Benutzer existiert bereits</h1>
            <p><strong>Benutzername:</strong> admin</p>
            <p><strong>Passwort:</strong> [Standard-Passwort]</p>
            <p><a href="/auth/login">→ Zum Login</a></p>
        </body>
        </html>
        """
        
        # Erstelle Admin-Benutzer
        admin_data = {
            'username': 'admin',
            'password_hash': generate_password_hash('admin'),
            'role': 'admin',
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'firstname': 'Administrator',
            'lastname': 'System',
            'email': 'admin@scandy.local'
        }
        
        result = mongodb.insert_one('users', admin_data)
        
        return f"""
        <html>
        <head><title>Admin-Benutzer erstellt</title></head>
        <body>
            <h1>✅ Admin-Benutzer erfolgreich erstellt!</h1>
            <p><strong>Benutzername:</strong> admin</p>
            <p><strong>Passwort:</strong> [Standard-Passwort]</p>
            <p><a href="/auth/login">→ Zum Login</a></p>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <html>
        <head><title>Fehler</title></head>
        <body>
            <h1>❌ Fehler beim Erstellen des Admin-Benutzers</h1>
            <p>Fehler: {str(e)}</p>
        </body>
        </html>
        """

@bp.route('/about')
def about():
    """Zeigt die About-Seite mit Systemdokumentation"""
    return render_template('about.html') 