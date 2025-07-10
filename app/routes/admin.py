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
from app.utils.database_helpers import get_categories_from_settings, get_ticket_categories_from_settings, get_departments_from_settings, get_locations_from_settings
from docxtpl import DocxTemplate
from urllib.parse import unquote
import pandas as pd
import tempfile
from typing import Union

# Import der neuen Services
from app.services.admin_dashboard_service import AdminDashboardService
from app.services.admin_user_service import AdminUserService
from app.services.admin_backup_service import AdminBackupService
from app.services.admin_system_service import AdminSystemService
from app.services.admin_email_service import AdminEmailService
from app.services.admin_notification_service import AdminNotificationService
from app.services.admin_ticket_service import AdminTicketService
from app.utils.id_helpers import convert_id_for_query, find_document_by_id, find_user_by_id

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/admin')

# Stelle sicher, dass die Standard-Einstellungen beim Start der App vorhanden sind
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

def create_excel(data, columns):
    """Erstellt eine Excel-Datei aus Daten"""
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Header
    for col, header in enumerate(columns, 1):
        ws.cell(row=1, column=col, value=header)
    
    # Daten
    for row, item in enumerate(data, 2):
        for col, key in enumerate(columns.keys(), 1):
            value = item.get(key, '')
            ws.cell(row=row, column=col, value=value)
    
    # Speichern
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def create_multi_sheet_excel(data_dict):
    """Erstellt eine Excel-Datei mit mehreren Arbeitsblättern"""
    wb = openpyxl.Workbook()
    
    # Entferne das Standard-Arbeitsblatt
    wb.remove(wb.active)
    
    for sheet_name, data in data_dict.items():
        ws = wb.create_sheet(title=sheet_name)
        
        if data and len(data) > 0:
            # Header aus den ersten Datenzeilen
            headers = list(data[0].keys())
            
            # Header schreiben
            for col, header in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=header)
            
            # Daten schreiben
            for row, item in enumerate(data, 2):
                for col, key in enumerate(headers, 1):
                    value = item.get(key, '')
                    ws.cell(row=row, column=col, value=value)
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

@bp.route('/')
@mitarbeiter_required
def index():
    """Admin-Startseite"""
    return redirect(url_for('admin.dashboard'))

@bp.route('/dashboard')
@mitarbeiter_required
def dashboard():
    """Admin-Dashboard"""
    try:
        # Verwende den AdminDashboardService für alle Dashboard-Daten
        recent_activity = AdminDashboardService.get_recent_activity()
        material_usage = AdminDashboardService.get_material_usage()
        warnings = AdminDashboardService.get_warnings()
        backup_info = AdminDashboardService.get_backup_info()
        consumables_forecast = AdminDashboardService.get_consumables_forecast()
        consumable_trend = AdminDashboardService.get_consumable_trend()
        
        # Hole zusätzliche Statistiken
        total_tools = mongodb.count_documents('tools', {'deleted': {'$ne': True}})
        total_consumables = mongodb.count_documents('consumables', {'deleted': {'$ne': True}})
        total_workers = mongodb.count_documents('workers', {'deleted': {'$ne': True}})
        total_tickets = mongodb.count_documents('tickets', {})
        
        # Tool-Statistiken
        tool_stats = {
            'total': total_tools,
            'available': mongodb.count_documents('tools', {'status': 'verfügbar', 'deleted': {'$ne': True}}),
            'lent': mongodb.count_documents('tools', {'status': 'ausgeliehen', 'deleted': {'$ne': True}}),
            'defect': mongodb.count_documents('tools', {'status': 'defekt', 'deleted': {'$ne': True}})
        }
        
        # Consumable-Statistiken
        consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
        sufficient = 0
        warning = 0
        critical = 0
        
        for consumable in consumables:
            if consumable['quantity'] >= consumable.get('warning_threshold', 10):
                sufficient += 1
            elif consumable['quantity'] >= consumable.get('critical_threshold', 5):
                warning += 1
            else:
                critical += 1
        
        consumable_stats = {
            'total': total_consumables,
            'sufficient': sufficient,
            'warning': warning,
            'critical': critical
        }
        
        # Worker-Statistiken
        workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}))
        worker_stats = {
            'total': total_workers,
            'by_department': []
        }
        
        # Gruppiere nach Abteilung
        dept_counts = {}
        for worker in workers:
            dept = worker.get('department', 'Ohne Abteilung')
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        for dept, count in dept_counts.items():
            worker_stats['by_department'].append({
                'name': dept,
                'count': count
            })
        
        # Tool-Warnungen
        tool_warnings = []
        defect_tools = list(mongodb.find('tools', {'status': 'defekt', 'deleted': {'$ne': True}}))
        for tool in defect_tools:
            tool_warnings.append({
                'name': tool['name'],
                'status': 'Defekt',
                'severity': 'error'
            })
        
        # Consumable-Warnungen
        consumable_warnings = []
        low_stock_consumables = list(mongodb.find('consumables', {
            'quantity': {'$lt': 5},
            'deleted': {'$ne': True}
        }))
        for consumable in low_stock_consumables:
            consumable_warnings.append({
                'message': f"{consumable['name']} (Bestand: {consumable['quantity']})",
                'type': 'error' if consumable['quantity'] == 0 else 'warning',
                'icon': 'times' if consumable['quantity'] == 0 else 'exclamation-triangle'
            })
        
        # Aktuelle Ausleihen
        current_lendings = list(mongodb.find('lendings', {'returned_at': None}))
        
        # Verarbeite Ausleihen für Anzeige
        processed_lendings = []
        for lending in current_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
            
            if tool and worker:
                processed_lendings.append({
                    'tool_name': tool['name'],
                    'worker_name': f"{worker['firstname']} {worker['lastname']}",
                    'lent_at': lending['lent_at'],
                    'days_lent': (datetime.now() - lending['lent_at']).days
                })
        
        # Sortiere nach Ausleihdatum (älteste zuerst)
        processed_lendings.sort(key=lambda x: x['lent_at'])
        
        return render_template('admin/dashboard.html',
                             recent_activity=recent_activity,
                             material_usage=material_usage,
                             warnings=warnings,
                             backup_info=backup_info,
                             consumables_forecast=consumables_forecast,
                             consumable_trend=consumable_trend,
                             total_tools=total_tools,
                             total_consumables=total_consumables,
                             total_workers=total_workers,
                             total_tickets=total_tickets,
                             current_lendings=processed_lendings,
                             tool_stats=tool_stats,
                             consumable_stats=consumable_stats,
                             worker_stats=worker_stats,
                             tool_warnings=tool_warnings,
                             consumable_warnings=consumable_warnings)
                             
    except Exception as e:
        logger.error(f"Fehler beim Laden des Admin-Dashboards: {str(e)}")
        flash('Fehler beim Laden des Dashboards', 'error')
        return render_template('admin/dashboard.html',
                             recent_activity=[],
                             material_usage={'usage_data': [], 'period_days': 30},
                             warnings={'defect_tools': [], 'overdue_lendings': [], 'low_stock_consumables': []},
                             backup_info={'backups': [], 'total_count': 0, 'total_size_mb': 0},
                             consumables_forecast=[],
                             consumable_trend={'labels': [], 'datasets': []},
                             total_tools=0,
                             total_consumables=0,
                             total_workers=0,
                             total_tickets=0,
                             current_lendings=[],
                             tool_stats={'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                             consumable_stats={'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                             worker_stats={'total': 0, 'by_department': []},
                             tool_warnings=[],
                             consumable_warnings=[])

@bp.route('/manual-lending', methods=['GET', 'POST'])
@mitarbeiter_required
def manual_lending():
    """Manuelle Ausleihe/Rückgabe"""
    if request.method == 'POST':
        logger.info("POST-Anfrage für manuelle Ausleihe empfangen")
        
        try:
            # JSON-Daten für manuelle Ausleihe
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'message': 'Keine Daten empfangen'}), 400
            
            # Validiere erforderliche Felder
            required_fields = ['item_barcode', 'worker_barcode', 'action', 'item_type']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'message': f'Feld {field} ist erforderlich'}), 400
            
            # Hole Daten aus JSON
            item_barcode = data.get('item_barcode', '').strip()
            worker_barcode = data.get('worker_barcode', '').strip()
            action = data.get('action', '').strip()
            item_type = data.get('item_type', '').strip()
            quantity = data.get('quantity', 1)
            
            if not item_barcode or not worker_barcode or not action or not item_type:
                return jsonify({'success': False, 'message': 'Alle Felder sind erforderlich'}), 400
            
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
        
        # Gelöschte Tickets
        tickets = mongodb.find('tickets', {'deleted': True}, sort=[('deleted_at', -1)])
        
        return render_template('admin/trash.html',
                           tools=tools,
                           consumables=consumables,
                           workers=workers,
                           tickets=tickets)
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
                             
        elif type == 'ticket':
            # Prüfe ob das Ticket existiert
            ticket = mongodb.find_one('tickets', {'_id': convert_id_for_query(decoded_barcode), 'deleted': True})
            
            if not ticket:
                return jsonify({
                    'success': False,
                    'message': 'Ticket nicht gefunden'
                }), 404
                
            # Stelle das Ticket wieder her
            mongodb.update_one('tickets', 
                             {'_id': convert_id_for_query(decoded_barcode)}, 
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
    ticket = mongodb.find_one('tickets', {'_id': convert_id_for_query(ticket_id)})
    
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
    notes = mongodb.find('ticket_notes', {'ticket_id': convert_id_for_query(ticket_id)})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': convert_id_for_query(ticket_id)})
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
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': convert_id_for_query(ticket_id)})
    logging.info(f"DEBUG: auftrag_details für Ticket {ticket_id}: {auftrag_details}")
    
    # Hole die Materialliste
    material_list = mongodb.find('auftrag_material', {'ticket_id': convert_id_for_query(ticket_id)})

    # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
    users = mongodb.find('users', {'is_active': True})
    users = [dict(user) for user in users]

    # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
    assigned_users = mongodb.find('ticket_assignments', {'ticket_id': convert_id_for_query(ticket_id)})

    # Hole alle Kategorien aus der settings Collection
    categories = get_ticket_categories_from_settings()

    # Hole Arbeitszeiten
    arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': convert_id_for_query(ticket_id)}))
    
    # Hole Notizen
    notes = list(mongodb.find('ticket_notes', {'ticket_id': convert_id_for_query(ticket_id)}, sort=[('created_at', -1)]))
    
    # Hole Nachrichten
    messages = list(mongodb.find('ticket_messages', {'ticket_id': convert_id_for_query(ticket_id)}, sort=[('created_at', -1)]))
    
    # Hole alle Mitarbeiter für Zuweisung
    workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}, sort=[('lastname', 1)]))
    
    # Hole alle Abteilungen
    departments = get_departments_from_settings()
    
    # Hole alle Standorte
    locations = get_locations_from_settings()

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
                         now=datetime.now(),
                         arbeit_list=arbeit_list)

@bp.route('/tickets/<ticket_id>/message', methods=['POST'])
@login_required
@admin_required
def add_ticket_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu."""
    try:
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

        # Verwende den AdminTicketService
        success, result_message = AdminTicketService.add_ticket_message(ticket_id, message, 'message')
        
        if success:
            return jsonify({
                'success': True,
                'message': {
                    'sender': current_user.username,
                    'text': message,
                    'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result_message
            }), 400

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
    """Fügt eine neue Notiz zu einem Ticket hinzu"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        note_text = data.get('note', '').strip()
        
        if not note_text:
            return jsonify({'success': False, 'message': 'Notiz darf nicht leer sein'}), 400

        # Erstelle die Notiz
        note_data = {
            'ticket_id': convert_id_for_query(ticket_id),
            'note': note_text,
            'created_by': current_user.username,
            'created_at': datetime.now()
        }
        
        result = mongodb.insert_one('ticket_notes', note_data)
        
        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Speichern der Notiz'}), 500

        return jsonify({
            'success': True,
            'message': 'Notiz erfolgreich hinzugefügt',
            'note': {
                'id': str(result),
                'text': note_text,
                'created_by': current_user.username,
                'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Notiz: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id
        
        # Aktualisiere die Auftragsdetails
        if not mongodb.update_one('auftrag_details', {'ticket_id': ticket_id_for_update}, {'$set': auftrag_details}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Auftragsdetails'})
        
        # Aktualisiere die Materialliste
        material_list = data.get('material_list', [])
        if not mongodb.update_many('auftrag_material', {'ticket_id': ticket_id_for_update}, {'$set': {'menge': m['menge'], 'einzelpreis': m['einzelpreis']} for m in material_list}):
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
        # Verwende den AdminTicketService
        success, message, file_path = AdminTicketService.export_ticket_as_word(id)
        
        if success and file_path:
            # Sende das Dokument
            ticket = find_document_by_id('tickets', id)
            ticket_number = ticket.get('ticket_number', id) if ticket else id
            return send_file(file_path, as_attachment=True, download_name=f'ticket_{ticket_number}_export.docx')
        else:
            flash(message, 'error')
            return redirect(url_for('admin.ticket_detail', ticket_id=id))
        
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
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id
        
        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        
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
            'ticket_id': ticket_id_for_update,
            'auftrag_an': data.get('auftrag_an', ''),
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': data.get('auftraggeber_typ') == 'intern',
            'auftraggeber_extern': data.get('auftraggeber_typ') == 'extern',
            'beschreibung': data.get('beschreibung', ''),
            'prioritaet': data.get('prioritaet', 'normal'),
            'deadline': data.get('deadline'),
            'updated_at': datetime.now()
        }
        
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id
        
        if not mongodb.update_one('auftrag_details', {'ticket_id': ticket_id_for_update}, {'$set': auftrag_details}):
            mongodb.insert_one('auftrag_details', auftrag_details)
        
        # Materialliste aktualisieren
        material_list = data.get('material_list', [])
        if material_list:
            # Lösche alte Materialeinträge
            mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id_for_update})
            
            # Füge neue Materialeinträge hinzu
            for material in material_list:
                material['ticket_id'] = ticket_id_for_update
                material['created_at'] = datetime.now()
                mongodb.insert_one('auftrag_material', material)
        
        # Ticket selbst aktualisieren
        ticket_update = {
            'title': data.get('title', ticket.get('title', '')),
            'description': data.get('description', ticket.get('description', '')),
            'priority': data.get('prioritaet', ticket.get('priority', 'normal')),
            'updated_at': datetime.now()
        }
        
        # Verarbeite estimated_time (wird in Minuten gespeichert)
        if 'estimated_time' in data:
            estimated_time = data['estimated_time']
            if estimated_time is not None and estimated_time != '':
                ticket_update['estimated_time'] = float(estimated_time)
            else:
                ticket_update['estimated_time'] = None
        
        # Verarbeite category
        if 'category' in data:
            ticket_update['category'] = data['category']
        
        # Verarbeite due_date
        if 'due_date' in data:
            due_date = data['due_date']
            if due_date:
                try:
                    # Versuche verschiedene Datumsformate zu parsen
                    if 'T' in due_date:
                        due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                    else:
                        due_date = datetime.strptime(due_date, '%Y-%m-%d')
                    ticket_update['due_date'] = due_date
                except ValueError:
                    return jsonify({'success': False, 'message': 'Ungültiges Datumsformat'}), 400
            else:
                ticket_update['due_date'] = None
        
        if not mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': ticket_update}):
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



@bp.route('/manage_users')
@mitarbeiter_required
def manage_users():
    """Benutzerverwaltung"""
    try:
        users = AdminUserService.get_all_users()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Benutzer: {e}")
        flash('Fehler beim Laden der Benutzer', 'error')
        return render_template('admin/users.html', users=[])

@bp.route('/add_user', methods=['GET', 'POST'])
@mitarbeiter_required
def add_user():
    """Neuen Benutzer hinzufügen"""
    if request.method == 'POST':
        # Prüfe Berechtigung für Admin-Rolle
        role = request.form.get('role', '').strip()
        if current_user.role != 'admin' and role == 'admin':
            flash('Sie dürfen keine Admin-Benutzer anlegen.', 'error')
            return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'], form_data=request.form)
        
        # Verwende Services für Validierung und E-Mail
        from app.services.validation_service import ValidationService
        from app.services.email_service import EmailService
        from app.services.utility_service import UtilityService
        
        form_data = UtilityService.get_form_data_dict(request.form)
        
        # Validierung mit ValidationService
        is_valid, errors, processed_data = ValidationService.validate_user_form(form_data, is_edit=False)
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/user_form.html', 
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                                 form_data=request.form)
        
        # Automatische Passwort-Generierung wenn keines eingegeben wurde
        if not processed_data['password']:
            password = ValidationService.generate_secure_password()
            processed_data['password'] = password
            processed_data['password_confirm'] = password
        
        # Benutzer erstellen mit AdminUserService
        user_data = {
            'username': processed_data['username'],
            'password': processed_data['password'],
            'role': processed_data['role'],
            'email': processed_data['email'] if processed_data['email'] else '',
            'firstname': processed_data['firstname'],
            'lastname': processed_data['lastname'],
            'timesheet_enabled': processed_data['timesheet_enabled'],
            'is_active': True
        }
        
        success, message, user_id = AdminUserService.create_user(user_data)
        
        if success:
            # E-Mail mit Passwort versenden (falls E-Mail vorhanden)
            if processed_data['email']:
                try:
                    email_sent = EmailService.send_new_user_email(
                        processed_data['email'],
                        processed_data['username'],
                        processed_data['password'],
                        processed_data['firstname']
                    )
                    
                    if email_sent:
                        flash(f'{message} Passwort wurde per E-Mail an {processed_data["email"]} gesendet.', 'success')
                    else:
                        flash(f'{message} E-Mail konnte nicht versendet werden.', 'warning')
                except Exception as e:
                    logger.error(f"Fehler beim Versenden der E-Mail: {e}")
                    flash(f'{message} E-Mail konnte nicht versendet werden.', 'warning')
            else:
                flash(f'{message} Passwort: {processed_data["password"]}', 'success')
            
            return redirect(url_for('admin.manage_users'))
        else:
            flash(message, 'error')
            return render_template('admin/user_form.html', 
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                                 form_data=request.form)
    
    return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])

@bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@mitarbeiter_required
def edit_user(user_id):
    """Benutzer bearbeiten"""
    user = AdminUserService.get_user_by_id(user_id)
    
    if not user:
        flash('Benutzer nicht gefunden', 'error')
        return redirect(url_for('admin.manage_users'))
    
    if current_user.role != 'admin' and user.get('role') == 'admin':
        flash('Sie dürfen keine Admin-Benutzer bearbeiten.', 'error')
        return redirect(url_for('admin.manage_users'))
    
    # GET-Request: Zeige das Formular mit den aktuellen Daten
    if request.method == 'GET':
        return render_template('admin/user_form.html', 
                             user=user,
                             roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])
    
    # POST-Request: Verarbeite die Formulardaten
    try:
        # Verwende Services für Validierung
        from app.services.validation_service import ValidationService
        from app.services.utility_service import UtilityService
        
        form_data = UtilityService.get_form_data_dict(request.form)
        
        # Validierung mit ValidationService
        is_valid, errors, processed_data = ValidationService.validate_user_form(form_data, is_edit=True)
        
        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/user_form.html', 
                                 user=user,
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])
        
        # Benutzer aktualisieren mit AdminUserService
        user_data = {
            'username': processed_data['username'],
            'role': processed_data['role'],
            'email': processed_data['email'] if processed_data['email'] else '',
            'firstname': processed_data['firstname'],
            'lastname': processed_data['lastname'],
            'timesheet_enabled': processed_data['timesheet_enabled']
        }
        
        # Passwort hinzufügen falls angegeben
        if processed_data['password']:
            user_data['password'] = processed_data['password']
        
        success, message = AdminUserService.update_user(user_id, user_data)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('admin.manage_users'))
        else:
            flash(message, 'error')
            return render_template('admin/user_form.html', 
                                 user=user,
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Benutzers: {e}")
        flash('Fehler beim Aktualisieren des Benutzers', 'error')
        return render_template('admin/user_form.html', 
                             user=user,
                             roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])
    
    return render_template('admin/user_form.html', 
                         user=user,
                         roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])

@bp.route('/notices')
@admin_required
def notices():
    """Notizen-Übersicht"""
    notices = AdminNotificationService.get_all_notices()
    return render_template('admin/notices.html', notices=notices)

@bp.route('/create_notice', methods=['GET', 'POST'])
@admin_required
def create_notice():
    """Neue Notiz erstellen"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        notice_type = request.form.get('type', 'info')
        
        success, message = AdminNotificationService.create_notice(title, content, notice_type)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('admin.notices'))
    
    return render_template('admin/notice_form.html')

@bp.route('/edit_notice/<id>', methods=['GET', 'POST'])
@admin_required
def edit_notice(id):
    """Notiz bearbeiten"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        notice_type = request.form.get('type', 'info')
        
        success, message = AdminNotificationService.update_notice(id, title, content, notice_type)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('admin.notices'))
    
    notice = AdminNotificationService.get_notice_by_id(id)
    if not notice:
        flash('Notiz nicht gefunden', 'error')
        return redirect(url_for('admin.notices'))
    
    return render_template('admin/notice_form.html', notice=notice)

@bp.route('/delete_notice/<id>', methods=['POST'])
@admin_required
def delete_notice(id):
    """Löscht einen Hinweis"""
    try:
        success, message = AdminNotificationService.delete_notice(id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
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
            return redirect(url_for('tickets.create'))

        # Prüfen ob Ticket-Kategorie bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
        if settings and name in settings.get('value', []):
            flash('Diese Ticket-Kategorie existiert bereits.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie zur Liste hinzufügen
        if settings:
            mongodb.update_one_array(
                'settings',
                {'key': 'ticket_categories'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.insert_one('settings', {
                'key': 'ticket_categories',
                'value': [name]
            })

        flash('Ticket-Kategorie erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/delete_ticket_category/<category>', methods=['POST'])
@admin_required
def delete_ticket_category(category):
    """Löscht eine Ticket-Kategorie"""
    try:
        # Überprüfen, ob die Ticket-Kategorie in Verwendung ist
        tickets_with_category = mongodb.db.tickets.find_one({'category': category})
        if tickets_with_category:
            flash('Die Ticket-Kategorie kann nicht gelöscht werden, da sie noch von Tickets verwendet wird.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie aus der Liste entfernen
        mongodb.update_one_array(
            'settings',
            {'key': 'ticket_categories'},
            {'$pull': {'value': category}}
        )
        
        flash('Ticket-Kategorie erfolgreich gelöscht.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/system', methods=['GET', 'POST'])
@admin_required
def system():
    """System-Einstellungen"""
    try:
        if request.method == 'POST':
            # Begriffe & Icons verarbeiten
            app_labels = {
                'tools': {
                    'name': request.form.get('label_tools_name', 'Werkzeuge'),
                    'icon': request.form.get('label_tools_icon', 'fas fa-tools')
                },
                'consumables': {
                    'name': request.form.get('label_consumables_name', 'Verbrauchsmaterial'),
                    'icon': request.form.get('label_consumables_icon', 'fas fa-box')
                },
                'tickets': {
                    'name': request.form.get('label_tickets_name', 'Tickets'),
                    'icon': request.form.get('label_tickets_icon', 'fas fa-ticket-alt')
                }
            }
            
            success, message = AdminSystemService.save_app_labels(app_labels)
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
            
            return redirect(url_for('admin.system'))
        
        # Hole alle verfügbaren Logos
        logos = AdminSystemService.get_available_logos()
        
        # Hole aktuelle Einstellungen und App-Labels
        settings, app_labels = AdminSystemService.get_system_data()
        
        return render_template('admin/server-settings.html', 
                             logos=logos, 
                             settings=settings,
                             app_labels=app_labels)
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
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('department', '').strip()
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
        
        # Speichere als Array mit robuster Methode
        try:
            mongodb.update_one(
                'settings',
                {'key': 'departments'},
                {'value': current_departments},
                upsert=True
            )
        except Exception as db_error:
            logger.error(f"Datenbankfehler beim Speichern der Abteilung: {str(db_error)}")
            # Fallback: Versuche es mit update_one_array
            mongodb.update_one_array(
                'settings',
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
        # URL-dekodieren
        decoded_name = unquote(name)
        
        # Überprüfen, ob die Abteilung in Verwendung ist
        workers_with_department = mongodb.db.workers.find_one({'department': decoded_name})
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
        if decoded_name in current_departments:
            current_departments.remove(decoded_name)
            try:
                mongodb.update_one(
                    'settings',
                    {'key': 'departments'},
                    {'value': current_departments},
                    upsert=True
                )
            except Exception as db_error:
                logger.error(f"Datenbankfehler beim Löschen der Abteilung: {str(db_error)}")
                # Fallback: Versuche es mit update_one_array
                mongodb.update_one_array(
                    'settings',
                    {'key': 'departments'},
                    {'$set': {'value': current_departments}},
                    upsert=True
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
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('category', '').strip()
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
        
        # Speichere als Array mit robuster Methode
        try:
            mongodb.update_one(
                'settings',
                {'key': 'categories'},
                {'value': current_categories},
                upsert=True
            )
        except Exception as db_error:
            logger.error(f"Datenbankfehler beim Speichern der Kategorie: {str(db_error)}")
            # Fallback: Versuche es mit update_one_array
            mongodb.update_one_array(
                'settings',
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
        # URL-dekodieren
        decoded_name = unquote(name)
        
        # Überprüfen, ob die Kategorie in Verwendung ist
        tools_with_category = mongodb.db.tools.find_one({'category': decoded_name})
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
        if decoded_name in current_categories:
            current_categories.remove(decoded_name)
            try:
                mongodb.update_one(
                    'settings',
                    {'key': 'categories'},
                    {'value': current_categories},
                    upsert=True
                )
            except Exception as db_error:
                logger.error(f"Datenbankfehler beim Löschen der Kategorie: {str(db_error)}")
                # Fallback: Versuche es mit update_one_array
                mongodb.update_one_array(
                    'settings',
                    {'key': 'categories'},
                    {'$set': {'value': current_categories}},
                    upsert=True
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
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('location', '').strip()
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
        
        # Speichere als Array mit robuster Methode
        try:
            mongodb.update_one(
                'settings',
                {'key': 'locations'},
                {'value': current_locations},
                upsert=True
            )
        except Exception as db_error:
            logger.error(f"Datenbankfehler beim Speichern des Standorts: {str(db_error)}")
            # Fallback: Versuche es mit update_one_array
            mongodb.update_one_array(
                'settings',
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
        # URL-dekodieren
        decoded_name = unquote(name)
        
        # Überprüfen, ob der Standort in Verwendung ist
        tools_with_location = mongodb.db.tools.find_one({'location': decoded_name})
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
        if decoded_name in current_locations:
            current_locations.remove(decoded_name)
            try:
                mongodb.update_one(
                    'settings',
                    {'key': 'locations'},
                    {'value': current_locations},
                    upsert=True
                )
            except Exception as db_error:
                logger.error(f"Datenbankfehler beim Löschen des Standorts: {str(db_error)}")
                # Fallback: Versuche es mit update_one_array
                mongodb.update_one_array(
                    'settings',
                    {'key': 'locations'},
                    {'$set': {'value': current_locations}},
                    upsert=True
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

# Ticket-Kategorienverwaltung (JSON-API)
@bp.route('/ticket_categories')
@mitarbeiter_required
def get_ticket_categories():
    """Gibt alle Ticket-Kategorien zurück"""
    try:
        settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
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
        logger.error(f"Fehler beim Abrufen der Ticket-Kategorien: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Ticket-Kategorien'
        })

@bp.route('/ticket_categories/add', methods=['POST'])
@admin_required
def add_ticket_category_json():
    """Fügt eine neue Ticket-Kategorie hinzu (JSON-API)"""
    try:
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('category', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Prüfen ob Ticket-Kategorie bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
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
                'message': 'Diese Ticket-Kategorie existiert bereits.'
            })

        # Ticket-Kategorie zur Liste hinzufügen
        current_categories.append(name)
        
        # Speichere als Array mit robuster Methode
        try:
            mongodb.update_one(
                'settings',
                {'key': 'ticket_categories'},
                {'value': current_categories},
                upsert=True
            )
        except Exception as db_error:
            logger.error(f"Datenbankfehler beim Speichern der Ticket-Kategorie: {str(db_error)}")
            # Fallback: Versuche es mit update_one_array
            mongodb.update_one_array(
                'settings',
                {'key': 'ticket_categories'},
                {'$set': {'value': current_categories}},
                upsert=True
            )

        return jsonify({
            'success': True,
            'message': 'Ticket-Kategorie erfolgreich hinzugefügt.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/ticket_categories/delete/<name>', methods=['POST'])
@admin_required
def delete_ticket_category_json(name):
    """Löscht eine Ticket-Kategorie (JSON-API)"""
    try:
        # URL-dekodieren
        decoded_name = unquote(name)
        
        # Überprüfen, ob die Ticket-Kategorie in Verwendung ist
        tickets_with_category = mongodb.db.tickets.find_one({'category': decoded_name})
        if tickets_with_category:
            return jsonify({
                'success': False,
                'message': 'Die Ticket-Kategorie kann nicht gelöscht werden, da sie noch von Tickets verwendet wird.'
            })

        # Ticket-Kategorie aus der Liste entfernen
        try:
            mongodb.update_one_array(
                'settings',
                {'key': 'ticket_categories'},
                {'$pull': {'value': decoded_name}}
            )
        except Exception as db_error:
            logger.error(f"Datenbankfehler beim Löschen der Ticket-Kategorie: {str(db_error)}")
            # Fallback: Lade alle Kategorien und entferne die gewünschte
            settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
            if settings and 'value' in settings:
                current_categories = settings['value']
                if isinstance(current_categories, list) and decoded_name in current_categories:
                    current_categories.remove(decoded_name)
                    mongodb.update_one(
                        'settings',
                        {'key': 'ticket_categories'},
                        {'value': current_categories},
                        upsert=True
                    )
        
        return jsonify({
            'success': True,
            'message': 'Ticket-Kategorie erfolgreich gelöscht.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

# Legacy-Routen für Ticket-Kategorien (für Kompatibilität)
@bp.route('/add_ticket_category', methods=['POST'])
@admin_required
def add_ticket_category_legacy():
    """Fügt eine neue Ticket-Kategorie hinzu (Legacy-Route)"""
    try:
        name = request.form.get('category')
        if not name:
            flash('Bitte geben Sie einen Namen ein.', 'error')
            return redirect(url_for('tickets.create'))

        # Prüfen ob Ticket-Kategorie bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
        if settings and name in settings.get('value', []):
            flash('Diese Ticket-Kategorie existiert bereits.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie zur Liste hinzufügen
        if settings:
            mongodb.update_one_array(
                'settings',
                {'key': 'ticket_categories'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.insert_one('settings', {
                'key': 'ticket_categories',
                'value': [name]
            })

        flash('Ticket-Kategorie erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/delete_ticket_category/<category>', methods=['POST'])
@admin_required
def delete_ticket_category_legacy(category):
    """Löscht eine Ticket-Kategorie (Legacy-Route)"""
    try:
        # Überprüfen, ob die Ticket-Kategorie in Verwendung ist
        tickets_with_category = mongodb.db.tickets.find_one({'category': category})
        if tickets_with_category:
            flash('Die Ticket-Kategorie kann nicht gelöscht werden, da sie noch von Tickets verwendet wird.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie aus der Liste entfernen
        mongodb.update_one_array(
            'settings',
            {'key': 'ticket_categories'},
            {'$pull': {'value': category}}
        )
        
        flash('Ticket-Kategorie erfolgreich gelöscht.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/backup/list')
@mitarbeiter_required
def backup_list():
    """Gibt eine Liste der verfügbaren Backups zurück"""
    try:
        backups = AdminBackupService.get_backup_list()
        return jsonify({
            'status': 'success',
            'backups': backups
        })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Backups: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Laden der Backups: {str(e)}'
        }), 500

@bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Erstellt ein neues Backup der aktuellen Datenbank"""
    try:
        success, message, backup_filename = AdminBackupService.create_backup()
        
        if success:
            # E-Mail-Versand (optional)
            email_recipient = request.form.get('email_recipient', '').strip()
            if email_recipient and backup_filename:
                try:
                    from app.utils.email_utils import send_backup_mail
                    from app.utils.backup_manager import backup_manager
                    backup_path = backup_manager.get_backup_path(backup_filename)
                    send_backup_mail(email_recipient, str(backup_path))
                    return jsonify({
                        'status': 'success',
                        'message': f'{message} und an {email_recipient} gesendet',
                        'filename': backup_filename
                    })
                except Exception as e:
                    logger.error(f"Fehler beim E-Mail-Versand: {str(e)}")
                    return jsonify({
                        'status': 'success',
                        'message': f'{message}, aber E-Mail-Versand fehlgeschlagen',
                        'filename': backup_filename
                    })
            else:
                return jsonify({
                    'status': 'success',
                    'message': message,
                    'filename': backup_filename
                })
        else:
            return jsonify({
                'status': 'error',
                'message': message
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
            logger.warning("Backup-Upload: Keine Datei in request.files gefunden")
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400
            
        file = request.files['backup_file']
        if file.filename == '':
            logger.warning("Backup-Upload: Leerer Dateiname")
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400
            
        # Prüfe Dateityp
        if not file.filename.endswith('.json'):
            logger.warning(f"Backup-Upload: Ungültiger Dateityp: {file.filename}")
            return jsonify({
                'status': 'error',
                'message': 'Ungültiger Dateityp. Bitte eine .json-Datei hochladen.'
            }), 400
        
        # Prüfe Dateigröße
        file.seek(0, 2)  # Gehe zum Ende der Datei
        file_size = file.tell()
        file.seek(0)  # Zurück zum Anfang
        
        logger.info(f"Backup-Upload: Datei {file.filename}, Größe: {file_size} bytes")
        
        if file_size == 0:
            logger.warning("Backup-Upload: Datei ist leer")
            return jsonify({
                'status': 'error',
                'message': 'Die hochgeladene Datei ist leer. Bitte wählen Sie eine gültige Backup-Datei aus.'
            }), 400
        
        success, message = AdminBackupService.upload_backup(file)
        
        if success:
            logger.info("Backup-Upload: Backup erfolgreich wiederhergestellt")
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            logger.error("Backup-Upload: Fehler beim Wiederherstellen des Backups")
            return jsonify({
                'status': 'error',
                'message': message
            }), 500
            
    except Exception as e:
        logger.error(f"Fehler beim Hochladen des Backups: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Hochladen des Backups: {str(e)}'
        }), 500

@bp.route('/backup/restore/<filename>', methods=['POST'])
@admin_required
def restore_backup(filename):
    """Stellt ein Backup wieder her"""
    try:
        success, message, validation_info = AdminBackupService.restore_backup(filename)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'validation_info': validation_info
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
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
        backup_path = AdminBackupService.get_backup_path(filename)
        
        if not backup_path or not backup_path.exists():
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

@bp.route('/backup/test/<filename>')
@admin_required
def test_backup(filename):
    """Testet ein Backup ohne es wiederherzustellen"""
    try:
        success, result = AdminBackupService.test_backup(filename)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Backup-Test erfolgreich',
                'data': result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result
            }), 400
            
    except Exception as e:
        logger.error(f"Fehler beim Testen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Testen des Backups: {str(e)}'
        }), 500

@bp.route('/debug/session')
def debug_session():
    """Debug-Route für Session-Informationen"""
    try:
        from flask import session
        from app.models.mongodb_models import MongoDBUser
        from app.models.mongodb_database import mongodb
        
        session_info = {
            'session_id': session.get('_id'),
            'user_id': session.get('user_id'),
            'all_session_keys': list(session.keys())
        }
        
        # Alle User in der Datenbank mit detaillierten Informationen
        all_users = mongodb.find('users', {})
        user_list = []
        for user in all_users:
            user_list.append({
                'id': str(user.get('_id')),
                'id_type': type(user.get('_id')).__name__,
                'username': user.get('username'),
                'role': user.get('role'),
                'is_active': user.get('is_active', True),
                'email': user.get('email', 'N/A')
            })
        
        # Versuche den spezifischen User zu finden
        target_id = '685e3b2dbf696ee3c30fc7ab'
        specific_user = None
        
        # Suche mit verschiedenen Methoden
        for user in all_users:
            if str(user.get('_id')) == target_id:
                specific_user = {
                    'id': str(user.get('_id')),
                    'id_type': type(user.get('_id')).__name__,
                    'username': user.get('username'),
                    'role': user.get('role'),
                    'is_active': user.get('is_active', True)
                }
                break
        
        return jsonify({
            'session_info': session_info,
            'users_in_db': user_list,
            'total_users': len(user_list),
            'target_user': specific_user,
            'target_id': target_id
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@bp.route('/debug/backup-info')
@login_required
def debug_backup_info():
    """Debug-Route für Backup-Informationen"""
    try:
        backup_dir = Path(__file__).parent.parent.parent / 'backups'
        backup_info = {
            'backup_dir_exists': backup_dir.exists(),
            'backup_dir_path': str(backup_dir),
            'backup_dir_absolute': str(backup_dir.absolute()),
            'backup_files': []
        }
        
        if backup_dir.exists():
            for backup_file in backup_dir.glob('*.json'):
                try:
                    backup_info['backup_files'].append({
                        'name': backup_file.name,
                        'size': backup_file.stat().st_size,
                        'exists': backup_file.exists(),
                        'readable': backup_file.is_file()
                    })
                except Exception as e:
                    backup_info['backup_files'].append({
                        'name': backup_file.name,
                        'error': str(e)
                    })
        
        return jsonify(backup_info)
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': str(e.__traceback__)
        }), 500

@bp.route('/debug/clear-session')
def clear_session():
    """Löscht die aktuelle Session"""
    try:
        from flask import session
        from flask_login import logout_user
        
        logout_user()
        session.clear()
        
        return jsonify({
            'status': 'success',
            'message': 'Session gelöscht. Bitte melden Sie sich erneut an.'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/debug/fix-session/<username>')
def fix_session(username):
    """Repariert die Session für einen bestimmten Benutzer"""
    try:
        from flask import session
        from flask_login import login_user
        from app.models.mongodb_models import MongoDBUser
        from app.models.user import User
        
        # Finde den User
        user_data = MongoDBUser.get_by_username(username)
        if not user_data:
            return jsonify({
                'status': 'error',
                'message': f'Benutzer {username} nicht gefunden'
            }), 404
        
        # Erstelle User-Objekt
        user = User(user_data)
        
        # Logge den User ein
        login_user(user)
        
        return jsonify({
            'status': 'success',
            'message': f'Session für {username} repariert',
            'user_id': user.id,
            'username': user.username,
            'role': user.role
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/debug/normalize-user-ids')
def normalize_user_ids():
    """Normalisiert alle User-IDs in der Datenbank zu Strings"""
    try:
        from app.models.mongodb_database import mongodb
        from bson import ObjectId
        
        # Hole alle User
        all_users = mongodb.find('users', {})
        updated_count = 0
        
        for user in all_users:
            user_id = user.get('_id')
            
            # Falls die ID ein ObjectId ist, konvertiere sie zu String
            if isinstance(user_id, ObjectId):
                string_id = str(user_id)
                
                # Erstelle ein neues Dokument mit String-ID
                new_user = user.copy()
                new_user['_id'] = string_id
                
                # Lösche das alte Dokument und füge das neue ein
                mongodb.delete_one('users', {'_id': user_id})
                mongodb.insert_one('users', new_user)
                
                updated_count += 1
                print(f"User-ID normalisiert: {user.get('username')} von {user_id} zu {string_id}")
        
        return jsonify({
            'status': 'success',
            'message': f'{updated_count} User-IDs normalisiert',
            'updated_count': updated_count
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/debug/normalize-all-ids')
def normalize_all_ids():
    """Normalisiert alle IDs in allen Collections zu Strings"""
    try:
        from app.models.mongodb_database import mongodb
        from bson import ObjectId
        
        collections_to_normalize = [
            'users', 'tickets', 'tools', 'workers', 'consumables', 
            'lendings', 'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit', 'timesheets'
        ]
        
        total_updated = 0
        collection_results = {}
        
        for collection in collections_to_normalize:
            try:
                all_docs = mongodb.find(collection, {})
                updated_count = 0
                
                for doc in all_docs:
                    doc_id = doc.get('_id')
                    
                    # Falls die ID ein ObjectId ist, konvertiere sie zu String
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)
                        
                        # Erstelle ein neues Dokument mit String-ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id
                        
                        # Lösche das alte Dokument und füge das neue ein
                        mongodb.delete_one(collection, {'_id': doc_id})
                        mongodb.insert_one(collection, new_doc)
                        
                        updated_count += 1
                
                collection_results[collection] = updated_count
                total_updated += updated_count
                print(f"Collection {collection}: {updated_count} IDs normalisiert")
                
            except Exception as e:
                collection_results[collection] = f"Fehler: {str(e)}"
                print(f"Fehler bei Collection {collection}: {e}")
        
        return jsonify({
            'status': 'success',
            'message': f'{total_updated} IDs in allen Collections normalisiert',
            'total_updated': total_updated,
            'collection_results': collection_results
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/debug/user-management')
@login_required
@admin_required
def debug_user_management():
    """Debug-Route für User-Management-Probleme"""
    try:
        from app.models.mongodb_models import MongoDBUser
        from app.models.mongodb_database import mongodb
        
        # Hole alle User mit detaillierten Informationen
        all_users = mongodb.find('users', {})
        user_list = []
        
        for user in all_users:
            user_id = user.get('_id')
            user_list.append({
                'id': str(user_id),
                'id_type': type(user_id).__name__,
                'username': user.get('username'),
                'role': user.get('role'),
                'is_active': user.get('is_active', True),
                'email': user.get('email', 'N/A'),
                'firstname': user.get('firstname', 'N/A'),
                'lastname': user.get('lastname', 'N/A'),
                'created_at': str(user.get('created_at', 'N/A')),
                'updated_at': str(user.get('updated_at', 'N/A'))
            })
        
        # Teste verschiedene Suchmethoden
        test_results = []
        if user_list:
            test_user = user_list[0]
            test_id = test_user['id']
            
            # Test 1: Direkte String-Suche
            try:
                direct_result = mongodb.find_one('users', {'_id': test_id})
                test_results.append({
                    'method': 'Direkte String-Suche',
                    'success': direct_result is not None,
                    'result': str(direct_result.get('username') if direct_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'Direkte String-Suche',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })
            
            # Test 2: ObjectId-Suche
            try:
                from bson import ObjectId
                obj_id = ObjectId(test_id)
                obj_result = mongodb.find_one('users', {'_id': obj_id})
                test_results.append({
                    'method': 'ObjectId-Suche',
                    'success': obj_result is not None,
                    'result': str(obj_result.get('username') if obj_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'ObjectId-Suche',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })
            
            # Test 3: find_user_by_id
            try:
                user_result = find_user_by_id(test_id)
                test_results.append({
                    'method': 'find_user_by_id',
                    'success': user_result is not None,
                    'result': str(user_result.get('username') if user_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'find_user_by_id',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })
            
            # Test 4: MongoDBUser.get_by_id
            try:
                mongo_user_result = MongoDBUser.get_by_id(test_id)
                test_results.append({
                    'method': 'MongoDBUser.get_by_id',
                    'success': mongo_user_result is not None,
                    'result': str(mongo_user_result.get('username') if mongo_user_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'MongoDBUser.get_by_id',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })
        
        return jsonify({
            'status': 'success',
            'total_users': len(user_list),
            'users': user_list,
            'test_results': test_results,
            'test_id_used': test_user['id'] if user_list else 'Keine User vorhanden'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/debug/test-user-id/<user_id>')
@login_required
@admin_required
def debug_test_user_id(user_id):
    """Testet eine spezifische User-ID"""
    try:
        logging.info(f"DEBUG: Teste User-ID: {user_id}")
        
        # Teste verschiedene Suchmethoden
        results = {}
        
        # 1. Direkte Suche mit String
        user1 = mongodb.find_one('users', {'_id': user_id})
        results['direct_string'] = {
            'found': user1 is not None,
            'username': user1.get('username') if user1 else None
        }
        
        # 2. Suche mit ObjectId
        try:
            object_id = ObjectId(user_id)
            user2 = mongodb.find_one('users', {'_id': object_id})
            results['objectid'] = {
                'found': user2 is not None,
                'username': user2.get('username') if user2 else None
            }
        except Exception as e:
            results['objectid'] = {
                'found': False,
                'error': str(e)
            }
        
        # 3. Suche mit find_user_by_id
        user3 = find_user_by_id(user_id)
        results['find_user_by_id'] = {
            'found': user3 is not None,
            'username': user3.get('username') if user3 else None
        }
        
        # 4. Suche mit convert_id_for_query
        try:
            converted_id = convert_id_for_query(user_id)
            user4 = mongodb.find_one('users', {'_id': converted_id})
            results['convert_id_for_query'] = {
                'found': user4 is not None,
                'username': user4.get('username') if user4 else None,
                'converted_id_type': type(converted_id).__name__
            }
        except Exception as e:
            results['convert_id_for_query'] = {
                'found': False,
                'error': str(e)
            }
        
        return jsonify({
            'success': True,
            'tested_id': user_id,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Testen der User-ID {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

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

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id

        # Aktualisiere die Zuweisung direkt im Ticket
        if not mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': {'assigned_to': assigned_to, 'updated_at': datetime.now()}}):
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
        
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id
        
        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
            
        # Aktualisiere den Status
        mongodb.update_one('tickets', 
                          {'_id': ticket_id_for_update}, 
                          {
                              '$set': {
                                  'status': new_status,
                                  'updated_at': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
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
    """Ticket soft löschen (markieren als gelöscht)"""
    try:
        # Verwende den AdminTicketService
        success, message = AdminTicketService.delete_ticket(ticket_id, permanent=False)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Tickets: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/delete-permanent', methods=['DELETE'])
@login_required
@admin_required
def delete_ticket_permanent(ticket_id):
    """Ticket endgültig löschen"""
    try:
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id
        
        # Prüfe ob das Ticket existiert und gelöscht ist
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update, 'deleted': True})
        
        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden oder nicht gelöscht'
            }), 404
            
        # Lösche das Ticket und alle zugehörigen Daten endgültig
        mongodb.delete_one('tickets', {'_id': ticket_id_for_update})
        mongodb.delete_many('ticket_notes', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('ticket_messages', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('ticket_assignments', {'ticket_id': ticket_id_for_update})
        mongodb.delete_one('auftrag_details', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('auftrag_arbeit', {'ticket_id': ticket_id_for_update})
        
        return jsonify({
            'success': True,
            'message': 'Ticket wurde endgültig gelöscht'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim endgültigen Löschen des Tickets: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500











@bp.route('/delete_user/<user_id>', methods=['POST'])
@mitarbeiter_required
def delete_user(user_id):
    """Benutzer löschen"""
    try:
        user = AdminUserService.get_user_by_id(user_id)
        if not user:
            flash('Benutzer nicht gefunden', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Verhindere das Löschen des eigenen Accounts
        if user['username'] == current_user.username:
            flash('Sie können Ihren eigenen Account nicht löschen', 'error')
            return redirect(url_for('admin.manage_users'))
        
        # Benutzer löschen mit AdminUserService
        success, message = AdminUserService.delete_user(user_id)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')
        
        return redirect(url_for('admin.manage_users'))
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Benutzers: {e}")
        flash('Fehler beim Löschen des Benutzers', 'error')
        return redirect(url_for('admin.manage_users'))

@bp.route('/user_form')
@mitarbeiter_required
def user_form():
    """Benutzer-Formular (für neue Benutzer)"""
    return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])

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
        settings = list(mongodb.find('settings', {}))
        
        # Erstelle Excel-Datei mit mehreren Arbeitsblättern
        data_dict = {
            'Werkzeuge': tools,
            'Mitarbeiter': workers,
            'Verbrauchsmaterial': consumables,
            'Ausleihverlauf': lendings,
            'Settings': settings
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

def fix_id_for_import(doc):
    """
    Wandelt das _id-Feld in einen echten ObjectId um, wenn möglich.
    Verbesserte Version für robuste Importe.
    """
    if '_id' in doc:
        # Falls _id ein String ist und wie eine ObjectId aussieht
        if isinstance(doc['_id'], str) and len(doc['_id']) == 24:
            try:
                doc['_id'] = ObjectId(doc['_id'])
            except Exception:
                # Falls es keine gültige ObjectId ist, entferne das Feld
                # MongoDB wird automatisch eine neue ObjectId generieren
                del doc['_id']
        # Falls _id bereits eine ObjectId ist, belasse es
        elif isinstance(doc['_id'], ObjectId):
            pass
        # Falls _id ein anderer Typ ist, entferne es
        else:
            del doc['_id']
    
    # Entferne NaN-Werte und leere Strings
    cleaned_doc = {}
    for key, value in doc.items():
        if pd.isna(value) or value == '' or value == 'nan':
            continue
        cleaned_doc[key] = value
    
    return cleaned_doc

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
            errors = []
            
            # Importiere Werkzeuge
            if 'Werkzeuge' in excel_file.sheet_names:
                try:
                    df_tools = pd.read_excel(excel_file, sheet_name='Werkzeuge')
                    for index, row in df_tools.iterrows():
                        try:
                            tool_data = row.to_dict()
                            tool_data = fix_id_for_import(tool_data)
                            
                            # Prüfe ob Barcode vorhanden ist
                            if not tool_data.get('barcode'):
                                errors.append(f"Zeile {index + 2}: Werkzeug ohne Barcode übersprungen")
                                continue
                            
                            existing = mongodb.find_one('tools', {'barcode': tool_data.get('barcode')})
                            if not existing:
                                mongodb.insert_one('tools', tool_data)
                                imported_count += 1
                            else:
                                # Update existierendes Werkzeug
                                mongodb.update_one('tools', {'barcode': tool_data.get('barcode')}, {'$set': tool_data})
                                imported_count += 1
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Werkzeug: {str(e)}")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Werkzeuge-Tabelle: {str(e)}")
            
            # Importiere Mitarbeiter
            if 'Mitarbeiter' in excel_file.sheet_names:
                try:
                    df_workers = pd.read_excel(excel_file, sheet_name='Mitarbeiter')
                    for index, row in df_workers.iterrows():
                        try:
                            worker_data = row.to_dict()
                            worker_data = fix_id_for_import(worker_data)
                            
                            # Prüfe ob Barcode vorhanden ist
                            if not worker_data.get('barcode'):
                                errors.append(f"Zeile {index + 2}: Mitarbeiter ohne Barcode übersprungen")
                                continue
                            
                            existing = mongodb.find_one('workers', {'barcode': worker_data.get('barcode')})
                            if not existing:
                                mongodb.insert_one('workers', worker_data)
                                imported_count += 1
                            else:
                                # Update existierenden Mitarbeiter
                                mongodb.update_one('workers', {'barcode': worker_data.get('barcode')}, {'$set': worker_data})
                                imported_count += 1
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Mitarbeiter: {str(e)}")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Mitarbeiter-Tabelle: {str(e)}")
            
            # Importiere Verbrauchsmaterial
            if 'Verbrauchsmaterial' in excel_file.sheet_names:
                try:
                    df_consumables = pd.read_excel(excel_file, sheet_name='Verbrauchsmaterial')
                    for index, row in df_consumables.iterrows():
                        try:
                            consumable_data = row.to_dict()
                            consumable_data = fix_id_for_import(consumable_data)
                            
                            # Prüfe ob Barcode vorhanden ist
                            if not consumable_data.get('barcode'):
                                errors.append(f"Zeile {index + 2}: Verbrauchsmaterial ohne Barcode übersprungen")
                                continue
                            
                            existing = mongodb.find_one('consumables', {'barcode': consumable_data.get('barcode')})
                            if not existing:
                                mongodb.insert_one('consumables', consumable_data)
                                imported_count += 1
                            else:
                                # Update existierendes Verbrauchsmaterial
                                mongodb.update_one('consumables', {'barcode': consumable_data.get('barcode')}, {'$set': consumable_data})
                                imported_count += 1
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Verbrauchsmaterial: {str(e)}")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Verbrauchsmaterial-Tabelle: {str(e)}")
            
            # Importiere Settings (Kategorien, Standorte, Abteilungen)
            if 'Settings' in excel_file.sheet_names:
                try:
                    df_settings = pd.read_excel(excel_file, sheet_name='Settings')
                    for index, row in df_settings.iterrows():
                        try:
                            setting_data = row.to_dict()
                            setting_data = fix_id_for_import(setting_data)
                            valid_settings = ['categories', 'locations', 'departments', 'ticket_categories', 
                                            'label_tools_name', 'label_tools_icon', 'label_consumables_name', 
                                            'label_consumables_icon', 'label_tickets_name', 'label_tickets_icon']
                            
                            if setting_data.get('key') in valid_settings:
                                existing = mongodb.find_one('settings', {'key': setting_data.get('key')})
                                if not existing:
                                    mongodb.insert_one('settings', setting_data)
                                    imported_count += 1
                                else:
                                    mongodb.update_one('settings', 
                                                     {'key': setting_data.get('key')}, 
                                                     {'$set': setting_data})
                                    imported_count += 1
                            else:
                                errors.append(f"Zeile {index + 2}: Ungültige Setting '{setting_data.get('key')}' übersprungen")
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Setting: {str(e)}")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Settings-Tabelle: {str(e)}")
            
            # Zeige Erfolgsmeldung und eventuelle Fehler
            if errors:
                error_message = f'{imported_count} Datensätze importiert. {len(errors)} Fehler aufgetreten: ' + '; '.join(errors[:5])
                if len(errors) > 5:
                    error_message += f'... und {len(errors) - 5} weitere'
                flash(error_message, 'warning')
            else:
                flash(f'{imported_count} Datensätze erfolgreich importiert', 'success')
            
        finally:
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
            result = mongodb.update_one('users', 
                                     {'_id': convert_id_for_query(user['_id'])}, 
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



@bp.route('/backup/auto/status')
@login_required
@admin_required
def auto_backup_status():
    """Gibt den Status des automatischen Backup-Systems zurück"""
    try:
        from app.utils.auto_backup import get_auto_backup_status
        status = get_auto_backup_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Auto-Backup-Status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Abrufen des Status: {str(e)}'
        })

@bp.route('/backup/auto/start', methods=['POST'])
@login_required
@admin_required
def start_auto_backup():
    """Startet das automatische Backup-System"""
    try:
        from app.utils.auto_backup import start_auto_backup
        start_auto_backup()
        return jsonify({
            'success': True,
            'message': 'Automatisches Backup-System gestartet'
        })
    except Exception as e:
        logger.error(f"Fehler beim Starten des Auto-Backup-Systems: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Starten: {str(e)}'
        })

@bp.route('/backup/auto/stop', methods=['POST'])
@login_required
@admin_required
def stop_auto_backup():
    """Stoppt das automatische Backup-System"""
    try:
        from app.utils.auto_backup import stop_auto_backup
        stop_auto_backup()
        return jsonify({
            'success': True,
            'message': 'Automatisches Backup-System gestoppt'
        })
    except Exception as e:
        logger.error(f"Fehler beim Stoppen des Auto-Backup-Systems: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Stoppen: {str(e)}'
        })

@bp.route('/backup/auto/logs')
@login_required
@admin_required
def auto_backup_logs():
    """Gibt die Auto-Backup-Logs zurück"""
    try:
        from app.utils.auto_backup import auto_backup_scheduler
        log_file = auto_backup_scheduler.log_file
        
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            # Letzte 50 Zeilen
            recent_logs = logs[-50:] if len(logs) > 50 else logs
            return jsonify({
                'success': True,
                'logs': recent_logs
            })
        else:
            return jsonify({
                'success': True,
                'logs': ['Keine Logs verfügbar']
            })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Auto-Backup-Logs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Abrufen der Logs: {str(e)}'
        })

@bp.route('/auto-backup', methods=['GET', 'POST'])
@login_required
@admin_required
def auto_backup():
    """Automatisches Backup-System Verwaltungsseite"""
    try:
        from app.utils.auto_backup import auto_backup_scheduler
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'save_times':
                # Backup-Zeiten speichern
                times_input = request.form.get('backup_times', '')
                times_list = [t.strip() for t in times_input.split(',') if t.strip()]
                
                success, message = auto_backup_scheduler.save_backup_times(times_list)
                
                if success:
                    flash('Backup-Zeiten erfolgreich gespeichert.', 'success')
                else:
                    flash(f'Fehler beim Speichern der Backup-Zeiten: {message}', 'error')
            
            elif action == 'save_weekly_time':
                # Wöchentliche Backup-Zeit speichern
                weekly_time = request.form.get('weekly_backup_time', '').strip()
                
                success, message = auto_backup_scheduler.save_weekly_backup_time(weekly_time)
                
                if success:
                    flash('Wöchentliche Backup-Zeit erfolgreich gespeichert.', 'success')
                else:
                    flash(f'Fehler beim Speichern der wöchentlichen Backup-Zeit: {message}', 'error')
            
            elif action == 'save_weekly_email':
                # E-Mail für wöchentliche Backups speichern
                weekly_email = request.form.get('weekly_backup_email', '').strip()
                
                if weekly_email and '@' in weekly_email:
                    try:
                        from app.models.mongodb_database import mongodb
                        mongodb.update_one('settings', 
                                         {'key': 'weekly_backup_email'}, 
                                         {'$set': {'value': weekly_email}}, 
                                         upsert=True)
                        flash('E-Mail-Adresse für wöchentliche Backups erfolgreich gespeichert.', 'success')
                    except Exception as e:
                        logger.error(f"Fehler beim Speichern der wöchentlichen Backup-E-Mail: {e}")
                        flash(f'Fehler beim Speichern der E-Mail-Adresse: {str(e)}', 'error')
                else:
                    flash('Bitte geben Sie eine gültige E-Mail-Adresse ein.', 'error')
        
        # Lade aktuelle Einstellungen
        current_times = auto_backup_scheduler.get_backup_times()
        current_weekly_time = auto_backup_scheduler.get_weekly_backup_time()
        current_weekly_email = auto_backup_scheduler._get_weekly_backup_email()
        
        return render_template('admin/auto_backup.html', 
                             backup_times=current_times,
                             weekly_backup_time=current_weekly_time,
                             weekly_backup_email=current_weekly_email)
        
    except Exception as e:
        logger.error(f"Fehler bei Auto-Backup-Einstellungen: {e}")
        flash('Fehler beim Laden der Auto-Backup-Einstellungen.', 'error')
        return render_template('admin/auto_backup.html', 
                             backup_times=['06:00', '18:00'],
                             weekly_backup_time='17:00',
                             weekly_backup_email='')

@bp.route('/email_settings', methods=['GET', 'POST'])
@admin_required
def email_settings():
    """E-Mail-Konfiguration verwalten"""
    try:
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'save':
                # E-Mail-Konfiguration speichern
                use_auth = request.form.get('use_auth') == 'on'
                
                if use_auth:
                    # Mit Authentifizierung
                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('mail_username', ''),
                        'mail_password': request.form.get('mail_password', ''),
                        'test_email': request.form.get('test_email', ''),
                        'use_auth': True
                    }
                else:
                    # Ohne Authentifizierung
                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('sender_email', ''),  # Absender-E-Mail
                        'mail_password': '',  # Kein Passwort
                        'test_email': request.form.get('test_email', ''),
                        'use_auth': False
                    }
                
                success, message = AdminEmailService.save_email_config(config_data)
                if success:
                    flash(message, 'success')
                else:
                    flash(message, 'error')
                    
            elif action == 'test':
                # E-Mail-Konfiguration testen
                use_auth = request.form.get('use_auth') == 'on'
                
                if use_auth:
                    # Mit Authentifizierung
                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('mail_username', ''),
                        'mail_password': request.form.get('mail_password', ''),
                        'test_email': request.form.get('test_email', '')
                    }
                else:
                    # Ohne Authentifizierung
                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('sender_email', ''),  # Absender-E-Mail
                        'mail_password': '',  # Kein Passwort
                        'test_email': request.form.get('test_email', '')
                    }
                
                success, message = AdminEmailService.test_email_config(config_data)
                if success:
                    flash(f'E-Mail-Test erfolgreich: {message}', 'success')
                else:
                    flash(f'E-Mail-Test fehlgeschlagen: {message}', 'error')
        
        # Lade aktuelle Konfiguration
        config = AdminEmailService.get_email_config()
        
        return render_template('admin/email_settings.html', config=config)
        
    except Exception as e:
        logger.error(f"Fehler bei E-Mail-Einstellungen: {e}")
        flash('Fehler beim Laden der E-Mail-Einstellungen.', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/admin/email/diagnose', methods=['POST'])
@login_required
@admin_required
def diagnose_email():
    """Diagnostiziert die SMTP-Verbindung"""
    try:
        config_data = AdminEmailService.get_email_config()
        if not config_data:
            return jsonify({'success': False, 'message': 'Keine E-Mail-Konfiguration gefunden'})
        
        success, result = AdminEmailService.diagnose_smtp_connection(config_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'SMTP-Diagnose erfolgreich',
                'diagnosis': result
            })
        else:
            return jsonify({
                'success': False,
                'message': result
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Diagnose-Fehler: {str(e)}'
        })

@bp.route('/admin/email/test-simple', methods=['POST'])
@login_required
@admin_required
def test_email_simple():
    """Einfacher E-Mail-Test"""
    try:
        config_data = AdminEmailService.get_email_config()
        if not config_data:
            return jsonify({'success': False, 'message': 'Keine E-Mail-Konfiguration gefunden'})
        
        success, message = AdminEmailService.test_email_config(config_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Test-Fehler: {str(e)}'
        })

@bp.route('/backup/weekly/test', methods=['POST'])
@login_required
@admin_required
def test_weekly_backup():
    """Sendet das wöchentliche Backup-Archiv manuell"""
    try:
        from app.utils.auto_backup import auto_backup_scheduler
        
        # Führe wöchentliches Backup-Archiv manuell aus
        auto_backup_scheduler._create_weekly_backup_archive()
        
        return jsonify({
            'success': True,
            'message': 'Backup-Archiv erfolgreich erstellt, versendet und ZIP-Datei gelöscht'
        })
    except Exception as e:
        logger.error(f"Fehler beim Versenden des Backup-Archivs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Versenden: {str(e)}'
        })






