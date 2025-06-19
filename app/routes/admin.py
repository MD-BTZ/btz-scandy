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
from app.models.mongodb_database import MongoDB
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from bson import ObjectId
from werkzeug.security import generate_password_hash

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/admin')
mongodb = MongoDB()

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

# Stelle sicher, dass die Standard-Einstellungen beim Start der App vorhanden sind
ensure_default_settings()

def get_recent_activity():
    """Hole die letzten Aktivitäten"""
    # TODO: Implementiere MongoDB-Version
    return []

def get_material_usage():
    """Hole die Materialnutzung"""
    # TODO: Implementiere MongoDB-Version
    return []

def get_warnings():
    """Hole aktuelle Warnungen"""
    # TODO: Implementiere MongoDB-Version
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
    """Erstellt eine Excel-Datei mit mehreren Sheets aus einem Dictionary von Daten.
    Args:
        data_dict (dict): Ein Dictionary, bei dem Keys die Sheet-Namen sind
                          und Values Listen von Dictionaries (die Zeilen) sind.
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active) # Standard-Sheet entfernen

    # Deutsche Spaltenüberschriften
    headers_de = {
        'Werkzeuge': {
            'barcode': 'Barcode',
            'name': 'Name',
            'category': 'Kategorie',
            'location': 'Standort',
            'status': 'Status',
            'description': 'Beschreibung'
        },
        'Mitarbeiter': {
            'barcode': 'Barcode',
            'firstname': 'Vorname',
            'lastname': 'Nachname',
            'department': 'Abteilung',
            'email': 'E-Mail'
        },
        'Verbrauchsmaterial': {
            'barcode': 'Barcode',
            'name': 'Name',
            'category': 'Kategorie',
            'location': 'Standort',
            'quantity': 'Menge',
            'min_quantity': 'Mindestmenge',
            'description': 'Beschreibung'
        },
        'Verlauf': {
            'lent_at': 'Ausgeliehen am',
            'returned_at': 'Zurückgegeben am',
            'tool_name': 'Werkzeug',
            'tool_barcode': 'Werkzeug-Barcode',
            'consumable_name': 'Verbrauchsmaterial',
            'consumable_barcode': 'Material-Barcode',
            'worker_name': 'Mitarbeiter',
            'worker_barcode': 'Mitarbeiter-Barcode',
            'type': 'Typ',
            'quantity': 'Menge'
        }
    }

    for sheet_name, data in data_dict.items():
        ws = wb.create_sheet(title=sheet_name)
        
        if not data:
            ws.cell(row=1, column=1, value="Keine Daten verfügbar")
            continue
        
        # Headers aus dem ersten Datensatz holen
        headers = list(data[0].keys())
        
        # Deutsche Überschriften setzen
        for col, header in enumerate(headers, 1):
            de_header = headers_de.get(sheet_name, {}).get(header, header)
            cell = ws.cell(row=1, column=col, value=de_header)
            # Formatierung der Überschriften
            cell.font = openpyxl.styles.Font(bold=True)
            cell.fill = openpyxl.styles.PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            cell.alignment = openpyxl.styles.Alignment(horizontal='center', vertical='center')
        
        # Daten einfügen
        for row_idx, item in enumerate(data, 2):
            for col_idx, key in enumerate(headers, 1):
                value = item.get(key, '')
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                
                # Datumsformatierung
                if isinstance(value, datetime):
                    cell.number_format = 'DD.MM.YYYY HH:MM:SS'
                # Zahlenformatierung
                elif isinstance(value, (int, float)):
                    cell.number_format = '#,##0'
                    cell.alignment = openpyxl.styles.Alignment(horizontal='right')
                # Textformatierung
                else:
                    cell.alignment = openpyxl.styles.Alignment(horizontal='left')

        # Spaltenbreiten automatisch anpassen
        for col_idx, column_cells in enumerate(ws.columns, 1):
            max_length = 0
            column_letter = openpyxl.utils.get_column_letter(col_idx)
            
            for cell in column_cells:
                try:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        max_length = max(max_length, cell_length)
                except:
                    pass
            
            # Spaltenbreite mit Puffer
            adjusted_width = (max_length + 2) * 1.2
            ws.column_dimensions[column_letter].width = adjusted_width

        # Rahmen für alle Zellen
        thin_border = openpyxl.styles.Border(
            left=openpyxl.styles.Side(style='thin'),
            right=openpyxl.styles.Side(style='thin'),
            top=openpyxl.styles.Side(style='thin'),
            bottom=openpyxl.styles.Side(style='thin')
        )
        
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                cell.border = thin_border

    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    return excel_file

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
    # Sortiere die Ausleihen nach Datum (neueste zuerst)
    active_lendings.sort(key=lambda x: x.get('lent_at', datetime.min), reverse=True)
    
    for lending in active_lendings:
        tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
        worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
        if tool and worker:
            current_lendings.append({
                **lending,
                'tool_name': tool['name'],
                'worker_name': f"{worker['firstname']} {worker['lastname']}"
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
        print("POST-Anfrage empfangen")
        
        try:
            # JSON-Daten verarbeiten
            data = request.get_json()
            if data is None:
                return jsonify({
                    'success': False,
                    'message': 'Keine gültigen JSON-Daten empfangen'
                }), 400
                
            print("JSON-Daten:", data)
            
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
                print("Fehler bei der Ausleihe:", str(e))
                return jsonify({
                    'success': False,
                    'message': f'Fehler: {str(e)}'
                }), 500
            
        except Exception as e:
            print(f"Fehler beim Verarbeiten der Anfrage: {str(e)}")
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

        return render_template('admin/manual_lending.html', 
                              tools=tools,
                              workers=workers,
                              consumables=consumables)
    except Exception as e:
        print(f"Fehler beim Laden der Daten: {e}")
        flash('Fehler beim Laden der Daten', 'error')
        return render_template('admin/manual_lending.html', 
                              tools=[], 
                              workers=[], 
                              consumables=[])

@bp.route('/trash')
@mitarbeiter_required
def trash():
    """Papierkorb mit gelöschten Einträgen"""
    try:
        # Gelöschte Werkzeuge
        tools = mongodb.find('tools', {'deleted': True}, sort=[('deleted_at', -1)])
        
        logger.debug(f"Gelöschte Werkzeuge gefunden: {len(tools)}")
        for tool in tools:
            logger.debug(f"Tool: {tool}")
        
        # Gelöschte Verbrauchsmaterialien
        consumables = mongodb.find('consumables', {'deleted': True}, sort=[('deleted_at', -1)])
        
        logger.debug(f"Gelöschte Verbrauchsmaterialien gefunden: {len(consumables)}")
        for consumable in consumables:
            logger.debug(f"Consumable: {consumable}")
        
        # Gelöschte Mitarbeiter
        workers = mongodb.find('workers', {'deleted': True}, sort=[('deleted_at', -1)])
        
        logger.debug(f"Gelöschte Mitarbeiter gefunden: {len(workers)}")
        for worker in workers:
            logger.debug(f"Worker: {worker}")
        
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
        if type == 'tool':
            # Prüfe ob das Werkzeug existiert
            tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': True})
            
            if not tool:
                return jsonify({
                    'success': False,
                    'message': 'Werkzeug nicht gefunden'
                }), 404
                
            # Stelle das Werkzeug wieder her
            mongodb.update_one('tools', 
                             {'barcode': barcode}, 
                             {'$set': {'deleted': False, 'deleted_at': None}})
            
        elif type == 'consumable':
            # Prüfe ob das Verbrauchsmaterial existiert
            consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': True})
            
            if not consumable:
                return jsonify({
                    'success': False,
                    'message': 'Verbrauchsmaterial nicht gefunden'
                }), 404
                
            # Stelle das Verbrauchsmaterial wieder her
            mongodb.update_one('consumables', 
                             {'barcode': barcode}, 
                             {'$set': {'deleted': False, 'deleted_at': None}})
            
        elif type == 'worker':
            # Prüfe ob der Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': True})
            
            if not worker:
                return jsonify({
                    'success': False,
                    'message': 'Mitarbeiter nicht gefunden'
                }), 404
                
            # Stelle den Mitarbeiter wieder her
            mongodb.update_one('workers', 
                             {'barcode': barcode}, 
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

def get_label_setting(key, default):
    """Hole eine Label-Einstellung aus MongoDB"""
    try:
        setting = mongodb.find_one('settings', {'key': key})
        return setting['value'] if setting and setting.get('value') else default
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Einstellung {key}: {str(e)}")
        return default

def get_app_labels():
    """Hole alle Label-Einstellungen aus MongoDB"""
    return {
        'tools': {
            'name': get_label_setting('label_tools_name', 'Werkzeuge'),
            'icon': get_label_setting('label_tools_icon', 'fas fa-tools')
        },
        'consumables': {
            'name': get_label_setting('label_consumables_name', 'Verbrauchsmaterial'),
            'icon': get_label_setting('label_consumables_icon', 'fas fa-box-open')
        },
        'tickets': {
            'name': get_label_setting('label_tickets_name', 'Tickets'),
            'icon': get_label_setting('label_tickets_icon', 'fas fa-ticket-alt')
        }
    }

def get_all_users():
    """Gibt alle aktiven Benutzer zurück"""
    return mongodb.find('users', {'is_active': True}, sort=[('username', 1)])

def get_categories():
    """Gibt alle Kategorien zurück"""
    return mongodb.find('categories', {'deleted': {'$ne': True}}, sort=[('name', 1)])

@bp.route('/server-settings', methods=['GET', 'POST'])
@admin_required
def server_settings():
    if request.method == 'POST':
        # Begriffe & Icons
        label_tools_name = request.form.get('label_tools_name', 'Werkzeuge')
        label_tools_icon = request.form.get('label_tools_icon', 'fas fa-tools')
        label_consumables_name = request.form.get('label_consumables_name', 'Verbrauchsmaterial')
        label_consumables_icon = request.form.get('label_consumables_icon', 'fas fa-box')
        label_tickets_name = request.form.get('label_tickets_name', 'Tickets')
        label_tickets_icon = request.form.get('label_tickets_icon', 'fas fa-ticket-alt')
        
        # Speichere die Einstellungen in MongoDB
        settings_to_update = [
            {'key': 'label_tools_name', 'value': label_tools_name},
            {'key': 'label_tools_icon', 'value': label_tools_icon},
            {'key': 'label_consumables_name', 'value': label_consumables_name},
            {'key': 'label_consumables_icon', 'value': label_consumables_icon},
            {'key': 'label_tickets_name', 'value': label_tickets_name},
            {'key': 'label_tickets_icon', 'value': label_tickets_icon}
        ]
        
        for setting in settings_to_update:
            mongodb.update_one('settings', 
                             {'key': setting['key']}, 
                             {'$set': setting}, 
                             upsert=True)
        
        flash('Einstellungen wurden gespeichert', 'success')
        return redirect(url_for('admin.server_settings'))
    
    return render_template('admin/server-settings.html')

@bp.route('/export/all')
@mitarbeiter_required
def export_all_data():
    """Exportiert alle relevanten Collections in eine Excel-Datei mit mehreren Sheets"""
    try:
        # Daten abrufen aus MongoDB
        tools_data = mongodb.find('tools', {'deleted': {'$ne': True}}, sort=[('name', 1)])
        workers_data = mongodb.find('workers', {'deleted': {'$ne': True}}, sort=[('lastname', 1), ('firstname', 1)])
        consumables_data = mongodb.find('consumables', {'deleted': {'$ne': True}}, sort=[('name', 1)])
        
        # Lendings und Verbrauchsmaterial-Entnahmen
        lendings = mongodb.find('lendings', sort=[('lent_at', -1)])
        
        # Verbrauchsmaterial-Entnahmen
        consumable_usages = mongodb.find('consumable_usages', sort=[('used_at', -1)])
        
        # Verlauf-Daten zusammenstellen
        history_data = []
        
        # Werkzeug-Ausleihen
        for lending in lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
            if tool and worker:
                history_data.append({
                    'lent_at': lending['lent_at'],
                    'returned_at': lending.get('returned_at'),
                    'tool_name': tool['name'],
                    'tool_barcode': tool['barcode'],
                    'worker_name': f"{worker['firstname']} {worker['lastname']}",
                    'worker_barcode': worker['barcode'],
                    'type': 'Werkzeug Ausleihe',
                    'quantity': None
                })
        
        # Material-Verbrauch
        for usage in consumable_usages:
            consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
            worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
            if consumable and worker:
                history_data.append({
                    'lent_at': usage['used_at'],
                    'returned_at': None,
                    'consumable_name': consumable['name'],
                    'consumable_barcode': consumable['barcode'],
                    'worker_name': f"{worker['firstname']} {worker['lastname']}",
                    'worker_barcode': worker['barcode'],
                    'type': 'Material Verbrauch',
                    'quantity': usage['quantity']
                })

        # Daten für die Excel-Funktion vorbereiten
        export_data = {
            "Werkzeuge": tools_data,
            "Mitarbeiter": workers_data,
            "Verbrauchsmaterial": consumables_data,
            "Verlauf": history_data
        }

        excel_file = create_multi_sheet_excel(export_data)
        filename = f'scandy_gesamtexport_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Fehler beim Exportieren der Daten: {str(e)}", exc_info=True)
        flash(f'Fehler beim Exportieren: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/import/all', methods=['POST'])
@mitarbeiter_required
def import_all_data():
    """Importiert Daten aus einer Excel-Datei mit mehreren Sheets."""
    if 'file' not in request.files:
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('admin.system'))

    file = request.files['file']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'error')
        return redirect(url_for('admin.system'))

    if not file.filename.endswith('.xlsx'):
        flash('Ungültiger Dateityp. Bitte eine .xlsx-Datei hochladen.', 'error')
        return redirect(url_for('admin.system'))

    try:
        # Excel-Datei in BytesIO laden, um sie mit openpyxl zu öffnen
        file_content = BytesIO(file.read())
        wb = openpyxl.load_workbook(file_content, data_only=True) # data_only=True vermeidet Formeln

        imported_counts = {"Werkzeuge": 0, "Mitarbeiter": 0, "Verbrauchsmaterial": 0}
        errors = []

        # --- Werkzeuge importieren ---
        if "Werkzeuge" in wb.sheetnames:
            ws_tools = wb["Werkzeuge"]
            headers_tools = [cell.value for cell in ws_tools[1]]
            # Erwartete Spalten prüfen (Mindestanforderung)
            required_tools_cols = ['barcode', 'name']
            if not all(col in headers_tools for col in required_tools_cols):
                errors.append("Arbeitsblatt 'Werkzeuge' hat ungültige Spaltenüberschriften.")
            else:
                for row_idx, row in enumerate(ws_tools.iter_rows(min_row=2), start=2):
                    row_data = {headers_tools[i]: cell.value for i, cell in enumerate(row)}
                    try:
                        # Nur importieren, wenn Barcode und Name vorhanden sind
                        if row_data.get('barcode') and row_data.get('name'):
                             # Default-Werte für optionale Felder setzen, falls sie fehlen
                            desc = row_data.get('description', '')
                            cat = row_data.get('category')
                            loc = row_data.get('location')
                            status = row_data.get('status', 'verfügbar') # Default-Status

                            tool_data = {
                                'barcode': row_data['barcode'],
                                'name': row_data['name'],
                                'description': desc,
                                'category': cat,
                                'location': loc,
                                'status': status,
                                'deleted': False
                            }
                            
                            mongodb.update_one('tools', 
                                             {'barcode': tool_data['barcode']}, 
                                             {'$set': tool_data}, 
                                             upsert=True)
                            imported_counts["Werkzeuge"] += 1
                    except Exception as e:
                        errors.append(f"Fehler in Werkzeuge Zeile {row_idx}: {e}")
        else:
            errors.append("Arbeitsblatt 'Werkzeuge' nicht gefunden.")

        # --- Mitarbeiter importieren ---
        if "Mitarbeiter" in wb.sheetnames:
            ws_workers = wb["Mitarbeiter"]
            headers_workers = [cell.value for cell in ws_workers[1]]
            required_workers_cols = ['barcode', 'firstname', 'lastname']
            if not all(col in headers_workers for col in required_workers_cols):
                errors.append("Arbeitsblatt 'Mitarbeiter' hat ungültige Spaltenüberschriften.")
            else:
                 for row_idx, row in enumerate(ws_workers.iter_rows(min_row=2), start=2):
                    row_data = {headers_workers[i]: cell.value for i, cell in enumerate(row)}
                    try:
                        if row_data.get('barcode') and row_data.get('firstname') and row_data.get('lastname'):
                            dept = row_data.get('department')
                            email = row_data.get('email')

                            worker_data = {
                                'barcode': row_data['barcode'],
                                'firstname': row_data['firstname'],
                                'lastname': row_data['lastname'],
                                'department': dept,
                                'email': email,
                                'deleted': False
                            }
                            
                            mongodb.update_one('workers', 
                                             {'barcode': worker_data['barcode']}, 
                                             {'$set': worker_data}, 
                                             upsert=True)
                            imported_counts["Mitarbeiter"] += 1
                    except Exception as e:
                        errors.append(f"Fehler in Mitarbeiter Zeile {row_idx}: {e}")
        else:
            errors.append("Arbeitsblatt 'Mitarbeiter' nicht gefunden.")

        # --- Verbrauchsmaterial importieren ---
        if "Verbrauchsmaterial" in wb.sheetnames:
            ws_consumables = wb["Verbrauchsmaterial"]
            headers_consumables = [cell.value for cell in ws_consumables[1]]
            required_consumables_cols = ['barcode', 'name']
            if not all(col in headers_consumables for col in required_consumables_cols):
                 errors.append("Arbeitsblatt 'Verbrauchsmaterial' hat ungültige Spaltenüberschriften.")
            else:
                for row_idx, row in enumerate(ws_consumables.iter_rows(min_row=2), start=2):
                    row_data = {headers_consumables[i]: cell.value for i, cell in enumerate(row)}
                    try:
                        if row_data.get('barcode') and row_data.get('name'):
                            desc = row_data.get('description', '')
                            cat = row_data.get('category')
                            loc = row_data.get('location')
                            quantity = row_data.get('quantity', 0)
                            unit = row_data.get('unit', 'Stück')

                            consumable_data = {
                                'barcode': row_data['barcode'],
                                'name': row_data['name'],
                                'description': desc,
                                'category': cat,
                                'location': loc,
                                'quantity': quantity,
                                'unit': unit,
                                'deleted': False
                            }
                            
                            mongodb.update_one('consumables', 
                                             {'barcode': consumable_data['barcode']}, 
                                             {'$set': consumable_data}, 
                                             upsert=True)
                            imported_counts["Verbrauchsmaterial"] += 1
                    except Exception as e:
                        errors.append(f"Fehler in Verbrauchsmaterial Zeile {row_idx}: {e}")
        else:
            errors.append("Arbeitsblatt 'Verbrauchsmaterial' nicht gefunden.")

        # Erfolgs- und Fehlermeldungen anzeigen
        if errors:
            for error in errors:
                flash(error, 'error')
        
        if any(count > 0 for count in imported_counts.values()):
            success_msg = f"Import abgeschlossen: "
            success_parts = []
            for item_type, count in imported_counts.items():
                if count > 0:
                    success_parts.append(f"{count} {item_type}")
            success_msg += ", ".join(success_parts)
            flash(success_msg, 'success')
        return redirect(url_for('admin.system'))
    except Exception as e:
        logger.error(f"Fehler beim Importieren der Daten: {str(e)}", exc_info=True)
        flash(f'Fehler beim Importieren: {str(e)}', 'error')
        return redirect(url_for('admin.system'))

@bp.route('/users/toggle_active/<user_id>', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Benutzer aktivieren/deaktivieren"""
    try:
        user = mongodb.find_one('users', {'_id': ObjectId(user_id)})
        if not user:
            flash('Benutzer nicht gefunden', 'error')
            return redirect(url_for('admin.manage_users'))
        
        new_status = not user.get('is_active', True)
        mongodb.update_one('users', 
                          {'_id': ObjectId(user_id)}, 
                          {'$set': {'is_active': new_status}})
        
        status_text = 'aktiviert' if new_status else 'deaktiviert'
        flash(f'Benutzer {user["username"]} wurde {status_text}', 'success')
        
    except Exception as e:
        logger.error(f"Fehler beim Ändern des Benutzerstatus: {e}")
        flash('Fehler beim Ändern des Benutzerstatus', 'error')
    
    return redirect(url_for('admin.manage_users'))

@bp.route('/users/delete/<user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Benutzer löschen"""
    try:
        user = mongodb.find_one('users', {'_id': ObjectId(user_id)})
        if not user:
            flash('Benutzer nicht gefunden', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Verhindere Löschung des eigenen Accounts
        if str(user['_id']) == str(current_user.id):
            flash('Sie können Ihren eigenen Account nicht löschen', 'error')
            return redirect(url_for('admin.manage_users'))
        
        mongodb.delete_one('users', {'_id': ObjectId(user_id)})
        flash(f'Benutzer {user["username"]} wurde gelöscht', 'success')
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Benutzers: {e}")
        flash('Fehler beim Löschen des Benutzers', 'error')
    
    return redirect(url_for('admin.manage_users'))

@bp.app_context_processor
def inject_app_labels():
    """Injiziert die App-Labels in alle Templates"""
    return {'app_labels': get_app_labels()}

@bp.route('/upload-icon', methods=['POST'])
@login_required
@admin_required
def upload_icon():
    if 'icon' not in request.files:
        return jsonify({'success': False, 'error': 'Keine Datei hochgeladen'}), 400
    
    file = request.files['icon']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Keine Datei ausgewählt'}), 400
    
    if file:
        try:
            # Lese das Bild
            img = Image.open(file.stream)
            
            # Konvertiere zu RGB falls nötig (für PNG mit Transparenz)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            
            # Berechne die neue Größe (maximal 64x64 Pixel)
            max_size = (64, 64)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Erstelle einen eindeutigen Dateinamen
            filename = secure_filename(file.filename)
            base, ext = os.path.splitext(filename)
            unique_filename = f"{base}_{int(time.time())}.png"  # Immer als PNG speichern
            
            # Stelle sicher, dass das Verzeichnis existiert
            upload_dir = os.path.join(current_app.static_folder, 'uploads', 'icons')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Speichere die Datei
            file_path = os.path.join(upload_dir, unique_filename)
            img.save(file_path, 'PNG', quality=95, optimize=True)
            
            # Generiere den relativen Pfad für die Verwendung im Template
            relative_path = f"/static/uploads/icons/{unique_filename}"
            
            return jsonify({
                'success': True,
                'icon_path': relative_path
            })
            
        except Exception as e:
            logger.error(f"Fehler bei der Bildverarbeitung: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Fehler bei der Bildverarbeitung: {str(e)}'
            }), 500
    
    return jsonify({'success': False, 'error': 'Ungültige Datei'}), 400

@bp.route('/tools/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_tool_permanent(barcode):
    """Werkzeug endgültig löschen"""
    try:
        # Prüfe ob das Werkzeug existiert und gelöscht ist
        tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': True})
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden oder nicht gelöscht'
            }), 404
            
        # Lösche das Werkzeug endgültig
        mongodb.delete_one('tools', {'barcode': barcode})
        
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
            
        barcode = data['barcode']
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
        # Prüfe ob das Verbrauchsmaterial existiert und gelöscht ist
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': True})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden oder nicht gelöscht'}), 404
            
        # Führe das permanente Löschen durch
        mongodb.delete_one('consumables', {'barcode': barcode})
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial permanent gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Verbrauchsmaterials: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/workers/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_permanent(barcode):
    try:
        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeiter nicht gefunden'}), 404
            
        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings_count = mongodb.count_documents('lendings', {
            'worker_barcode': barcode, 
            'returned_at': None
        })
        if active_lendings_count > 0:
            return jsonify({'success': False, 'message': 'Mitarbeiter hat noch aktive Ausleihen'}), 400
            
        # Führe das permanente Löschen durch
        mongodb.delete_one('workers', {'barcode': barcode})
        return jsonify({'success': True, 'message': 'Mitarbeiter permanent gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Mitarbeiters: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/tickets/<ticket_id>')
@login_required
@admin_required
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

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ObjectId(ticket_id)})
    logging.info(f"DEBUG: auftrag_details für Ticket {ticket_id}: {auftrag_details}")
    
    # Hole die Materialliste
    material_list = mongodb.find('auftrag_material', {'ticket_id': ObjectId(ticket_id)})

    # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
    with mongodb.get_connection() as db:
        users = db.find('users', {'is_active': True})
        users = [dict(user) for user in users]

    # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
    assigned_users = mongodb.find('ticket_assignments', {'ticket_id': ObjectId(ticket_id)})

    # Hole alle Kategorien aus der ticket_categories Tabelle
    categories = mongodb.find('ticket_categories', {})
    categories = [c['name'] for c in categories]

    return render_template('admin/ticket_detail.html', 
                         ticket=ticket, 
                         notes=notes,
                         messages=messages,
                         users=users,
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
            'message': message  # Sende die Nachricht zurück
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
        print(f"DEBUG: Notiz-Anfrage für Ticket {ticket_id} erhalten")
        # Hole das Ticket
        ticket = mongodb.find_one('tickets', {'_id': ObjectId(ticket_id)})
        
        if not ticket:
            print(f"DEBUG: Ticket {ticket_id} nicht gefunden")
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Hole die Notiz
        if not request.is_json:
            print("DEBUG: Ungültiges Anfrageformat. JSON erwartet.")
            return jsonify({
                'success': False,
                'message': 'Ungültiges Anfrageformat. JSON erwartet.'
            }), 400

        data = request.get_json()
        note = data.get('note')
        
        if not note or not note.strip():
            print("DEBUG: Notiz ist leer")
            return jsonify({
                'success': False,
                'message': 'Notiz ist erforderlich'
            }), 400

        print(f"DEBUG: Notiz hinzufügen: {note}")
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
            'auftraggeber_intern': bool(data.get('auftraggeber_intern', False)),
            'auftraggeber_extern': bool(data.get('auftraggeber_extern', False)),
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
    ticket = mongodb.find_one('tickets', {'_id': ObjectId(id)})
    if not ticket:
        return abort(404)
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ObjectId(id)}) or {}
    material_list = mongodb.find('auftrag_material', {'ticket_id': ObjectId(id)}) or []

    # --- Auftragnehmer (Vorname Nachname) ---
    auftragnehmer_user = None
    if ticket.get('assigned_to'):
        auftragnehmer_user = User.get_by_username(ticket['assigned_to'])
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
        'intern_checkbox': intern_checkbox,
        'extern_checkbox': extern_checkbox,
        'auftraggeber_name': auftrag_details.get('auftraggeber_name', ''),
        'kontakt': auftrag_details.get('kontakt', ''),
        'auftragsbeschreibung': auftrag_details.get('auftragsbeschreibung', ''),
        'arbeiten_1': arbeiten_zeilen[0]['arbeiten'],
        'arbeitsstunden_1': arbeiten_zeilen[0]['arbeitsstunden'],
        'leistungskategorie_1': arbeiten_zeilen[0]['leistungskategorie'],
        'arbeiten_2': arbeiten_zeilen[1]['arbeiten'],
        'arbeitsstunden_2': arbeiten_zeilen[1]['arbeitsstunden'],
        'leistungskategorie_2': arbeiten_zeilen[1]['leistungskategorie'],
        'arbeiten_3': arbeiten_zeilen[2]['arbeiten'],
        'arbeitsstunden_3': arbeiten_zeilen[2]['arbeitsstunden'],
        'leistungskategorie_3': arbeiten_zeilen[2]['leistungskategorie'],
        'arbeiten_4': arbeiten_zeilen[3]['arbeiten'],
        'arbeitsstunden_4': arbeiten_zeilen[3]['arbeitsstunden'],
        'leistungskategorie_4': arbeiten_zeilen[3]['leistungskategorie'],
        'arbeiten_5': arbeiten_zeilen[4]['arbeiten'],
        'arbeitsstunden_5': arbeiten_zeilen[4]['arbeitsstunden'],
        'leistungskategorie_5': arbeiten_zeilen[4]['leistungskategorie'],
        'material_1': material_rows[0]['material'],
        'materialmenge_1': material_rows[0]['materialmenge'],
        'materialpreis_1': material_rows[0]['materialpreis'],
        'materialpreisges_1': material_rows[0]['materialpreisges'],
        'material_2': material_rows[1]['material'],
        'materialmenge_2': material_rows[1]['materialmenge'],
        'materialpreis_2': material_rows[1]['materialpreis'],
        'materialpreisges_2': material_rows[1]['materialpreisges'],
        'material_3': material_rows[2]['material'],
        'materialmenge_3': material_rows[2]['materialmenge'],
        'materialpreis_3': material_rows[2]['materialpreis'],
        'materialpreisges_3': material_rows[2]['materialpreisges'],
        'material_4': material_rows[3]['material'],
        'materialmenge_4': material_rows[3]['materialmenge'],
        'materialpreis_4': material_rows[3]['materialpreis'],
        'materialpreisges_4': material_rows[3]['materialpreisges'],
        'material_5': material_rows[4]['material'],
        'materialmenge_5': material_rows[4]['materialmenge'],
        'materialpreis_5': material_rows[4]['materialpreis'],
        'materialpreisges_5': material_rows[4]['materialpreisges'],
        'summe_material': f"{summe_material:.2f}".replace('.', ','),
        'arbeitspausch': f"{arbeitspausch:.2f}".replace('.', ','),
        'ubertrag': f"{ubertrag:.2f}".replace('.', ','),
        'zwischensumme': f"{zwischensumme:.2f}".replace('.', ','),
        'mwst': f"{mwst:.2f}".replace('.', ','),
        'gesamtsumme': f"{gesamtsumme:.2f}".replace('.', ',')
    }

    # --- Word-Dokument generieren ---
    try:
        # Lade das Template
        template_path = os.path.join(app.static_folder, 'word', 'btzauftrag.docx')
        doc = DocxTemplate(template_path)
        
        # Rendere das Dokument
        doc.render(context)
        
        # Speichere das generierte Dokument
        output_path = os.path.join(app.static_folder, 'uploads', f'ticket_{id}_export.docx')
        doc.save(output_path)
        
        # Sende das Dokument
        return send_file(output_path, as_attachment=True, download_name=f'ticket_{id}_export.docx')
        
    except Exception as e:
        logging.error(f"Fehler beim Generieren des Word-Dokuments: {str(e)}")
        flash('Fehler beim Generieren des Dokuments.', 'error')
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
            'auftraggeber_intern': data.get('auftraggeber_intern', ''),
            'auftraggeber_extern': data.get('auftraggeber_extern', ''),
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
    """Erstellt ein MongoDB-Backup (Platzhalter)"""
    # TODO: Implementiere echtes MongoDB-Backup
    return True

@bp.route('/tickets')
@login_required
@admin_required
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
    categories = list(mongodb.db.ticket_categories.find())
    
    return render_template('admin/tickets.html', 
                         tickets=tickets,
                         categories=categories,
                         title="Ticket-Verwaltung")

@bp.route('/manage_users')
@admin_required
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
@admin_required
def add_user():
    """Neuen Benutzer hinzufügen"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            password_confirm = request.form.get('password_confirm', '').strip()
            firstname = request.form.get('firstname', '').strip()
            lastname = request.form.get('lastname', '').strip()
            role = request.form.get('role', '').strip()
            
            # Validierung
            if not username or not password or not firstname or not lastname or not role:
                flash('Alle Pflichtfelder müssen ausgefüllt werden', 'error')
                return render_template('admin/user_form.html', 
                                     roles=['admin', 'mitarbeiter', 'anwender'],
                                     form_data=request.form)
            
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
            flash(f'Benutzer "{username}" erfolgreich erstellt', 'success')
            return redirect(url_for('admin.manage_users'))
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Benutzers: {e}")
            flash('Fehler beim Erstellen des Benutzers', 'error')
            return render_template('admin/user_form.html', 
                                 roles=['admin', 'mitarbeiter', 'anwender'],
                                 form_data=request.form)
    
    return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender'])

@bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Benutzer bearbeiten"""
    try:
        user = mongodb.find_one('users', {'_id': ObjectId(user_id)})
        if not user:
            flash('Benutzer nicht gefunden', 'error')
            return redirect(url_for('admin.manage_users'))
        
        if request.method == 'POST':
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
                             
    except Exception as e:
        logger.error(f"Fehler beim Laden des Benutzers: {e}")
        flash('Fehler beim Laden des Benutzers', 'error')
        return redirect(url_for('admin.manage_users'))

@bp.route('/notices')
@admin_required
def notices():
    """Notizen-Übersicht"""
    notices = mongodb.find('notices', {})
    return render_template('admin/notices.html', notices=notices)

@bp.route('/create_notice', methods=['GET', 'POST'])
@admin_required
def create_notice():
    """Neue Notiz erstellen"""
    if request.method == 'POST':
        # TODO: Implementiere Notiz-Erstellung
        flash('Notiz erfolgreich erstellt', 'success')
        return redirect(url_for('admin.notices'))
    return render_template('admin/notice_form.html')

@bp.route('/edit_notice/<id>', methods=['GET', 'POST'])
@admin_required
def edit_notice(id):
    """Notiz bearbeiten"""
    if request.method == 'POST':
        # TODO: Implementiere Notiz-Bearbeitung
        flash('Notiz erfolgreich aktualisiert', 'success')
        return redirect(url_for('admin.notices'))
    notice = mongodb.find_one('notices', {'_id': ObjectId(id)})
    return render_template('admin/notice_form.html', notice=notice)

@bp.route('/delete_notice/<id>', methods=['POST'])
@admin_required
def delete_notice(id):
    # TODO: Implementiere MongoDB-Version
    return jsonify({'success': True})

@bp.route('/upload_logo', methods=['POST'])
@admin_required
def upload_logo():
    """Logo hochladen"""
    # TODO: Implementiere Logo-Upload
    flash('Logo erfolgreich hochgeladen', 'success')
    return redirect(url_for('admin.server_settings'))

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
    # TODO: Implementiere MongoDB-Version
    return jsonify({'success': True})

@bp.route('/delete_ticket_category/<category>', methods=['POST'])
@admin_required
def delete_ticket_category(category):
    # TODO: Implementiere MongoDB-Version
    return jsonify({'success': True})

@bp.route('/system')
@admin_required
def system():
    """System-Einstellungen"""
    return render_template('admin/system.html')

# Abteilungsverwaltung
@bp.route('/departments')
@mitarbeiter_required
def get_departments():
    """Gibt alle Abteilungen zurück"""
    try:
        settings = mongodb.db.settings.find_one({'key': 'departments'})
        departments = settings.get('value', []) if settings else []
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
        name = request.form.get('department')  # Geändert von 'name' zu 'department'
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Prüfen ob Abteilung bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'departments'})
        if settings and name in settings.get('value', []):
            return jsonify({
                'success': False,
                'message': 'Diese Abteilung existiert bereits.'
            })

        # Abteilung zur Liste hinzufügen
        if settings:
            mongodb.db.settings.update_one(
                {'key': 'departments'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.db.settings.insert_one({
                'key': 'departments',
                'value': [name]
            })

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
        workers_with_dept = mongodb.db.workers.find_one({'department': name})
        if workers_with_dept:
            return jsonify({
                'success': False,
                'message': 'Die Abteilung kann nicht gelöscht werden, da sie noch von Mitarbeitern verwendet wird.'
            })

        # Abteilung aus der Liste entfernen
        mongodb.db.settings.update_one(
            {'key': 'departments'},
            {'$pull': {'value': name}}
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
        categories = settings.get('value', []) if settings else []
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
        name = request.form.get('category')  # Geändert von 'name' zu 'category'
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Prüfen ob Kategorie bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'categories'})
        if settings and name in settings.get('value', []):
            return jsonify({
                'success': False,
                'message': 'Diese Kategorie existiert bereits.'
            })

        # Kategorie zur Liste hinzufügen
        if settings:
            mongodb.db.settings.update_one(
                {'key': 'categories'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.db.settings.insert_one({
                'key': 'categories',
                'value': [name]
            })

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

        # Kategorie aus der Liste entfernen
        mongodb.db.settings.update_one(
            {'key': 'categories'},
            {'$pull': {'value': name}}
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
        locations = settings.get('value', []) if settings else []
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
        name = request.form.get('location')  # Geändert von 'name' zu 'location'
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Prüfen ob Standort bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'locations'})
        if settings and name in settings.get('value', []):
            return jsonify({
                'success': False,
                'message': 'Dieser Standort existiert bereits.'
            })

        # Standort zur Liste hinzufügen
        if settings:
            mongodb.db.settings.update_one(
                {'key': 'locations'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.db.settings.insert_one({
                'key': 'locations',
                'value': [name]
            })

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

        # Standort aus der Liste entfernen
        mongodb.db.settings.update_one(
            {'key': 'locations'},
            {'$pull': {'value': name}}
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