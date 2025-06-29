from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, send_file, current_app, abort
from flask_login import current_user
from app.utils.decorators import admin_required, mitarbeiter_required, login_required
from app.models.mongodb_models import MongoDBUser
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from flask import current_app
import colorsys
import logging
from datetime import datetime, timedelta
from app.utils.backup_manager import backup_manager
import openpyxl
from io import BytesIO
import time
from PIL import Image
import io
from app.config.config import Config
from app.models.mongodb_database import mongodb
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.database_helpers import get_categories_from_settings, get_ticket_categories_from_settings
from docxtpl import DocxTemplate
from urllib.parse import unquote
import pandas as pd
import tempfile

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Stelle sicher, dass die Standard-Einstellungen beim Start der App vorhanden sind
# ensure_default_settings()

def ensure_default_settings():
    """Stellt sicher, dass die Standard-Label-Einstellungen vorhanden sind"""
    default_settings = [
        {'key': 'label_tickets_name', 'value': 'Tickets'},
        {'key': 'label_tickets_icon', 'value': 'fas fa-ticket-alt'},
        {'key': 'label_tools_name', 'value': 'Werkzeuge'},
        {'key': 'label_tools_icon', 'value': 'fas fa-tools'},
        {'key': 'label_consumables_name', 'value': 'Verbrauchsmaterial'},
        {'key': 'label_consumables_icon', 'value': 'fas fa-box-open'}
    ]
    
    for setting in default_settings:
        mongodb.update_one('settings', 
                         {'key': setting['key']}, 
                         {'$setOnInsert': setting}, 
                         upsert=True)

def get_recent_activity():
    """Hole die letzten Aktivitäten"""
    try:
        # Hole die letzten 10 Ausleihen
        recent_lendings = list(mongodb.find('lendings', {}, sort=[('lent_at', -1)], limit=10))
        
        # Hole die letzten 10 Verbrauchsmaterial-Ausgaben
        recent_usages = list(mongodb.find('consumable_usages', {}, sort=[('used_at', -1)], limit=10))
        
        activities = []
        
        # Ausleihen verarbeiten
        for lending in recent_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
            
            if tool and worker:
                activities.append({
                    'type': 'lending',
                    'timestamp': lending['lent_at'],
                    'description': f'Werkzeug "{tool["name"]}" an {worker["firstname"]} {worker["lastname"]} ausgeliehen',
                    'icon': 'fas fa-tools'
                })
        
        # Verbrauchsmaterial verarbeiten
        for usage in recent_usages:
            consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
            worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
            
            if consumable and worker:
                activities.append({
                    'type': 'usage',
                    'timestamp': usage['used_at'],
                    'description': f'{usage["quantity"]}x "{consumable["name"]}" an {worker["firstname"]} {worker["lastname"]} ausgegeben',
                    'icon': 'fas fa-box-open'
                })
        
        # Nach Zeitstempel sortieren und die letzten 10 zurückgeben
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:10]
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der letzten Aktivitäten: {str(e)}")
        return []

def get_material_usage():
    """Hole die Materialnutzung"""
    try:
        # Hole Verbrauchsmaterial-Ausgaben der letzten 30 Tage
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        pipeline = [
            {
                '$match': {
                    'used_at': {'$gte': thirty_days_ago}
                }
            },
            {
                '$lookup': {
                    'from': 'consumables',
                    'localField': 'consumable_barcode',
                    'foreignField': 'barcode',
                    'as': 'consumable'
                }
            },
            {
                '$unwind': '$consumable'
            },
            {
                '$group': {
                    '_id': '$consumable_barcode',
                    'name': {'$first': '$consumable.name'},
                    'total_quantity': {'$sum': '$quantity'},
                    'usage_count': {'$sum': 1}
                }
            },
            {
                '$sort': {'total_quantity': -1}
            },
            {
                '$limit': 5
            }
        ]
        
        usage_stats = list(mongodb.db.consumable_usages.aggregate(pipeline))
        
        return usage_stats
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Materialnutzung: {str(e)}")
        return []

def get_warnings():
    """Hole aktuelle Warnungen"""
    try:
        warnings = []
        
        # Warnung für niedrige Verbrauchsmaterial-Bestände
        low_stock_consumables = list(mongodb.find('consumables', {
            'deleted': {'$ne': True},
            '$expr': {
                '$lte': ['$quantity', '$min_quantity']
            }
        }))
        
        for consumable in low_stock_consumables:
            warnings.append({
                'type': 'low_stock',
                'severity': 'warning',
                'message': f'Verbrauchsmaterial "{consumable["name"]}" hat niedrigen Bestand: {consumable["quantity"]}',
                'icon': 'fas fa-exclamation-triangle'
            })
        
        # Warnung für überfällige Ausleihen (mehr als 30 Tage)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        overdue_lendings = list(mongodb.find('lendings', {
            'returned_at': None,
            'lent_at': {'$lt': thirty_days_ago}
        }))
        
        for lending in overdue_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
            
            if tool and worker:
                days_overdue = (datetime.now() - lending['lent_at']).days
                warnings.append({
                    'type': 'overdue',
                    'severity': 'danger',
                    'message': f'Werkzeug "{tool["name"]}" ist seit {days_overdue} Tagen an {worker["firstname"]} {worker["lastname"]} ausgeliehen',
                    'icon': 'fas fa-clock'
                })
        
        # Warnung für defekte Werkzeuge
        defective_tools = list(mongodb.find('tools', {
            'deleted': {'$ne': True},
            'status': 'defekt'
        }))
        
        for tool in defective_tools:
            warnings.append({
                'type': 'defective',
                'severity': 'info',
                'message': f'Werkzeug "{tool["name"]}" ist als defekt markiert',
                'icon': 'fas fa-tools'
            })
        
        return warnings
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Warnungen: {str(e)}")
        return []

def get_backup_info():
    """Hole Informationen über vorhandene Backups"""
    backups = []
    backup_dir = Path(__file__).parent.parent.parent / 'backups'
    
    if backup_dir.exists():
        for backup_file in sorted(backup_dir.glob('*.json'), reverse=True):
            # Backup-Statistiken aus der Datei lesen
            stats = None
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    import json
                    data = json.load(f)
                    stats = {
                        'tools': len(data.get('tools', [])),
                        'consumables': len(data.get('consumables', [])),
                        'workers': len(data.get('workers', [])),
                        'active_lendings': len([l for l in data.get('lendings', []) if not l.get('returned_at')])
                    }
            except:
                stats = None
            
            # Unix-Timestamp verwenden
            created_timestamp = backup_file.stat().st_mtime
            
            backups.append({
                'name': backup_file.name,
                'size': backup_file.stat().st_size,
                'created': created_timestamp,
                'stats': stats
            })
    
    return backups

def get_consumables_forecast():
    """Berechnet die Bestandsprognose für Verbrauchsmaterialien"""
    # MongoDB-Version der Prognose
    pipeline = [
        {
            '$lookup': {
                'from': 'consumable_usages',
                'localField': 'barcode',
                'foreignField': 'consumable_barcode',
                'as': 'usages'
            }
        },
        {
            '$addFields': {
                'recent_usages': {
                    '$filter': {
                        'input': '$usages',
                        'cond': {
                            '$gte': [
                                '$$this.used_at',
                                datetime.now() - timedelta(days=30)
                            ]
                        }
                    }
                }
            }
        },
        {
            '$addFields': {
                'avg_daily_usage': {
                    '$cond': {
                        'if': {'$gt': [{'$size': '$recent_usages'}, 0]},
                        'then': {
                            '$divide': [
                                {'$sum': '$recent_usages.quantity'},
                                30
                            ]
                        },
                        'else': 0
                    }
                }
            }
        },
        {
            '$addFields': {
                'days_remaining': {
                    '$cond': {
                        'if': {'$gt': ['$avg_daily_usage', 0]},
                        'then': {'$divide': ['$quantity', '$avg_daily_usage']},
                        'else': 999
                    }
                }
            }
        },
        {
            '$match': {
                'deleted': {'$ne': True},
                'quantity': {'$gt': 0}
            }
        },
        {
            '$sort': {'days_remaining': 1}
        },
        {
            '$limit': 6
        },
        {
            '$project': {
                'name': 1,
                'current_amount': '$quantity',
                'avg_daily_usage': {'$round': ['$avg_daily_usage', 2]},
                'days_remaining': {'$round': ['$days_remaining']}
            }
        }
    ]
    
    return list(mongodb.db.consumables.aggregate(pipeline))

def create_excel(data, columns):
    """Erstellt eine Excel-Datei aus den gegebenen Daten"""
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Headers hinzufügen
    for col, header in enumerate(columns, 1):
        ws.cell(row=1, column=col, value=header)
    
    # Daten einfügen
    for row, item in enumerate(data, 2):
        for col, key in enumerate(columns, 1):
            ws.cell(row=row, column=col, value=item.get(key, ''))
    
    # Excel-Datei in BytesIO speichern
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    return excel_file

# Angepasste Excel-Funktion für mehrere Sheets
def create_multi_sheet_excel(data_dict):
    """Erstellt eine Excel-Datei mit mehreren Arbeitsblättern"""
    import pandas as pd
    import tempfile
    import os
    
    # Erstelle temporäre Datei
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        tmp_file_path = tmp_file.name
    
    try:
        # Erstelle Excel-Writer
        with pd.ExcelWriter(tmp_file_path, engine='openpyxl') as writer:
            for sheet_name, data_list in data_dict.items():
                if data_list:
                    # Konvertiere MongoDB-Dokumente zu DataFrame
                    df = pd.DataFrame(data_list)
                    
                    # Entferne MongoDB-spezifische Felder
                    if '_id' in df.columns:
                        df = df.drop('_id', axis=1)
                    
                    # Schreibe Arbeitsblatt
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    # Leeres Arbeitsblatt erstellen
                    pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
        
        return tmp_file_path
        
    except Exception as e:
        # Bei Fehler temporäre Datei löschen
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
        raise e

@bp.route('/')
@mitarbeiter_required
def index():
    """Admin Dashboard"""
    return redirect(url_for('admin.dashboard'))

@bp.route('/dashboard')
@mitarbeiter_required
def dashboard():
    """Admin Dashboard"""
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
                        '$cond': [{'$gt': ['$quantity', '$min_quantity']}, 1, 0]
                    }
                },
                'critical': {
                    '$sum': {
                        '$cond': [{'$lte': ['$quantity', '$min_quantity']}, 1, 0]
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
    
    # Warnungen für defekte Werkzeuge und überfällige Ausleihen
    tool_warnings = []
    
    # Defekte Werkzeuge
    defect_tools = list(mongodb.find('tools', {'status': 'defekt', 'deleted': {'$ne': True}}))
    for tool in defect_tools:
        tool_warnings.append({
            'name': tool['name'],
            'status': 'defekt',
            'severity': 'error',
            'description': 'Werkzeug ist defekt'
        })
    
    # Überfällige Ausleihen
    overdue_date = datetime.now() - timedelta(days=5)
    overdue_lendings = list(mongodb.find('lendings', {
        'returned_at': None,
        'lent_at': {'$lt': overdue_date}
    }))
    
    for lending in overdue_lendings:
        tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
        if tool:
            days_overdue = (datetime.now() - lending['lent_at']).days
            tool_warnings.append({
                'name': tool['name'],
                'status': 'überfällig',
                'severity': 'warning',
                'description': f'Ausleihe seit {days_overdue} Tagen überfällig'
            })
    
    # Warnungen für niedrigen Materialbestand
    consumable_warnings = []
    low_stock_consumables = list(mongodb.find('consumables', {
        'deleted': {'$ne': True},
        '$expr': {'$lte': ['$quantity', '$min_quantity']}
    }))
    
    for consumable in low_stock_consumables:
        consumable_warnings.append({
            'message': consumable['name'],
            'type': 'error',
            'icon': 'exclamation-triangle',
            'description': 'Kritischer Bestand'
        })
    
    # Materialverbrauch-Trend
    consumable_trend = get_consumable_trend()
    
    # Aktuelle Ausleihen
    current_lendings = []
    active_lendings = mongodb.find('lendings', {'returned_at': None})
    # NEU: Konvertiere alle lent_at zu datetime
    for lending in active_lendings:
        lent_at = lending.get('lent_at')
        if isinstance(lent_at, str):
            try:
                lending['lent_at'] = datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S')
            except Exception:
                lending['lent_at'] = datetime.min
        elif not isinstance(lent_at, datetime):
            lending['lent_at'] = datetime.min
    # Sortiere die Ausleihen nach Datum (neueste zuerst)
    active_lendings.sort(key=lambda x: x.get('lent_at', datetime.min), reverse=True)
    
    for lending in active_lendings:
        tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
        worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
        if tool and worker:
            current_lendings.append({
                **lending,
                'tool_name': tool['name'],
                'worker_name': f"{worker['firstname']} {worker['lastname']}",
                'lent_at': lending['lent_at']
            })
    
    # Letzte Materialentnahmen
    recent_consumable_usage = []
    recent_usages = mongodb.find('consumable_usages')
    # Sortiere und limitiere die Verwendungen
    recent_usages.sort(key=lambda x: x.get('used_at', datetime.min), reverse=True)
    recent_usages = recent_usages[:10]
    
    for usage in recent_usages:
        consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
        worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
        if consumable and worker:
            recent_consumable_usage.append({
                'consumable_name': consumable['name'],
                'quantity': usage['quantity'],
                'worker_name': f"{worker['firstname']} {worker['lastname']}",
                'used_at': usage['used_at']
            })
    
    # Bestandsprognose
    consumables_forecast = get_consumables_forecast()
    
    return render_template('admin/dashboard.html',
                         tool_stats=tool_stats,
                         consumable_stats=consumable_stats,
                         worker_stats=worker_stats,
                         tool_warnings=tool_warnings,
                         consumable_warnings=consumable_warnings,
                         consumable_trend=consumable_trend,
                         current_lendings=current_lendings,
                         recent_consumable_usage=recent_consumable_usage,
                         consumables_forecast=consumables_forecast)

def get_consumable_trend():
    """Hole die Top 5 Materialverbrauch der letzten 7 Tage"""
    try:
        # Hole die letzten 7 Tage
        seven_days_ago = datetime.now() - timedelta(days=6)
        
        # Top 5 Verbrauchsmaterialien der letzten 7 Tage
        top_consumables_pipeline = [
            {
                '$match': {
                    'used_at': {'$gte': seven_days_ago},
                    'quantity': {'$gt': 0}
                }
            },
            {
                '$lookup': {
                    'from': 'consumables',
                    'localField': 'consumable_barcode',
                    'foreignField': 'barcode',
                    'as': 'consumable'
                }
            },
            {
                '$unwind': '$consumable'
            },
            {
                '$group': {
                    '_id': '$consumable.name',
                    'total_quantity': {'$sum': '$quantity'}
                }
            },
            {'$sort': {'total_quantity': -1}},
            {'$limit': 5}
        ]
        
        top_consumables = list(mongodb.db.consumable_usages.aggregate(top_consumables_pipeline))
        
        # Tägliche Daten für die Top 5
        labels = []
        datasets = []
        
        # Generiere Datums-Labels für die letzten 7 Tage
        for i in range(7):
            date = datetime.now() - timedelta(days=6-i)
            labels.append(date.strftime('%Y-%m-%d'))
        
        # Für jedes Top-Verbrauchsmaterial
        for i, consumable in enumerate(top_consumables):
            consumable_name = consumable['_id']
            data = []
            
            # Für jeden Tag
            for j in range(7):
                date = datetime.now() - timedelta(days=6-j)
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Finde Verbrauch für diesen Tag
                daily_usage = mongodb.db.consumable_usages.aggregate([
                    {
                        '$match': {
                            'used_at': {'$gte': start_of_day, '$lte': end_of_day},
                            'quantity': {'$gt': 0}
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'consumables',
                            'localField': 'consumable_barcode',
                            'foreignField': 'barcode',
                            'as': 'consumable'
                        }
                    },
                    {
                        '$unwind': '$consumable'
                    },
                    {
                        '$match': {'consumable.name': consumable_name}
                    },
                    {
                        '$group': {
                            '_id': None,
                            'daily_quantity': {'$sum': '$quantity'}
                        }
                    }
                ])
                
                daily_result = list(daily_usage)
                data.append(daily_result[0]['daily_quantity'] if daily_result else 0)
            
            datasets.append({
                'label': consumable_name,
                'data': data,
                'fill': False,
                'borderColor': f'hsl({(i * 60) % 360}, 70%, 50%)',
                'tension': 0.1
            })
    
        return {
            'labels': labels,
            'datasets': datasets
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden des Materialverbrauch-Trends: {str(e)}")
        return {
            'labels': [],
            'datasets': []
        }

@bp.route('/manual-lending', methods=['GET', 'POST'])
@mitarbeiter_required
def manual_lending():
    """Manuelle Ausleihe/Rückgabe"""
    if request.method == 'POST':
        logger.info("POST-Anfrage für manuelle Ausleihe empfangen")
        
        try:
            # JSON-Daten verarbeiten
            data = request.get_json()
            if data is None:
                return jsonify({
                    'success': False,
                    'message': 'Keine gültigen JSON-Daten empfangen'
                }), 400
                
            logger.debug(f"JSON-Daten für manuelle Ausleihe: {data}")
            
            item_barcode = data.get('item_barcode')
            worker_barcode = data.get('worker_barcode')
            action = data.get('action')  # 'lend' oder 'return'
            quantity = data.get('quantity')
            if quantity is not None:
                quantity = int(quantity)
            
            if not item_barcode:
                return jsonify({
                    'success': False, 
                    'message': 'Artikel muss ausgewählt sein'
                }), 400
            
            if action == 'lend' and not worker_barcode:
                return jsonify({
                    'success': False, 
                    'message': 'Mitarbeiter muss ausgewählt sein'
                }), 400
            
            try:
                # Prüfe ob der Mitarbeiter existiert
                if worker_barcode:
                    worker = mongodb.find_one('workers', {'barcode': worker_barcode, 'deleted': {'$ne': True}})
                    if not worker:
                        return jsonify({
                            'success': False,
                            'message': 'Mitarbeiter nicht gefunden'
                        }), 404

                # Prüfe ob es ein Verbrauchsmaterial ist
                consumable = mongodb.find_one('consumables', {'barcode': item_barcode, 'deleted': {'$ne': True}})
                if consumable:  # Verbrauchsmaterial-Logik
                    if not quantity or quantity <= 0:
                        return jsonify({
                            'success': False,
                            'message': 'Ungültige Menge'
                        }), 400
                    if quantity > consumable['quantity']:
                        return jsonify({
                            'success': False,
                            'message': 'Nicht genügend Bestand'
                        }), 400
                    # Neue Verbrauchsmaterial-Ausgabe erstellen
                    usage_data = {
                        'consumable_barcode': item_barcode,
                        'worker_barcode': worker_barcode,
                        'quantity': quantity,
                        'used_at': datetime.now(),
                        'updated_at': datetime.now(),
                        'sync_status': 'pending'
                    }
                    mongodb.insert_one('consumable_usages', usage_data)
                    # Bestand aktualisieren
                    mongodb.update_one('consumables',
                        {'barcode': item_barcode},
                        {
                            '$inc': {'quantity': -quantity},
                            '$set': {
                                'updated_at': datetime.now(),
                                'sync_status': 'pending'
                            }
                        }
                    )
                    return jsonify({
                        'success': True,
                        'message': f'{quantity}x {consumable["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgegeben'
                    })

                # Werkzeug-Logik
                tool = mongodb.find_one('tools', {'barcode': item_barcode, 'deleted': {'$ne': True}})
                if not tool:
                    return jsonify({
                        'success': False,
                        'message': 'Werkzeug nicht gefunden'
                    }), 404
                # Prüfe aktuellen Status des Werkzeugs
                active_lending = mongodb.find_one('lendings', {
                    'tool_barcode': item_barcode,
                    'returned_at': None
                })
                current_status = 'ausgeliehen' if active_lending else tool.get('status', 'verfügbar')
                current_worker = None
                if active_lending:
                    current_worker = mongodb.find_one('workers', {'barcode': active_lending['worker_barcode']})
                if action == 'lend':
                    if current_status == 'ausgeliehen':
                        worker_name = f"{current_worker['firstname']} {current_worker['lastname']}" if current_worker else "unbekannt"
                        return jsonify({
                            'success': False,
                            'message': f'Dieses Werkzeug ist bereits an {worker_name} ausgeliehen'
                        }), 400
                    if current_status == 'defekt':
                        return jsonify({
                            'success': False,
                            'message': 'Dieses Werkzeug ist als defekt markiert'
                        }), 400
                    # Neue Ausleihe erstellen
                    lending_data = {
                        'tool_barcode': item_barcode,
                        'worker_barcode': worker_barcode,
                        'lent_at': datetime.now()
                    }
                    mongodb.insert_one('lendings', lending_data)
                    # Status des Werkzeugs aktualisieren
                    mongodb.update_one('tools',
                        {'barcode': item_barcode},
                        {
                            '$set': {
                                'status': 'ausgeliehen',
                                'modified_at': datetime.now(),
                                'sync_status': 'pending'
                            }
                        }
                    )
                    return jsonify({
                        'success': True,
                        'message': f'Werkzeug {tool["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgeliehen'
                    })
                elif action == 'return':
                    if current_status != 'ausgeliehen':
                        return jsonify({
                            'success': False,
                            'message': 'Dieses Werkzeug ist nicht ausgeliehen'
                        }), 400
                    # Wenn ein Mitarbeiter angegeben wurde, prüfe ob er berechtigt ist
                    if worker_barcode and active_lending and active_lending['worker_barcode'] != worker_barcode:
                        worker_name = f"{current_worker['firstname']} {current_worker['lastname']}" if current_worker else "unbekannt"
                        return jsonify({
                            'success': False,
                            'message': f'Dieses Werkzeug wurde von {worker_name} ausgeliehen'
                        }), 403
                    # Rückgabe verarbeiten
                    mongodb.update_one('lendings',
                        {'tool_barcode': item_barcode, 'returned_at': None},
                        {'$set': {'returned_at': datetime.now()}}
                    )
                    # Status des Werkzeugs aktualisieren
                    mongodb.update_one('tools',
                        {'barcode': item_barcode},
                        {
                            '$set': {
                                'status': 'verfügbar',
                                'modified_at': datetime.now(),
                                'sync_status': 'pending'
                            }
                        }
                    )
                    return jsonify({
                        'success': True,
                        'message': f'Werkzeug {tool["name"]} wurde zurückgegeben'
                    })
            except Exception as e:
                logger.error(f"Fehler bei der Ausleihe: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': f'Fehler: {str(e)}'
                }), 500
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der Anfrage: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Fehler beim Verarbeiten der Anfrage'
            }), 500
            
    # GET request - zeige das Formular
    try:
        # Hole alle verfügbaren Werkzeuge
        tools_pipeline = [
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
                    'current_status': {
                        '$cond': [
                            {'$gt': [{'$size': {'$filter': {'input': '$active_lendings', 'cond': {'$eq': ['$$this.returned_at', None]}}}}, 0]},
                            'ausgeliehen',
                            '$status'
                        ]
                    }
                }
            },
            {'$sort': {'name': 1}}
        ]
        
        tools = list(mongodb.aggregate('tools', tools_pipeline))
        
        # Hole alle Mitarbeiter
        workers = mongodb.find('workers', {'deleted': {'$ne': True}}, sort=[('firstname', 1)])
        
        # Verbrauchsmaterialien laden
        consumables = mongodb.find('consumables', {'deleted': {'$ne': True}}, sort=[('name', 1)])

        # Hole aktuelle Ausleihen
        current_lendings = []
        
        # Aktuelle Werkzeug-Ausleihen
        active_tool_lendings = mongodb.find('lendings', {'returned_at': None})
        for lending in active_tool_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
            
            if tool and worker:
                current_lendings.append({
                    'item_name': tool['name'],
                    'item_barcode': tool['barcode'],
                    'worker_name': f"{worker['firstname']} {worker['lastname']}",
                    'worker_barcode': worker['barcode'],
                    'action_date': lending['lent_at'],
                    'category': 'Werkzeuge',
                    'amount': None
                })

        # Aktuelle Verbrauchsmaterial-Ausgaben (letzte 30 Tage)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_consumable_usages = mongodb.find('consumable_usages', {
            'used_at': {'$gte': thirty_days_ago},
            'quantity': {'$gt': 0}  # Nur Ausgaben, nicht Entnahmen
        })
        
        for usage in recent_consumable_usages:
            consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
            worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
            
            if consumable and worker:
                current_lendings.append({
                    'item_name': consumable['name'],
                    'item_barcode': consumable['barcode'],
                    'worker_name': f"{worker['firstname']} {worker['lastname']}",
                    'worker_barcode': worker['barcode'],
                    'action_date': usage['used_at'],
                    'category': 'Verbrauchsmaterial',
                    'amount': usage['quantity']
                })

        # Sortiere nach Datum (neueste zuerst)
        def safe_date_key(lending):
            action_date = lending.get('action_date')
            if isinstance(action_date, str):
                try:
                    return datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    return datetime.min
            elif isinstance(action_date, datetime):
                return action_date
            else:
                return datetime.min
        
        current_lendings.sort(key=safe_date_key, reverse=True)

        return render_template('admin/manual_lending.html', 
                              tools=tools,
                              workers=workers,
                              consumables=consumables,
                              current_lendings=current_lendings)
    except Exception as e:
        print(f"Fehler beim Laden der Daten: {e}")
        flash('Fehler beim Laden der Daten', 'error')
        return render_template('admin/manual_lending.html', 
                              tools=[], 
                              workers=[], 
                              consumables=[],
                              current_lendings=[])

@bp.route('/trash')
@mitarbeiter_required
def trash():
    """Zeigt den Papierkorb mit gelöschten Einträgen an"""
    try:
        # Gelöschte Werkzeuge
        tools = mongodb.find('tools', {'deleted': True}, sort=[('deleted_at', -1)])
        
        # Gelöschte Verbrauchsmaterialien
        consumables = mongodb.find('consumables', {'deleted': True}, sort=[('deleted_at', -1)])
        
        # Gelöschte Mitarbeiter
        workers = mongodb.find('workers', {'deleted': True}, sort=[('deleted_at', -1)])
        
        return render_template('admin/trash.html',
                           tools=tools,
                           consumables=consumables,
                           workers=workers)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Papierkorbs: {str(e)}", exc_info=True)
        flash('Fehler beim Laden des Papierkorbs', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/trash/restore/<type>/<barcode>', methods=['POST'])
@mitarbeiter_required
def restore_item(type, barcode):
    """Stellt einen gelöschten Eintrag wieder her"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)
        
        if type == 'tool':
            # Prüfe ob das Werkzeug existiert
            tool = mongodb.find_one('tools', {'barcode': decoded_barcode, 'deleted': True})
            
            if not tool:
                return jsonify({
                    'success': False,
                    'message': 'Werkzeug nicht gefunden'
                }), 404
                
            # Stelle das Werkzeug wieder her
            mongodb.update_one('tools', 
                             {'barcode': decoded_barcode}, 
                             {'$set': {'deleted': False, 'deleted_at': None}})
            
        elif type == 'consumable':
            # Prüfe ob das Verbrauchsmaterial existiert
            consumable = mongodb.find_one('consumables', {'barcode': decoded_barcode, 'deleted': True})
            
            if not consumable:
                return jsonify({
                    'success': False,
                    'message': 'Verbrauchsmaterial nicht gefunden'
                }), 404
                
            # Stelle das Verbrauchsmaterial wieder her
            mongodb.update_one('consumables', 
                             {'barcode': decoded_barcode}, 
                             {'$set': {'deleted': False, 'deleted_at': None}})
            
        elif type == 'worker':
            # Prüfe ob der Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': decoded_barcode, 'deleted': True})
            
            if not worker:
                return jsonify({
                    'success': False,
                    'message': 'Mitarbeiter nicht gefunden'
                }), 404
                
            # Stelle den Mitarbeiter wieder her
            mongodb.update_one('workers', 
                             {'barcode': decoded_barcode}, 
                             {'$set': {'deleted': False, 'deleted_at': None}})
        else:
            return jsonify({
                'success': False,
                'message': 'Ungültiger Typ'
            }), 400
            
        return jsonify({
            'success': True,
            'message': 'Eintrag wurde wiederhergestellt'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen des Eintrags: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Wiederherstellen: {str(e)}'
        }), 500

@bp.route('/tools/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_tool_soft_json():
    """Werkzeug soft löschen (markieren als gelöscht) - Barcode aus JSON-Body"""
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400
            
        barcode = data['barcode'].strip()  # Barcode bereinigen
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode zu lang (max. 50 Zeichen)'}), 400
        
        # Prüfe ob das Werkzeug existiert
        tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
            
        # Prüfe ob das Werkzeug ausgeliehen ist
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': barcode, 
            'returned_at': None
        })
        
        if active_lending:
            return jsonify({
                'success': False,
                'message': 'Werkzeug ist noch ausgeliehen und kann nicht gelöscht werden'
            }), 400
            
        # Führe das Soft-Delete durch
        mongodb.update_one('tools', {'barcode': barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Werkzeug wurde erfolgreich gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/tools/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_tool_soft(barcode):
    """Werkzeug soft löschen (markieren als gelöscht) - Barcode aus URL (Legacy)"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)
        
        # Prüfe ob das Werkzeug existiert
        tool = mongodb.find_one('tools', {'barcode': decoded_barcode, 'deleted': {'$ne': True}})
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
            
        # Prüfe ob das Werkzeug ausgeliehen ist
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': decoded_barcode, 
            'returned_at': None
        })
        
        if active_lending:
            return jsonify({
                'success': False,
                'message': 'Werkzeug ist noch ausgeliehen und kann nicht gelöscht werden'
            }), 400
            
        # Führe das Soft-Delete durch
        mongodb.update_one('tools', {'barcode': decoded_barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Werkzeug wurde erfolgreich gelöscht'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/tools/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_tool_permanent(barcode):
    """Werkzeug endgültig löschen"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)
        
        # Prüfe ob das Werkzeug existiert und gelöscht ist
        tool = mongodb.find_one('tools', {'barcode': decoded_barcode, 'deleted': True})
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden oder nicht gelöscht'
            }), 404
            
        # Lösche das Werkzeug endgültig
        mongodb.delete_one('tools', {'barcode': decoded_barcode})
        
        return jsonify({
            'success': True,
            'message': 'Werkzeug wurde endgültig gelöscht'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim endgültigen Löschen des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/consumables/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_consumable_soft():
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400
            
        barcode = data['barcode'].strip()  # Barcode bereinigen
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode zu lang (max. 50 Zeichen)'}), 400
            
        # Prüfe ob das Verbrauchsmaterial existiert
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404
            
        # Führe das Soft-Delete durch
        mongodb.update_one('consumables', {'barcode': barcode}, {
            '$set': {
                'deleted': True, 
                'deleted_at': datetime.now()
            }
        })
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial erfolgreich gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/consumables/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_consumable_permanent(barcode):
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)
        
        # Prüfe ob das Verbrauchsmaterial existiert und gelöscht ist
        consumable = mongodb.find_one('consumables', {'barcode': decoded_barcode, 'deleted': True})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden oder nicht gelöscht'}), 404
            
        # Führe das permanente Löschen durch
        mongodb.delete_one('consumables', {'barcode': decoded_barcode})
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial permanent gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Verbrauchsmaterials: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/workers/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_soft_json():
    """Mitarbeiter soft löschen (markieren als gelöscht) - Barcode aus JSON-Body"""
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400
            
        barcode = data['barcode'].strip()  # Barcode bereinigen
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode zu lang (max. 50 Zeichen)'}), 400
        
        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404
            
        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings_count = mongodb.count_documents('lendings', {
            'worker_barcode': barcode, 
            'returned_at': None
        })
        
        if active_lendings_count > 0:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter hat noch aktive Ausleihen'
            }), 400
            
        # Führe das Soft-Delete durch
        mongodb.update_one('workers', {'barcode': barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Mitarbeiter wurde erfolgreich gelöscht'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Mitarbeiters: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/workers/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_soft(barcode):
    """Mitarbeiter soft löschen (markieren als gelöscht) - Barcode aus URL (Legacy)"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)
        
        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': decoded_barcode, 'deleted': {'$ne': True}})
        
        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404
            
        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings_count = mongodb.count_documents('lendings', {
            'worker_barcode': decoded_barcode, 
            'returned_at': None
        })
        
        if active_lendings_count > 0:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter hat noch aktive Ausleihen'
            }), 400
            
        # Führe das Soft-Delete durch
        mongodb.update_one('workers', {'barcode': decoded_barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })
        
        return jsonify({
            'success': True,
            'message': 'Mitarbeiter wurde erfolgreich gelöscht'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Mitarbeiters: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/workers/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_permanent(barcode):
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)
        
        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': decoded_barcode, 'deleted': {'$ne': True}})
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeiter nicht gefunden'}), 404
            
        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings_count = mongodb.count_documents('lendings', {
            'worker_barcode': decoded_barcode, 
            'returned_at': None
        })
        if active_lendings_count > 0:
            return jsonify({'success': False, 'message': 'Mitarbeiter hat noch aktive Ausleihen'}), 400
            
        # Führe das permanente Löschen durch
        mongodb.delete_one('workers', {'barcode': decoded_barcode})
        return jsonify({'success': True, 'message': 'Mitarbeiter permanent gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Mitarbeiters: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/tickets/<ticket_id>')
@login_required
@mitarbeiter_required
def ticket_detail(ticket_id):
    """Zeigt die Details eines Tickets für Administratoren."""
    ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
    
    if not ticket:
        return render_template('404.html'), 404
    
    # Füge id-Feld hinzu (für Template-Kompatibilität)
    ticket['id'] = str(ticket['_id'])
        
    # Konvertiere alle Datumsfelder zu datetime-Objekten
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
        
    # Hole die Notizen für das Ticket
    notes = mongodb.find('ticket_notes', {'ticket_id': ObjectId(ticket_id)})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': ObjectId(ticket_id)})
    # Formatiere die Nachrichten für das Template
    formatted_messages = []
    for msg in messages:
        formatted_msg = dict(msg)
        # Konvertiere created_at zu String-Format
        if isinstance(formatted_msg.get('created_at'), datetime):
            formatted_msg['created_at'] = formatted_msg['created_at'].strftime('%d.%m.%Y %H:%M')
        # Setze is_admin Flag basierend auf dem Sender
        formatted_msg['is_admin'] = formatted_msg.get('sender') == current_user.username
        formatted_messages.append(formatted_msg)

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ObjectId(ticket_id)})
    logging.info(f"DEBUG: auftrag_details für Ticket {ticket_id}: {auftrag_details}")
    
    # Hole die Materialliste
    material_list = mongodb.find('auftrag_material', {'ticket_id': ObjectId(ticket_id)})

    # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
    users = mongodb.find('users', {'is_active': True})
    users = [dict(user) for user in users]

    # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
    assigned_users = mongodb.find('ticket_assignments', {'ticket_id': ObjectId(ticket_id)})

    # Hole alle Kategorien aus der settings Collection
    categories = get_ticket_categories_from_settings()

    return render_template('admin/ticket_detail.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=formatted_messages,
                         users=users,
                         workers=users,  # Template erwartet 'workers'
                         assigned_users=assigned_users,
                         auftrag_details=auftrag_details,
                         material_list=material_list,
                         categories=categories,
                         now=datetime.now())

@bp.route('/tickets/<ticket_id>/message', methods=['POST'])
@login_required
@admin_required
def add_ticket_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu."""
    try:
        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Hole die Nachricht aus dem Request
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Ungültiges Anfrageformat. JSON erwartet.'
            }), 400

        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({
                'success': False,
                'message': 'Nachricht darf nicht leer sein'
            }), 400

        # Füge die Nachricht zur Datenbank hinzu
        message_data = {
            'ticket_id': ObjectId(ticket_id),
            'message': message,
            'sender': current_user.username,
            'created_at': datetime.now()
        }
        
        result = mongodb.insert_one('ticket_messages', message_data)

        return jsonify({
            'success': True,
            'message': {
                'sender': current_user.username,
                'text': message,
                'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Nachricht: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Speichern der Nachricht: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/note', methods=['POST'])
@login_required
@admin_required
def add_ticket_note(ticket_id):
    """Fügt eine neue Notiz zu einem Ticket hinzu."""
    try:
        logger.debug(f"Notiz-Anfrage für Ticket {ticket_id} erhalten")
        # Hole das Ticket
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
        
        if not ticket:
            logger.warning(f"Ticket {ticket_id} nicht gefunden")
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Hole die Notiz
        if not request.is_json:
            logger.warning("Ungültiges Anfrageformat. JSON erwartet.")
            return jsonify({
                'success': False,
                'message': 'Ungültiges Anfrageformat. JSON erwartet.'
            }), 400

        data = request.get_json()
        note = data.get('note')
        
        if not note or not note.strip():
            logger.warning("Notiz ist leer")
            return jsonify({
                'success': False,
                'message': 'Notiz ist erforderlich'
            }), 400

        logger.debug(f"Notiz hinzufügen: {note}")
        # Füge die Notiz hinzu
        note_data = {
            'ticket_id': ObjectId(ticket_id),
            'note': note.strip(),
            'created_by': current_user.username,
            'created_at': datetime.now()
        }
        
        result = mongodb.insert_one('ticket_notes', note_data)
        
        # Aktualisiere das updated_at Feld des Tickets
        mongodb.update_one('tickets', {'_id': ObjectId(ticket_id)}, {'$set': {'updated_at': datetime.now()}})

        return jsonify({
            'success': True,
            'message': 'Notiz wurde gespeichert',
            'note': {
                'id': str(result),
                'note': note.strip(),
                'created_by': current_user.username,
                'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Notiz: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/tickets/<ticket_id>/update', methods=['POST'])
@login_required
@admin_required
def update_ticket(ticket_id):
    """Aktualisiert ein Ticket"""
    try:
        data = request.get_json()
        logging.info(f"Empfangene Daten für Ticket {ticket_id}: {data}")
        
        # Verarbeite ausgeführte Arbeiten
        arbeit_list = data.get('arbeit_list', [])
        ausgefuehrte_arbeiten = '\n'.join([
            f"{arbeit['arbeit']}|{arbeit['arbeitsstunden']}|{arbeit['leistungskategorie']}"
            for arbeit in arbeit_list
        ])
        logging.info(f"Verarbeitete ausgeführte Arbeiten: {ausgefuehrte_arbeiten}")
        
        # Bereite die Auftragsdetails vor
        auftrag_details = {
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': data.get('auftraggeber_typ') == 'intern',
            'auftraggeber_extern': data.get('auftraggeber_typ') == 'extern',
            'auftraggeber_name': data.get('auftraggeber_name', ''),
            'kontakt': data.get('kontakt', ''),
            'auftragsbeschreibung': data.get('auftragsbeschreibung', ''),
            'ausgefuehrte_arbeiten': ausgefuehrte_arbeiten,
            'arbeitsstunden': data.get('arbeitsstunden', ''),
            'leistungskategorie': data.get('leistungskategorie', ''),
            'fertigstellungstermin': data.get('fertigstellungstermin', ''),
            'gesamtsumme': data.get('gesamtsumme', 0)
        }
        
        # Aktualisiere die Auftragsdetails
        if not mongodb.update_one('auftrag_details', {'ticket_id': ObjectId(ticket_id)}, {'$set': auftrag_details}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Auftragsdetails'})
        
        # Aktualisiere die Materialliste
        material_list = data.get('material_list', [])
        if not mongodb.update_many('auftrag_material', {'ticket_id': ObjectId(ticket_id)}, {'$set': {'menge': m['menge'], 'einzelpreis': m['einzelpreis']} for m in material_list}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Materialliste'})
        
        return jsonify({'success': True})
        
    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets {ticket_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/tickets/<id>/export')
@login_required
@admin_required
def export_ticket(id):
    """Exportiert das Ticket als ausgefülltes Word-Dokument."""
    try:
        # Prüfe ob die ID gültig ist
        try:
            ticket_id = ObjectId(id)
        except Exception as e:
            logging.error(f"Ungültige Ticket-ID: {id}")
            flash('Ungültige Ticket-ID.', 'error')
            return redirect(url_for('admin.tickets'))
        
        ticket = mongodb.find_one('tickets', {'_id': ticket_id})
        if not ticket:
            logging.error(f"Ticket nicht gefunden: {id}")
            flash('Ticket nicht gefunden.', 'error')
            return redirect(url_for('admin.tickets'))
        
        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id}) or {}
        material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id})) or []

        # --- Auftragnehmer (Vorname Nachname) ---
        auftragnehmer_user = None
        if ticket.get('assigned_to'):
            auftragnehmer_user = MongoDBUser.get_by_username(ticket['assigned_to'])
        if auftragnehmer_user:
            auftragnehmer_name = f"{auftragnehmer_user.firstname or ''} {auftragnehmer_user.lastname or ''}".strip()
        else:
            auftragnehmer_name = ''

        # --- Checkboxen für Auftraggeber intern/extern ---
        intern_checkbox = '☒' if auftrag_details.get('auftraggeber_intern') else '☐'
        extern_checkbox = '☒' if auftrag_details.get('auftraggeber_extern') else '☐'

        # --- Ausgeführte Arbeiten (bis zu 5) ---
        arbeiten_liste = auftrag_details.get('ausgefuehrte_arbeiten', '')
        arbeiten_zeilen = []
        if arbeiten_liste:
            for zeile in arbeiten_liste.split('\n'):
                if not zeile.strip():
                    continue
                teile = [t.strip() for t in zeile.split('|')]
                eintrag = {
                    'arbeiten': teile[0] if len(teile) > 0 else '',
                    'arbeitsstunden': teile[1] if len(teile) > 1 else '',
                    'leistungskategorie': teile[2] if len(teile) > 2 else ''
                }
                arbeiten_zeilen.append(eintrag)
        # Fülle auf 5 Zeilen auf
        while len(arbeiten_zeilen) < 5:
            arbeiten_zeilen.append({'arbeiten':'','arbeitsstunden':'','leistungskategorie':''})

        # Materialdaten aufbereiten
        material_rows = []
        summe_material = 0
        for m in material_list:
            menge = float(m.get('menge') or 0)
            einzelpreis = float(m.get('einzelpreis') or 0)
            gesamtpreis = menge * einzelpreis
            summe_material += gesamtpreis
            material_rows.append({
                'material': m.get('material', '') or '',
                'materialmenge': f"{menge:.2f}".replace('.', ',') if menge else '',
                'materialpreis': f"{einzelpreis:.2f}".replace('.', ',') if einzelpreis else '',
                'materialpreisges': f"{gesamtpreis:.2f}".replace('.', ',') if gesamtpreis else ''
            })
        while len(material_rows) < 5:
            material_rows.append({'material':'','materialmenge':'','materialpreis':'','materialpreisges':''})

        arbeitspausch = 0
        ubertrag = 0
        zwischensumme = summe_material + arbeitspausch + ubertrag
        mwst = zwischensumme * 0.07
        gesamtsumme = zwischensumme + mwst

        # --- Kontext für docxtpl bauen ---
        context = {
            'auftragnehmer': auftragnehmer_name,
            'auftragnummer': ticket.get('ticket_number', id),
            'datum': datetime.now().strftime('%d.%m.%Y'),
            'internchk': '☒' if auftrag_details.get('auftraggeber_intern') else '☐',
            'externchk': '☒' if auftrag_details.get('auftraggeber_extern') else '☐',
            'auftraggebername': auftrag_details.get('auftraggeber_name', ''),
            'auftraggebermail': auftrag_details.get('kontakt', ''),
            'bereich': auftrag_details.get('bereich', ''),
            'auftragsbeschreibung': auftrag_details.get('auftragsbeschreibung', ''),
            'duedate': auftrag_details.get('fertigstellungstermin', ''),
            'gesamtsumme': f"{gesamtsumme:.2f}".replace('.', ','),
            'matsum': f"{summe_material:.2f}".replace('.', ','),
            'ubertrag': f"{ubertrag:.2f}".replace('.', ','),
            'arpausch': f"{arbeitspausch:.2f}".replace('.', ','),
            'zwsum': f"{zwischensumme:.2f}".replace('.', ','),
            'mwst': f"{mwst:.2f}".replace('.', ','),
            'arbeitenblock': '\n'.join([arbeit['arbeiten'] for arbeit in arbeiten_zeilen]),
            'stundenblock': '\n'.join([arbeit['arbeitsstunden'] for arbeit in arbeiten_zeilen]),
            'kategorieblock': '\n'.join([arbeit['leistungskategorie'] for arbeit in arbeiten_zeilen]),
            'materialblock': '\n'.join([material['material'] for material in material_rows]),
            'mengenblock': '\n'.join([material['materialmenge'] for material in material_rows]),
            'preisblock': '\n'.join([material['materialpreis'] for material in material_rows]),
            'gesamtblock': '\n'.join([material['materialpreisges'] for material in material_rows])
        }

        # --- Word-Dokument generieren ---
        logging.info(f"Starte Admin-Export für Ticket {id}")
        
        # Lade das Template
        template_path = os.path.join(current_app.root_path, 'static', 'word', 'btzauftrag.docx')
        logging.info(f"Template-Pfad: {template_path}")
        
        if not os.path.exists(template_path):
            logging.error(f"Template-Datei nicht gefunden: {template_path}")
            flash('Word-Template nicht gefunden.', 'error')
            return redirect(url_for('admin.ticket_detail', ticket_id=id))
        
        doc = DocxTemplate(template_path)
        logging.info("Template erfolgreich geladen")
        
        # Rendere das Dokument
        logging.info(f"Rendere Dokument mit Kontext: {context}")
        doc.render(context)
        logging.info("Dokument erfolgreich gerendert")
        
        # Erstelle das uploads-Verzeichnis falls es nicht existiert
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Speichere das generierte Dokument
        ticket_number = ticket.get('ticket_number', id)
        output_path = os.path.join(uploads_dir, f'ticket_{ticket_number}_export.docx')
        
        logging.info(f"Speichere Dokument unter: {output_path}")
        doc.save(output_path)
        logging.info("Dokument erfolgreich gespeichert")
        
        logging.info(f"Word-Dokument erfolgreich generiert: {output_path}")
        
        # Sende das Dokument
        return send_file(output_path, as_attachment=True, download_name=f'ticket_{ticket_number}_export.docx')
        
    except Exception as e:
        logging.error(f"Fehler beim Generieren des Word-Dokuments: {str(e)}", exc_info=True)
        flash(f'Fehler beim Generieren des Dokuments: {str(e)}', 'error')
        return redirect(url_for('admin.ticket_detail', ticket_id=id))

@bp.route('/tickets/<ticket_id>/update-details', methods=['POST'])
@login_required
@admin_required
def update_ticket_details(ticket_id):
    """Aktualisiert die Details eines Tickets."""
    try:
        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Hole die Daten aus dem Request
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Ungültiges Anfrageformat. JSON erwartet.'
            }), 400

        data = request.get_json()
        
        # Auftragsdetails aktualisieren
        auftrag_details = {
            'ticket_id': ObjectId(ticket_id),
            'auftrag_an': data.get('auftrag_an', ''),
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': data.get('auftraggeber_typ') == 'intern',
            'auftraggeber_extern': data.get('auftraggeber_typ') == 'extern',
            'beschreibung': data.get('beschreibung', ''),
            'prioritaet': data.get('prioritaet', 'normal'),
            'deadline': data.get('deadline'),
            'updated_at': datetime.now()
        }
        
        if not mongodb.update_one('auftrag_details', {'ticket_id': ObjectId(ticket_id)}, {'$set': auftrag_details}):
            mongodb.insert_one('auftrag_details', auftrag_details)
        
        # Materialliste aktualisieren
        material_list = data.get('material_list', [])
        if material_list:
            # Lösche alte Materialeinträge
            mongodb.delete_many('auftrag_material', {'ticket_id': ObjectId(ticket_id)})
            
            # Füge neue Materialeinträge hinzu
            for material in material_list:
                material['ticket_id'] = ObjectId(ticket_id)
                material['created_at'] = datetime.now()
                mongodb.insert_one('auftrag_material', material)
        
        # Ticket selbst aktualisieren
        ticket_update = {
            'title': data.get('title', ticket.get('title', '')),
            'description': data.get('description', ticket.get('description', '')),
            'priority': data.get('prioritaet', ticket.get('priority', 'normal')),
            'updated_at': datetime.now()
        }
        
        if not mongodb.update_one('tickets', {'_id': ObjectId(ticket_id)}, {'$set': ticket_update}):
            return jsonify({
                'success': False,
                'message': 'Fehler beim Aktualisieren des Tickets'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Ticket-Details erfolgreich aktualisiert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Ticket-Details: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Interner Fehler: {str(e)}'
        }), 500

def create_mongodb_backup():
    """Erstellt ein MongoDB-Backup"""
    try:
        from app.utils.backup_manager import BackupManager
        
        backup_manager = BackupManager()
        backup_filename = backup_manager.create_backup()
        
        if backup_filename:
            logger.info(f"MongoDB-Backup erfolgreich erstellt: {backup_filename}")
            return True, backup_filename
        else:
            logger.error("Fehler beim Erstellen des MongoDB-Backups")
            return False, "Fehler beim Erstellen des Backups"
            
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des MongoDB-Backups: {str(e)}")
        return False, f"Fehler beim Erstellen des Backups: {str(e)}"

@bp.route('/tickets')
@login_required
@mitarbeiter_required
def tickets():
    """Zeigt die Ticket-Verwaltungsseite an."""
    # Hole alle Tickets aus der Datenbank
    tickets = list(mongodb.db.tickets.find({}).sort('created_at', -1))
    
    # Formatiere die Tickets für die Anzeige
    for ticket in tickets:
        ticket['id'] = str(ticket['_id'])
        ticket['created_at'] = ticket['created_at'].strftime('%d.%m.%Y %H:%M')
        if 'last_update' in ticket:
            ticket['last_update'] = ticket['last_update'].strftime('%d.%m.%Y %H:%M')
    
    # Hole alle Kategorien
    categories = get_ticket_categories_from_settings()
    
    return render_template('admin/tickets.html', 
                         tickets=tickets,
                         categories=categories,
                         title="Ticket-Verwaltung")

@bp.route('/manage_users')
@mitarbeiter_required
def manage_users():
    """Benutzerverwaltung"""
    try:
        users = mongodb.find('users', {}, sort=[('username', 1)])
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Benutzer: {e}")
        flash('Fehler beim Laden der Benutzer', 'error')
        return render_template('admin/users.html', users=[])

@bp.route('/add_user', methods=['GET', 'POST'])
@mitarbeiter_required
def add_user():
    if request.method == 'POST':
        role = request.form.get('role', '').strip()
        if current_user.role != 'admin' and role == 'admin':
            flash('Sie dürfen keine Admin-Benutzer anlegen.', 'error')
            return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender'], form_data=request.form)
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        firstname = request.form.get('firstname', '').strip()
        lastname = request.form.get('lastname', '').strip()
        role = request.form.get('role', '').strip()
        
        # Validierung der Pflichtfelder (Passwort ist jetzt optional)
        if not username or not firstname or not lastname or not role:
            flash('Alle Pflichtfelder müssen ausgefüllt werden', 'error')
            return render_template('admin/user_form.html', 
                                 roles=['admin', 'mitarbeiter', 'anwender'],
                                 form_data=request.form)
        
        # Automatische Passwort-Generierung wenn keines eingegeben wurde
        if not password:
            import secrets
            import string
            # Mindestens 1 von jeder Kategorie sicherstellen
            password = (
                secrets.choice(string.ascii_uppercase) +  # 1 Großbuchstabe
                secrets.choice(string.ascii_lowercase) +  # 1 Kleinbuchstabe
                secrets.choice(string.digits) +           # 1 Ziffer
                secrets.choice("!@#$%^&*") +              # 1 Sonderzeichen
                ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(8))  # 8 weitere zufällige Zeichen
            )
            # Passwort mischen
            password_list = list(password)
            secrets.SystemRandom().shuffle(password_list)
            password = ''.join(password_list)
            password_confirm = password  # Für die Validierung
        else:
            # Wenn Passwort eingegeben wurde, prüfe ob es bestätigt wurde
            if password != password_confirm:
                flash('Passwörter stimmen nicht überein', 'error')
                return render_template('admin/user_form.html', 
                                     roles=['admin', 'mitarbeiter', 'anwender'],
                                     form_data=request.form)
        
        # Prüfe ob Benutzername bereits existiert
        existing_user = mongodb.find_one('users', {'username': username})
        if existing_user:
            flash('Benutzername existiert bereits', 'error')
            return render_template('admin/user_form.html', 
                                 roles=['admin', 'mitarbeiter', 'anwender'],
                                 form_data=request.form)
        
        # Benutzer erstellen
        user_data = {
            'username': username,
            'email': email if email else None,
            'password_hash': generate_password_hash(password),
            'firstname': firstname,
            'lastname': lastname,
            'role': role,
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        mongodb.insert_one('users', user_data)
        
        # E-Mail mit Passwort versenden (falls E-Mail vorhanden)
        if email:
            try:
                from app.utils.email_utils import send_password_mail
                send_password_mail(email, password)
                flash(f'Benutzer "{username}" erfolgreich erstellt. Passwort wurde per E-Mail an {email} gesendet.', 'success')
            except Exception as e:
                logger.error(f"Fehler beim Versenden der E-Mail: {e}")
                flash(f'Benutzer "{username}" erfolgreich erstellt. E-Mail konnte nicht versendet werden.', 'warning')
        else:
            flash(f'Benutzer "{username}" erfolgreich erstellt. Passwort: {password}', 'success')
        
        return redirect(url_for('admin.manage_users'))
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Benutzers: {e}")
        flash('Fehler beim Erstellen des Benutzers', 'error')
        return render_template('admin/user_form.html', 
                             roles=['admin', 'mitarbeiter', 'anwender'],
                             form_data=request.form)
    
    return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender'])

@bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@mitarbeiter_required
def edit_user(user_id):
    user = mongodb.find_one('users', {'_id': ObjectId(user_id)})
    if not user:
        flash('Benutzer nicht gefunden', 'error')
        return redirect(url_for('admin.manage_users'))
    if current_user.role != 'admin' and user.get('role') == 'admin':
        flash('Sie dürfen keine Admin-Benutzer bearbeiten.', 'error')
        return redirect(url_for('admin.manage_users'))
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        firstname = request.form.get('firstname', '').strip()
        lastname = request.form.get('lastname', '').strip()
        role = request.form.get('role', '').strip()
        
        # Validierung
        if not username or not firstname or not lastname or not role:
            flash('Alle Pflichtfelder müssen ausgefüllt werden', 'error')
            return render_template('admin/user_form.html', 
                                 user=user,
                                 roles=['admin', 'mitarbeiter', 'anwender'])
        
        # Prüfe ob Passwort geändert werden soll
        if password:
            if password != password_confirm:
                flash('Passwörter stimmen nicht überein', 'error')
                return render_template('admin/user_form.html', 
                                     user=user,
                                     roles=['admin', 'mitarbeiter', 'anwender'])
            password_hash = generate_password_hash(password)
        else:
            password_hash = user.get('password_hash')
        
        # Prüfe ob Benutzername bereits existiert (außer bei diesem Benutzer)
        existing_user = mongodb.find_one('users', {
            'username': username,
            '_id': {'$ne': ObjectId(user_id)}
        })
        if existing_user:
            flash('Benutzername existiert bereits', 'error')
            return render_template('admin/user_form.html', 
                                 user=user,
                                 roles=['admin', 'mitarbeiter', 'anwender'])
        
        # Benutzer aktualisieren
        update_data = {
            'username': username,
            'email': email if email else None,
            'password_hash': password_hash,
            'firstname': firstname,
            'lastname': lastname,
            'role': role,
            'updated_at': datetime.now()
        }
        
        mongodb.update_one('users', 
                         {'_id': ObjectId(user_id)}, 
                         {'$set': update_data})
        
        flash(f'Benutzer "{username}" erfolgreich aktualisiert', 'success')
        return redirect(url_for('admin.manage_users'))
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Benutzers: {e}")
        flash('Fehler beim Aktualisieren des Benutzers', 'error')
        return render_template('admin/user_form.html', 
                             user=user,
                             roles=['admin', 'mitarbeiter', 'anwender'])
    
    return render_template('admin/user_form.html', 
                         user=user,
                         roles=['admin', 'mitarbeiter', 'anwender'])

@bp.route('/notices')
@admin_required
def notices():
    """Notizen-Übersicht"""
    notices = mongodb.find('homepage_notices', {})
    return render_template('admin/notices.html', notices=notices)

@bp.route('/create_notice', methods=['GET', 'POST'])
@admin_required
def create_notice():
    """Neue Notiz erstellen"""
    if request.method == 'POST':
        flash('Notiz-Funktion noch nicht implementiert', 'warning')
        return redirect(url_for('admin.notices'))
    return render_template('admin/notice_form.html')

@bp.route('/edit_notice/<id>', methods=['GET', 'POST'])
@admin_required
def edit_notice(id):
    """Notiz bearbeiten"""
    if request.method == 'POST':
        flash('Notiz-Funktion noch nicht implementiert', 'warning')
        return redirect(url_for('admin.notices'))
    notice = mongodb.find_one('homepage_notices', {'_id': ObjectId(id)})
    return render_template('admin/notice_form.html', notice=notice)

@bp.route('/delete_notice/<id>', methods=['POST'])
@admin_required
def delete_notice(id):
    """Löscht einen Hinweis"""
    try:
        # Konvertiere String-ID zu ObjectId
        object_id = ObjectId(id)
        
        # Lösche den Hinweis
        result = mongodb.delete_one('homepage_notices', {'_id': object_id})
        
        if result:
            flash('Hinweis erfolgreich gelöscht', 'success')
        else:
            flash('Hinweis nicht gefunden', 'error')
            
        return redirect(url_for('admin.notices'))
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Hinweises: {str(e)}")
        flash('Fehler beim Löschen des Hinweises', 'error')
        return redirect(url_for('admin.notices'))

@bp.route('/upload_logo', methods=['POST'])
@admin_required
def upload_logo():
    """Logo hochladen"""
    flash('Logo-Upload-Funktion noch nicht implementiert', 'warning')
    return redirect(url_for('admin.system'))

@bp.route('/delete-logo/<filename>', methods=['POST'])
@admin_required
def delete_logo(filename):
    """Logo löschen"""
    try:
        import os
        logo_path = os.path.join(current_app.root_path, 'static', 'uploads', 'logos', filename)
        if os.path.exists(logo_path):
            os.remove(logo_path)
            return jsonify({'success': True, 'message': 'Logo erfolgreich gelöscht'})
        else:
            return jsonify({'success': False, 'message': 'Logo nicht gefunden'}), 404
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Logos: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen des Logos'}), 500

@bp.route('/add_ticket_category', methods=['POST'])
@admin_required
def add_ticket_category():
    """Fügt eine neue Ticket-Kategorie hinzu"""
    try:
        name = request.form.get('category')
        if not name:
            flash('Bitte geben Sie einen Namen ein.', 'error')
            return redirect(url_for('admin.tickets'))

        # Prüfen ob Ticket-Kategorie bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
        if settings and name in settings.get('value', []):
            flash('Diese Ticket-Kategorie existiert bereits.', 'error')
            return redirect(url_for('admin.tickets'))

        # Ticket-Kategorie zur Liste hinzufügen
        if settings:
            mongodb.update_one_array(
                {'key': 'ticket_categories'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.insert_one('settings', {
                'key': 'ticket_categories',
                'value': [name]
            })

        flash('Ticket-Kategorie erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('admin.tickets'))
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('admin.tickets'))

@bp.route('/delete_ticket_category/<category>', methods=['POST'])
@admin_required
def delete_ticket_category(category):
    """Löscht eine Ticket-Kategorie"""
    try:
        # Überprüfen, ob die Ticket-Kategorie in Verwendung ist
        tickets_with_category = mongodb.db.tickets.find_one({'category': category})
        if tickets_with_category:
            flash('Die Ticket-Kategorie kann nicht gelöscht werden, da sie noch von Tickets verwendet wird.', 'error')
            return redirect(url_for('admin.tickets'))

        # Ticket-Kategorie aus der Liste entfernen
        mongodb.update_one_array(
            {'key': 'ticket_categories'},
            {'$pull': {'value': category}}
        )
        
        flash('Ticket-Kategorie erfolgreich gelöscht.', 'success')
        return redirect(url_for('admin.tickets'))
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('admin.tickets'))

@bp.route('/system')
@admin_required
def system():
    """System-Einstellungen"""
    try:
        # Hole alle verfügbaren Logos
        logos = []
        logos_dir = os.path.join(current_app.static_folder, 'uploads', 'logos')
        if os.path.exists(logos_dir):
            for filename in os.listdir(logos_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                    logos.append(filename)
        
        # Hole aktuelle Einstellungen
        settings = mongodb.db.settings.find_one({'key': 'system'}) or {}
        
        return render_template('admin/server-settings.html', 
                             logos=logos, 
                             settings=settings.get('value', {}))
    except Exception as e:
        logger.error(f"Fehler beim Laden der Systemeinstellungen: {str(e)}")
        flash('Fehler beim Laden der Systemeinstellungen', 'error')
        return redirect(url_for('admin.index'))

# Abteilungsverwaltung
@bp.route('/departments')
@mitarbeiter_required
def get_departments():
    """Gibt alle Abteilungen zurück"""
    try:
        settings = mongodb.db.settings.find_one({'key': 'departments'})
        departments = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                departments = [dept.strip() for dept in value.split(',') if dept.strip()]
            elif isinstance(value, list):
                departments = value
        return jsonify({
            'success': True,
            'departments': [{'name': dept} for dept in departments]
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Abteilungen: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Abteilungen'
        })

@bp.route('/departments/add', methods=['POST'])
@mitarbeiter_required
def add_department():
    """Fügt eine neue Abteilung hinzu"""
    try:
        name = request.form.get('department', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Lade aktuelle Abteilungen
        settings = mongodb.db.settings.find_one({'key': 'departments'})
        current_departments = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                current_departments = [dept.strip() for dept in value.split(',') if dept.strip()]
            elif isinstance(value, list):
                current_departments = value
        
        # Prüfe auf Duplikate (case-insensitive)
        if any(dept.lower() == name.lower() for dept in current_departments):
            return jsonify({
                'success': False,
                'message': 'Diese Abteilung existiert bereits.'
            })

        # Abteilung zur Liste hinzufügen
        current_departments.append(name)
        
        # Speichere als Array
        mongodb.db.settings.update_one(
            {'key': 'departments'},
            {'$set': {'value': current_departments}},
            upsert=True
        )

        return jsonify({
            'success': True,
            'message': 'Abteilung erfolgreich hinzugefügt.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Abteilung: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/departments/delete/<name>', methods=['POST'])
@mitarbeiter_required
def delete_department(name):
    try:
        # Überprüfen, ob die Abteilung in Verwendung ist
        workers_with_department = mongodb.db.workers.find_one({'department': name})
        if workers_with_department:
            return jsonify({
                'success': False,
                'message': 'Die Abteilung kann nicht gelöscht werden, da sie noch von Mitarbeitern verwendet wird.'
            })

        # Lade aktuelle Abteilungen
        settings = mongodb.db.settings.find_one({'key': 'departments'})
        current_departments = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                current_departments = [dept.strip() for dept in value.split(',') if dept.strip()]
            elif isinstance(value, list):
                current_departments = value
        
        # Abteilung aus der Liste entfernen
        if name in current_departments:
            current_departments.remove(name)
            mongodb.db.settings.update_one(
                {'key': 'departments'},
                {'$set': {'value': current_departments}}
            )
        
        return jsonify({
            'success': True,
            'message': 'Abteilung erfolgreich gelöscht.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Abteilung: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

# Kategorienverwaltung
@bp.route('/categories')
@mitarbeiter_required
def get_categories_admin():
    """Gibt alle Kategorien zurück"""
    try:
        settings = mongodb.db.settings.find_one({'key': 'categories'})
        categories = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                categories = [cat.strip() for cat in value.split(',') if cat.strip()]
            elif isinstance(value, list):
                categories = value
        return jsonify({
            'success': True,
            'categories': [{'name': cat} for cat in categories]
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Kategorien: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Kategorien'
        })

@bp.route('/categories/add', methods=['POST'])
@mitarbeiter_required
def add_category():
    """Fügt eine neue Kategorie hinzu"""
    try:
        name = request.form.get('category', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Lade aktuelle Kategorien
        settings = mongodb.db.settings.find_one({'key': 'categories'})
        current_categories = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                current_categories = [cat.strip() for cat in value.split(',') if cat.strip()]
            elif isinstance(value, list):
                current_categories = value
        
        # Prüfe auf Duplikate (case-insensitive)
        if any(cat.lower() == name.lower() for cat in current_categories):
            return jsonify({
                'success': False,
                'message': 'Diese Kategorie existiert bereits.'
            })

        # Kategorie zur Liste hinzufügen
        current_categories.append(name)
        
        # Speichere als Array
        mongodb.db.settings.update_one(
            {'key': 'categories'},
            {'$set': {'value': current_categories}},
            upsert=True
        )

        return jsonify({
            'success': True,
            'message': 'Kategorie erfolgreich hinzugefügt.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Kategorie: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/categories/delete/<name>', methods=['POST'])
@mitarbeiter_required
def delete_category(name):
    try:
        # Überprüfen, ob die Kategorie in Verwendung ist
        tools_with_category = mongodb.db.tools.find_one({'category': name})
        if tools_with_category:
            return jsonify({
                'success': False,
                'message': 'Die Kategorie kann nicht gelöscht werden, da sie noch von Werkzeugen verwendet wird.'
            })

        # Lade aktuelle Kategorien
        settings = mongodb.db.settings.find_one({'key': 'categories'})
        current_categories = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                current_categories = [cat.strip() for cat in value.split(',') if cat.strip()]
            elif isinstance(value, list):
                current_categories = value
        
        # Kategorie aus der Liste entfernen
        if name in current_categories:
            current_categories.remove(name)
            mongodb.db.settings.update_one(
                {'key': 'categories'},
                {'$set': {'value': current_categories}}
            )
        
        return jsonify({
            'success': True,
            'message': 'Kategorie erfolgreich gelöscht.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Kategorie: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

# Standortverwaltung
@bp.route('/locations')
@mitarbeiter_required
def get_locations():
    """Gibt alle Standorte zurück"""
    try:
        settings = mongodb.db.settings.find_one({'key': 'locations'})
        locations = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                locations = [loc.strip() for loc in value.split(',') if loc.strip()]
            elif isinstance(value, list):
                locations = value
        return jsonify({
            'success': True,
            'locations': [{'name': loc} for loc in locations]
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Standorte: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Standorte'
        })

@bp.route('/locations/add', methods=['POST'])
@mitarbeiter_required
def add_location():
    """Fügt einen neuen Standort hinzu"""
    try:
        name = request.form.get('location', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Lade aktuelle Standorte
        settings = mongodb.db.settings.find_one({'key': 'locations'})
        current_locations = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                current_locations = [loc.strip() for loc in value.split(',') if loc.strip()]
            elif isinstance(value, list):
                current_locations = value
        
        # Prüfe auf Duplikate (case-insensitive)
        if any(loc.lower() == name.lower() for loc in current_locations):
            return jsonify({
                'success': False,
                'message': 'Dieser Standort existiert bereits.'
            })

        # Standort zur Liste hinzufügen
        current_locations.append(name)
        
        # Speichere als Array
        mongodb.db.settings.update_one(
            {'key': 'locations'},
            {'$set': {'value': current_locations}},
            upsert=True
        )

        return jsonify({
            'success': True,
            'message': 'Standort erfolgreich hinzugefügt.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Standorts: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/locations/delete/<name>', methods=['POST'])
@mitarbeiter_required
def delete_location(name):
    try:
        # Überprüfen, ob der Standort in Verwendung ist
        tools_with_location = mongodb.db.tools.find_one({'location': name})
        if tools_with_location:
            return jsonify({
                'success': False,
                'message': 'Der Standort kann nicht gelöscht werden, da er noch von Werkzeugen verwendet wird.'
            })

        # Lade aktuelle Standorte
        settings = mongodb.db.settings.find_one({'key': 'locations'})
        current_locations = []
        if settings and 'value' in settings:
            value = settings['value']
            if isinstance(value, str):
                current_locations = [loc.strip() for loc in value.split(',') if loc.strip()]
            elif isinstance(value, list):
                current_locations = value
        
        # Standort aus der Liste entfernen
        if name in current_locations:
            current_locations.remove(name)
            mongodb.db.settings.update_one(
                {'key': 'locations'},
                {'$set': {'value': current_locations}}
            )
        
        return jsonify({
            'success': True,
            'message': 'Standort erfolgreich gelöscht.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Standorts: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/backup/list')
@mitarbeiter_required
def backup_list():
    """Gibt eine Liste der verfügbaren Backups zurück"""
    try:
        backups = get_backup_info()
        return jsonify({
            'status': 'success',
            'backups': backups
        })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Fehler beim Laden der Backups'
        }), 500

@bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Erstellt ein neues Backup der aktuellen Datenbank"""
    try:
        from app.utils.backup_manager import backup_manager
        
        backup_file = backup_manager.create_backup()
        
        if backup_file:
            # E-Mail-Versand (optional)
            email_recipient = request.form.get('email_recipient', '').strip()
            if email_recipient:
                try:
                    from app.utils.email_utils import send_backup_mail
                    backup_path = backup_manager.get_backup_path(backup_file)
                    send_backup_mail(email_recipient, str(backup_path))
                    return jsonify({
                        'status': 'success',
                        'message': f'Backup erfolgreich erstellt und an {email_recipient} gesendet',
                        'filename': backup_file
                    })
                except Exception as e:
                    logger.error(f"Fehler beim E-Mail-Versand: {str(e)}")
                    return jsonify({
                        'status': 'success',
                        'message': 'Backup erfolgreich erstellt, aber E-Mail-Versand fehlgeschlagen',
                        'filename': backup_file
                    })
            else:
                return jsonify({
                    'status': 'success',
                    'message': 'Backup erfolgreich erstellt',
                    'filename': backup_file
                })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Fehler beim Erstellen des Backups'
            }), 500
            
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Erstellen des Backups: {str(e)}'
        }), 500

@bp.route('/backup/upload', methods=['POST'])
@admin_required
def upload_backup():
    """Lädt ein Backup hoch und stellt es wieder her"""
    try:
        if 'backup_file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400
            
        file = request.files['backup_file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400
            
        # Prüfe Dateityp
        if not file.filename.endswith('.json'):
            return jsonify({
                'status': 'error',
                'message': 'Ungültiger Dateityp. Bitte eine .json-Datei hochladen.'
            }), 400
            
        from app.utils.backup_manager import backup_manager
        
        # Erstelle Backup der aktuellen DB vor dem Upload
        current_backup = backup_manager.create_backup()
        
        # Stelle das hochgeladene Backup wieder her
        success = backup_manager.restore_backup(file)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Backup erfolgreich hochgeladen und aktiviert',
                'previous_backup': current_backup
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Fehler beim Wiederherstellen des Backups'
            }), 500
            
    except Exception as e:
        logger.error(f"Fehler beim Hochladen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Hochladen des Backups: {str(e)}'
        }), 500

@bp.route('/backup/restore/<filename>', methods=['POST'])
@admin_required
def restore_backup(filename):
    """Stellt ein Backup wieder her"""
    try:
        from app.utils.backup_manager import backup_manager
        
        # Erstelle Backup der aktuellen DB vor der Wiederherstellung
        current_backup = backup_manager.create_backup()
        
        # Stelle das Backup wieder her
        success = backup_manager.restore_backup_by_filename(filename)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Backup erfolgreich wiederhergestellt',
                'previous_backup': current_backup
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Fehler beim Wiederherstellen des Backups'
            }), 500
            
    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Wiederherstellen des Backups: {str(e)}'
        }), 500

@bp.route('/backup/download/<filename>')
@admin_required
def download_backup(filename):
    """Lädt ein Backup herunter"""
    try:
        from app.utils.backup_manager import backup_manager
        
        backup_path = backup_manager.get_backup_path(filename)
        
        if not backup_path.exists():
            return jsonify({
                'status': 'error',
                'message': 'Backup-Datei nicht gefunden'
            }), 404
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Fehler beim Herunterladen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Herunterladen des Backups: {str(e)}'
        }), 500

@bp.route('/backup/delete/<filename>', methods=['DELETE'])
@admin_required
def delete_backup(filename):
    """Löscht ein Backup"""
    try:
        from app.utils.backup_manager import backup_manager
        
        success = backup_manager.delete_backup(filename)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Backup erfolgreich gelöscht'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Fehler beim Löschen des Backups'
            }), 500
            
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Löschen des Backups: {str(e)}'
        }), 500

@bp.route('/available-logos')
@mitarbeiter_required
def available_logos():
    """Gibt eine Liste der verfügbaren Logos zurück"""
    try:
        logo_dir = Path(current_app.static_folder) / 'uploads' / 'logos'
        logos = []
        
        if logo_dir.exists():
            for logo_file in logo_dir.glob('*'):
                if logo_file.is_file() and logo_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.svg']:
                    logos.append({
                        'name': logo_file.name,
                        'path': f'/static/uploads/logos/{logo_file.name}',
                        'size': logo_file.stat().st_size,
                        'modified': datetime.fromtimestamp(logo_file.stat().st_mtime)
                    })
        
        return jsonify({
            'success': True,
            'logos': logos
        })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Logos: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Logos'
        }), 500

# Update-Verwaltung
@bp.route('/updates')
@admin_required
def updates():
    """Update-Verwaltungsseite"""
    return render_template('admin/updates.html')

@bp.route('/updates/check', methods=['POST'])
@admin_required
def check_updates():
    """Prüft auf verfügbare Updates"""
    try:
        from app.utils.update_manager import UpdateManager
        
        update_manager = UpdateManager(current_app.root_path)
        update_info = update_manager.check_for_updates()
        
        if update_info.get('update_available'):
            return jsonify({
                'status': 'success',
                'updates_available': True,
                'current_version': update_info['current_version'],
                'latest_version': update_info['latest_version'],
                'release_notes': update_info.get('release_notes', ''),
                'commits_behind': f"Version {update_info['current_version']} → {update_info['latest_version']}"
            })
        else:
            return jsonify({
                'status': 'success',
                'updates_available': False,
                'current_version': update_info['current_version'],
                'latest_version': update_info['latest_version'],
                'message': 'Keine Updates verfügbar'
            })
            
    except Exception as e:
        logger.error(f"Fehler beim Prüfen auf Updates: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Prüfen auf Updates: {str(e)}'
        }), 500

@bp.route('/updates/apply', methods=['POST'])
@admin_required
def apply_updates():
    """Führt ein Update durch"""
    try:
        from app.utils.update_manager import UpdateManager
        
        update_manager = UpdateManager(current_app.root_path)
        result = update_manager.perform_update()
        
        if result.get('success'):
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'backup_file': result.get('backup_file', '')
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('message', 'Unbekannter Fehler beim Update')
            }), 500
            
    except Exception as e:
        logger.error(f"Fehler beim Durchführen des Updates: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Durchführen des Updates: {str(e)}'
        }), 500

@bp.route('/updates/status')
@admin_required
def update_status():
    """Gibt den aktuellen Update-Status zurück"""
    try:
        from app.utils.update_manager import UpdateManager
        
        update_manager = UpdateManager(current_app.root_path)
        status = update_manager.get_update_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Update-Status: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@bp.route('/updates/history')
@admin_required
def update_history():
    """Gibt die Update-Historie zurück"""
    try:
        from app.utils.update_manager import UpdateManager
        
        update_manager = UpdateManager(current_app.root_path)
        history = update_manager.get_update_history()
        
        return jsonify({
            'status': 'success',
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Update-Historie: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Abrufen der Update-Historie: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/update-assignment', methods=['POST'])
@login_required
@admin_required
def update_ticket_assignment(ticket_id):
    """Aktualisiert die Zuweisung eines Tickets"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        assigned_to = data.get('assigned_to')
        
        # Wenn assigned_to leer ist, setze es auf None
        if not assigned_to or assigned_to == "":
            assigned_to = None

        # Aktualisiere die Zuweisung direkt im Ticket
        if not mongodb.update_one('tickets', {'_id': ObjectId(ticket_id)}, {'$set': {'assigned_to': assigned_to, 'updated_at': datetime.now()}}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Zuweisung'})

        return jsonify({'success': True, 'message': 'Zuweisung erfolgreich aktualisiert'})

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Zuweisung: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/tickets/<ticket_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_ticket_status(ticket_id):
    """Ticket-Status aktualisieren"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'success': False, 'message': 'Status nicht angegeben'}), 400
            
        new_status = data['status']
        
        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
            
        # Aktualisiere den Status
        mongodb.update_one('tickets', 
                          {'_id': ObjectId(ticket_id)}, 
                          {
                              '$set': {
                                  'status': new_status,
                                  'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                              }
                          })
        
        return jsonify({
            'success': True,
            'message': f'Status wurde auf "{new_status}" geändert'
        })

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/tickets/<ticket_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_ticket(ticket_id):
    """Ticket löschen"""
    try:
        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404
            
        # Lösche das Ticket
        mongodb.delete_one('tickets', {'_id': ObjectId(ticket_id)})
        
        # Lösche auch zugehörige Daten
        mongodb.delete_many('ticket_notes', {'ticket_id': ObjectId(ticket_id)})
        mongodb.delete_many('ticket_messages', {'ticket_id': ObjectId(ticket_id)})
        mongodb.delete_many('ticket_assignments', {'ticket_id': ObjectId(ticket_id)})
        mongodb.delete_one('auftrag_details', {'ticket_id': ObjectId(ticket_id)})
        mongodb.delete_many('auftrag_material', {'ticket_id': ObjectId(ticket_id)})
        
        return jsonify({
            'success': True,
            'message': 'Ticket wurde erfolgreich gelöscht'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Tickets: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/debug/barcodes')
@mitarbeiter_required
def debug_barcodes():
    """Debug-Route zum Überprüfen der Barcodes in der Datenbank"""
    try:
        tools = list(mongodb.find('tools', {}, limit=5))
        workers = list(mongodb.find('workers', {}, limit=5))
        consumables = list(mongodb.find('consumables', {}, limit=5))
        
        return jsonify({
            'tools': [{'barcode': t.get('barcode'), 'name': t.get('name')} for t in tools],
            'workers': [{'barcode': w.get('barcode'), 'name': f"{w.get('firstname', '')} {w.get('lastname', '')}"} for w in workers],
            'consumables': [{'barcode': c.get('barcode'), 'name': c.get('name')} for c in consumables]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/debug/clean-barcodes', methods=['POST'])
@mitarbeiter_required
def clean_barcodes():
    """Bereinigt verunreinigte Barcodes in der Datenbank"""
    try:
        cleaned_count = 0
        
        # Werkzeuge bereinigen
        tools = mongodb.find('tools', {})
        for tool in tools:
            old_barcode = tool.get('barcode', '')
            if old_barcode and ' - IP:' in str(old_barcode):
                # Entferne IP-Informationen
                clean_barcode = str(old_barcode).split(' - IP:')[0].strip()
                mongodb.update_one('tools', {'_id': tool['_id']}, {'$set': {'barcode': clean_barcode}})
                cleaned_count += 1
        
        # Mitarbeiter bereinigen
        workers = mongodb.find('workers', {})
        for worker in workers:
            old_barcode = worker.get('barcode', '')
            if old_barcode and ' - IP:' in str(old_barcode):
                # Entferne IP-Informationen
                clean_barcode = str(old_barcode).split(' - IP:')[0].strip()
                mongodb.update_one('workers', {'_id': worker['_id']}, {'$set': {'barcode': clean_barcode}})
                cleaned_count += 1
        
        # Verbrauchsmaterialien bereinigen
        consumables = mongodb.find('consumables', {})
        for consumable in consumables:
            old_barcode = consumable.get('barcode', '')
            if old_barcode and ' - IP:' in str(old_barcode):
                # Entferne IP-Informationen
                clean_barcode = str(old_barcode).split(' - IP:')[0].strip()
                mongodb.update_one('consumables', {'_id': consumable['_id']}, {'$set': {'barcode': clean_barcode}})
                cleaned_count += 1
        
        return jsonify({
            'success': True,
            'message': f'{cleaned_count} Barcodes wurden bereinigt'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/debug')
@mitarbeiter_required
def debug_page():
    """Debug-Seite für Barcode-Bereinigung"""
    return render_template('admin/debug.html')

@bp.route('/debug/test-barcodes')
@mitarbeiter_required
def test_barcodes():
    """Test-Route zum Überprüfen der Barcodes"""
    try:
        # Hole ein paar Beispiele aus jeder Kategorie
        tools = list(mongodb.find('tools', {}, limit=3))
        workers = list(mongodb.find('workers', {}, limit=3))
        consumables = list(mongodb.find('consumables', {}, limit=3))
        
        result = {
            'tools': [{'barcode': str(t.get('barcode', '')), 'name': t.get('name', '')} for t in tools],
            'workers': [{'barcode': str(w.get('barcode', '')), 'name': f"{w.get('firstname', '')} {w.get('lastname', '')}"} for w in workers],
            'consumables': [{'barcode': str(c.get('barcode', '')), 'name': c.get('name', '')} for c in consumables]
        }
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/delete_user/<user_id>', methods=['POST'])
@mitarbeiter_required
def delete_user(user_id):
    """Benutzer löschen"""
    try:
        user = mongodb.find_one('users', {'_id': ObjectId(user_id)})
        if not user:
            flash('Benutzer nicht gefunden', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Verhindere das Löschen des eigenen Accounts
        if user['username'] == current_user.username:
            flash('Sie können Ihren eigenen Account nicht löschen', 'error')
            return redirect(url_for('admin.manage_users'))
        
        mongodb.delete_one('users', {'_id': ObjectId(user_id)})
        flash(f'Benutzer "{user["username"]}" erfolgreich gelöscht', 'success')
        return redirect(url_for('admin.manage_users'))
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Benutzers: {e}")
        flash('Fehler beim Löschen des Benutzers', 'error')
        return redirect(url_for('admin.manage_users'))

@bp.route('/user_form')
@mitarbeiter_required
def user_form():
    """Benutzer-Formular (für neue Benutzer)"""
    return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender'])

@bp.route('/export_all_data')
@admin_required
def export_all_data():
    """Exportiert alle Daten als Excel-Datei"""
    try:
        # Hole alle Daten aus der Datenbank
        tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
        workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}))
        consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
        lendings = list(mongodb.find('lendings', {}))
        
        # Erstelle Excel-Datei mit mehreren Arbeitsblättern
        data_dict = {
            'Werkzeuge': tools,
            'Mitarbeiter': workers,
            'Verbrauchsmaterial': consumables,
            'Ausleihverlauf': lendings
        }
        
        # Erstelle Excel-Datei
        excel_file = create_multi_sheet_excel(data_dict)
        
        # Sende Datei als Download
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=f'scandy_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Fehler beim Exportieren der Daten: {str(e)}")
        flash('Fehler beim Exportieren der Daten', 'error')
        return redirect(url_for('admin.system'))

@bp.route('/import_all_data', methods=['POST'])
@admin_required
def import_all_data():
    """Importiert Daten aus einer Excel-Datei"""
    try:
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('admin.system'))
            
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('admin.system'))
            
        if not file.filename.endswith('.xlsx'):
            flash('Nur Excel-Dateien (.xlsx) werden unterstützt', 'error')
            return redirect(url_for('admin.system'))
        
        # Speichere temporäre Datei
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            file.save(tmp_file.name)
            tmp_file_path = tmp_file.name
        
        try:
            # Lese Excel-Datei
            import pandas as pd
            
            # Lese alle Arbeitsblätter
            excel_file = pd.ExcelFile(tmp_file_path)
            
            imported_count = 0
            
            # Importiere Werkzeuge
            if 'Werkzeuge' in excel_file.sheet_names:
                df_tools = pd.read_excel(excel_file, sheet_name='Werkzeuge')
                for _, row in df_tools.iterrows():
                    tool_data = row.to_dict()
                    # Entferne NaN-Werte
                    tool_data = {k: v for k, v in tool_data.items() if pd.notna(v)}
                    # Prüfe ob Werkzeug bereits existiert
                    existing = mongodb.find_one('tools', {'barcode': tool_data.get('barcode')})
                    if not existing:
                        mongodb.insert_one('tools', tool_data)
                        imported_count += 1
            
            # Importiere Mitarbeiter
            if 'Mitarbeiter' in excel_file.sheet_names:
                df_workers = pd.read_excel(excel_file, sheet_name='Mitarbeiter')
                for _, row in df_workers.iterrows():
                    worker_data = row.to_dict()
                    worker_data = {k: v for k, v in worker_data.items() if pd.notna(v)}
                    existing = mongodb.find_one('workers', {'barcode': worker_data.get('barcode')})
                    if not existing:
                        mongodb.insert_one('workers', worker_data)
                        imported_count += 1
            
            # Importiere Verbrauchsmaterial
            if 'Verbrauchsmaterial' in excel_file.sheet_names:
                df_consumables = pd.read_excel(excel_file, sheet_name='Verbrauchsmaterial')
                for _, row in df_consumables.iterrows():
                    consumable_data = row.to_dict()
                    consumable_data = {k: v for k, v in consumable_data.items() if pd.notna(v)}
                    existing = mongodb.find_one('consumables', {'barcode': consumable_data.get('barcode')})
                    if not existing:
                        mongodb.insert_one('consumables', consumable_data)
                        imported_count += 1
            
            flash(f'{imported_count} Datensätze erfolgreich importiert', 'success')
            
        finally:
            # Lösche temporäre Datei
            os.unlink(tmp_file_path)
        
        return redirect(url_for('admin.system'))
        
    except Exception as e:
        logger.error(f"Fehler beim Importieren der Daten: {str(e)}")
        flash(f'Fehler beim Importieren: {str(e)}', 'error')
        return redirect(url_for('admin.system'))

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Passwort-Reset per E-Mail"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Bitte geben Sie eine E-Mail-Adresse ein.', 'error')
            return render_template('auth/reset_password.html')
        
        # Prüfe ob Benutzer mit dieser E-Mail existiert
        user = mongodb.find_one('users', {'email': email})
        if not user:
            flash('Kein Benutzer mit dieser E-Mail-Adresse gefunden.', 'error')
            return render_template('auth/reset_password.html')
        
        # Generiere sicheres neues Passwort (wie bei add_user)
        import secrets
        import string
        # Mindestens 1 von jeder Kategorie sicherstellen
        password = (
            secrets.choice(string.ascii_uppercase) +  # 1 Großbuchstabe
            secrets.choice(string.ascii_lowercase) +  # 1 Kleinbuchstabe
            secrets.choice(string.digits) +           # 1 Ziffer
            secrets.choice("!@#$%^&*") +              # 1 Sonderzeichen
            ''.join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*") for _ in range(8))  # 8 weitere zufällige Zeichen
        )
        # Passwort mischen
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        password = ''.join(password_list)
        
        # Hash das neue Passwort
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(password)
        
        # Aktualisiere das Passwort in der Datenbank
        try:
            from bson import ObjectId
            result = mongodb.update_one('users', 
                                     {'_id': ObjectId(user['_id'])}, 
                                     {'$set': {'password_hash': password_hash, 'updated_at': datetime.now()}})
            
            # Prüfe ob das Update erfolgreich war (result ist ein bool)
            if not result:
                logger.error(f"Fehler beim Aktualisieren des Passworts für Benutzer {user['username']} - Update fehlgeschlagen")
                flash('Fehler beim Zurücksetzen des Passworts.', 'error')
                return render_template('auth/reset_password.html')
            
            logger.info(f"Passwort erfolgreich zurückgesetzt für Benutzer {user['username']} ({email})")
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Passworts in der Datenbank: {e}")
            flash('Fehler beim Zurücksetzen des Passworts.', 'error')
            return render_template('auth/reset_password.html')
        
        # Sende E-Mail mit neuem Passwort
        try:
            from app.utils.email_utils import send_password_reset_mail
            send_result = send_password_reset_mail(email, password=password)
            if send_result:
                flash('Ein neues Passwort wurde an Ihre E-Mail-Adresse gesendet.', 'success')
                logger.info(f"Passwort-Reset-E-Mail erfolgreich an {email} gesendet")
            else:
                flash('Passwort wurde zurückgesetzt, aber E-Mail konnte nicht versendet werden.', 'warning')
                logger.warning(f"Passwort-Reset-E-Mail konnte nicht an {email} gesendet werden")
        except Exception as e:
            logger.error(f"Fehler beim Versenden der E-Mail: {e}")
            flash('Passwort wurde zurückgesetzt, aber E-Mail konnte nicht versendet werden.', 'warning')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html')

@bp.route('/debug/password/<username>')
@admin_required
def debug_password(username):
    """Debug-Route zum Überprüfen des Passwort-Hashes eines Benutzers"""
    try:
        user = mongodb.find_one('users', {'username': username})
        if not user:
            return jsonify({'error': 'Benutzer nicht gefunden'}), 404
        
        return jsonify({
            'username': user['username'],
            'email': user.get('email'),
            'has_password_hash': 'password_hash' in user,
            'password_hash_length': len(user.get('password_hash', '')),
            'password_hash_preview': user.get('password_hash', '')[:20] + '...' if user.get('password_hash') else None,
            'updated_at': user.get('updated_at'),
            'created_at': user.get('created_at')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500