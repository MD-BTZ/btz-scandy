from flask import Blueprint, render_template, current_app, redirect, url_for
from flask_login import current_user
from ..utils.auth_utils import needs_setup
from ..models.mongodb_database import MongoDB
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
        
    try:
        # Werkzeug-Statistiken mit MongoDB-Aggregation
        tool_pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$lookup': {
                    'from': 'lendings',
                    'localField': 'barcode',
                    'foreignField': 'tool_barcode',
                    'as': 'active_lendings'
                }
            },
            {
                '$addFields': {
                    'has_active_lending': {
                        '$gt': [
                            {'$size': {'$filter': {'input': '$active_lendings', 'cond': {'$eq': ['$$this.returned_at', None]}}}},
                            0
                        ]
                    }
                }
            },
            {
                '$group': {
                    '_id': None,
                    'total': {'$sum': 1},
                    'available': {
                        '$sum': {
                            '$cond': [
                                {'$and': [{'$eq': ['$status', 'verfügbar']}, {'$not': '$has_active_lending'}]},
                                1,
                                0
                            ]
                        }
                    },
                    'lent': {
                        '$sum': {
                            '$cond': ['$has_active_lending', 1, 0]
                        }
                    },
                    'defect': {
                        '$sum': {
                            '$cond': [{'$eq': ['$status', 'defekt']}, 1, 0]
                        }
                    }
                }
            }
        ]
        
        tool_stats_result = list(mongodb.db.tools.aggregate(tool_pipeline))
        tool_stats = tool_stats_result[0] if tool_stats_result else {'total': 0, 'available': 0, 'lent': 0, 'defect': 0}
        
        # Verbrauchsmaterial-Statistiken
        consumable_pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$group': {
                    '_id': None,
                    'total': {'$sum': 1},
                    'sufficient': {
                        '$sum': {
                            '$cond': [{'$gte': ['$quantity', '$min_quantity']}, 1, 0]
                        }
                    },
                    'warning': {
                        '$sum': {
                            '$cond': [
                                {
                                    '$and': [
                                        {'$lt': ['$quantity', '$min_quantity']},
                                        {'$gte': ['$quantity', {'$multiply': ['$min_quantity', 0.5]}]}
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    },
                    'critical': {
                        '$sum': {
                            '$cond': [
                                {'$lt': ['$quantity', {'$multiply': ['$min_quantity', 0.5]}]},
                                1,
                                0
                            ]
                        }
                    }
                }
            }
        ]
        
        consumable_stats_result = list(mongodb.db.consumables.aggregate(consumable_pipeline))
        consumable_stats = consumable_stats_result[0] if consumable_stats_result else {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0}

        # Mitarbeiter-Statistiken
        worker_pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$group': {
                    '_id': '$department',
                    'count': {'$sum': 1}
                }
            },
            {'$match': {'_id': {'$ne': None}}},
            {'$sort': {'_id': 1}},
            {
                '$project': {
                    'name': '$_id',
                    'count': 1,
                    '_id': 0
                }
            }
        ]
        
        worker_by_department = list(mongodb.db.workers.aggregate(worker_pipeline))
        worker_total = mongodb.db.workers.count_documents({'deleted': {'$ne': True}})
        
        worker_stats = {
            'total': worker_total,
            'by_department': worker_by_department
        }

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
        
        ticket_stats_result = list(mongodb.db.tickets.aggregate(ticket_pipeline))
        ticket_stats = ticket_stats_result[0] if ticket_stats_result else {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}

        # Prüfung auf doppelte Barcodes
        tool_entries = list(mongodb.db.tools.find({'deleted': {'$ne': True}}, {'barcode': 1, 'name': 1}))
        consumable_entries = list(mongodb.db.consumables.find({'deleted': {'$ne': True}}, {'barcode': 1, 'name': 1}))
        worker_entries = list(mongodb.db.workers.find({'deleted': {'$ne': True}}, {'barcode': 1, 'firstname': 1, 'lastname': 1}))
        
        barcode_map = {}
        for entry in tool_entries:
            bc = entry.get('barcode')
            if bc:
                barcode_map.setdefault(bc, []).append({'type': 'Werkzeug', 'name': entry.get('name', '')})
        for entry in consumable_entries:
            bc = entry.get('barcode')
            if bc:
                barcode_map.setdefault(bc, []).append({'type': 'Verbrauchsmaterial', 'name': entry.get('name', '')})
        for entry in worker_entries:
            bc = entry.get('barcode')
            if bc:
                name = f"{entry.get('firstname', '')} {entry.get('lastname', '')}".strip()
                barcode_map.setdefault(bc, []).append({'type': 'Mitarbeiter', 'name': name})
        
        duplicate_barcodes = [
            {'barcode': bc, 'entries': infos}
            for bc, infos in barcode_map.items() if len(infos) > 1
        ]

        # Lade aktive Hinweise aus der Datenbank
        notices = mongodb.find('homepage_notices', {'is_active': True})
        # Sortiere die Hinweise nach Priorität und Erstellungsdatum
        notices.sort(key=lambda x: (x.get('priority', 0), x.get('created_at', datetime.min)), reverse=True)
        
        return render_template('index.html',
                           tool_stats=tool_stats,
                           consumable_stats=consumable_stats,
                           worker_stats=worker_stats,
                           ticket_stats=ticket_stats,
                           duplicate_barcodes=duplicate_barcodes,
                           notices=notices)
        
    except Exception as e:
        current_app.logger.error(f"Fehler beim Laden der Startseite: {str(e)}")
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