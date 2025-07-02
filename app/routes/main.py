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
        
        # Verwende die zentrale get_statistics Methode
        try:
            stats = MongoDBTool.get_statistics()
            tool_stats = stats['tool_stats']
            consumable_stats = stats['consumable_stats']
            worker_stats = stats['worker_stats']
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Statistiken: {str(e)}")
            import traceback
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            tool_stats = {'total': 0, 'available': 0, 'lent': 0, 'defect': 0}
            consumable_stats = {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0}
            worker_stats = {'total': 0, 'by_department': []}
        
        # Consumable- und Worker-Statistiken kommen jetzt von der zentralen get_statistics Methode

        # Ticket-Statistiken
        ticket_pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$group': {
                    '_id': None,
                    'total': {'$sum': 1},
                    'open': {
                        '$sum': {
                            '$cond': [{'$eq': ['$status', 'offen']}, 1, 0]
                        }
                    },
                    'in_progress': {
                        '$sum': {
                            '$cond': [{'$eq': ['$status', 'in_bearbeitung']}, 1, 0]
                        }
                    },
                    'closed': {
                        '$sum': {
                            '$cond': [{'$eq': ['$status', 'geschlossen']}, 1, 0]
                        }
                    }
                }
            }
        ]
        
        try:
            ticket_stats_result = list(mongodb.db.tickets.aggregate(ticket_pipeline))
            ticket_stats = ticket_stats_result[0] if ticket_stats_result else {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Ticket-Statistiken: {str(e)}")
            ticket_stats = {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}

        # Prüfung auf doppelte Barcodes
        try:
            duplicate_barcodes = MongoDBTool.get_duplicate_barcodes()
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der doppelten Barcodes: {str(e)}")
            duplicate_barcodes = []

        # Lade aktive Hinweise aus der Datenbank
        try:
            notices = mongodb.find('homepage_notices', {'is_active': True})
            # Sortiere die Hinweise nach Priorität und Erstellungsdatum
            notices.sort(key=lambda x: (x.get('priority', 0), x.get('created_at', datetime.min)), reverse=True)
        except Exception as e:
            current_app.logger.error(f"Fehler beim Laden der Hinweise: {str(e)}")
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

@bp.route('/about')
def about():
    """Zeigt die About-Seite mit Systemdokumentation"""
    return render_template('about.html') 