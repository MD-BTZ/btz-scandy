from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, send_file, current_app, abort
from app.models.database import Database
from app.utils.decorators import admin_required, mitarbeiter_required
from werkzeug.utils import secure_filename
import os
from pathlib import Path
from flask import current_app
from app.utils.db_schema import SchemaManager, validate_input, truncate_field
import colorsys
import logging
from datetime import datetime, timedelta
from app.models.models import Tool, Consumable, Worker
from app.models.user import User
import sqlite3
from app.utils.error_handler import handle_errors, safe_db_query
from flask_login import login_required, current_user
from app.models.settings import Settings
from app.utils.backup_manager import backup_manager
import openpyxl
from io import BytesIO
import time
from PIL import Image
import io
from app.config.config import Config
from app.models.ticket_db import TicketDatabase

# Logger einrichten
logger = logging.getLogger(__name__)

bp = Blueprint('admin', __name__, url_prefix='/admin')
ticket_db = TicketDatabase()

def get_recent_activity():
    """Hole die letzten Aktivitäten"""
    return Database.query('''
        SELECT 
            'Ausleihe' as type,
            t.name as item_name,
            w.firstname || ' ' || w.lastname as worker_name,
            l.lent_at as action_date
        FROM lendings l
        JOIN tools t ON l.tool_barcode = t.barcode
        JOIN workers w ON l.worker_barcode = w.barcode
        WHERE l.returned_at IS NULL
        LIMIT 6
        
        UNION ALL
        
        SELECT 
            'Verbrauch' as type,
            c.name as item_name,
            w.firstname || ' ' || w.lastname as worker_name,
            cu.used_at as action_date
        FROM consumable_usages cu
        JOIN consumables c ON cu.consumable_barcode = c.barcode
        JOIN workers w ON cu.worker_barcode = w.barcode
        ORDER BY action_date DESC
        LIMIT 10
    ''')

def get_material_usage():
    """Hole die Materialnutzung"""
    return Database.query('''
        SELECT 
            c.name,
            SUM(CASE WHEN cu.quantity > 0 THEN cu.quantity ELSE 0 END) as total_quantity
        FROM consumable_usages cu
        JOIN consumables c ON cu.consumable_barcode = c.barcode
        GROUP BY c.name
        ORDER BY total_quantity DESC
        LIMIT 5
    ''')

def get_warnings():
    """Hole aktuelle Warnungen"""
    return Database.query('''
        SELECT 
            'Werkzeug defekt' as type,
            name as message,
            'error' as severity
        FROM tools 
        WHERE status = 'defekt' AND deleted = 0
        
        UNION ALL
        
        SELECT 
            'Material niedrig' as type,
            name || ' (Bestand: ' || quantity || ')' as message,
            CASE 
                WHEN quantity < min_quantity * 0.5 THEN 'error'
                ELSE 'warning'
            END as severity
        FROM consumables
        WHERE quantity < min_quantity AND deleted = 0
        ORDER BY severity DESC
        LIMIT 5
    ''')

def get_backup_info():
    """Hole Informationen über vorhandene Backups"""
    backups = []
    backup_dir = Path(__file__).parent.parent.parent / 'backups'
    
    if backup_dir.exists():
        for backup_file in sorted(backup_dir.glob('*.db'), reverse=True):
            # Backup-Statistiken aus der Datei lesen
            stats = None
            try:
                with sqlite3.connect(str(backup_file)) as conn:
                    cursor = conn.cursor()
                    stats = {
                        'tools': cursor.execute('SELECT COUNT(*) FROM tools WHERE deleted = 0').fetchone()[0],
                        'consumables': cursor.execute('SELECT COUNT(*) FROM consumables WHERE deleted = 0').fetchone()[0],
                        'workers': cursor.execute('SELECT COUNT(*) FROM workers WHERE deleted = 0').fetchone()[0],
                        'active_lendings': cursor.execute('SELECT COUNT(*) FROM lendings WHERE returned_at IS NULL').fetchone()[0]
                    }
            except:
                stats = None
            
            # Unix-Timestamp in datetime umwandeln
            created_timestamp = backup_file.stat().st_mtime
            created_datetime = datetime.fromtimestamp(created_timestamp)
            
            backups.append({
                'name': backup_file.name,
                'size': backup_file.stat().st_size,
                'created': created_datetime,
                'stats': stats
            })
    
    return backups

def get_consumables_forecast():
    """Berechnet die Bestandsprognose für Verbrauchsmaterialien"""
    return Database.query('''
        WITH avg_usage AS (
            SELECT 
                c.barcode,
                c.name,
                c.quantity as current_amount,
                COALESCE(CAST(SUM(cu.quantity) AS FLOAT) / 30, 0) as avg_daily_usage
            FROM consumables c
            LEFT JOIN consumable_usages cu ON c.barcode = cu.consumable_barcode
                AND cu.used_at >= date('now', '-30 days')
            WHERE c.deleted = 0
            GROUP BY c.barcode, c.name, c.quantity
        )
        SELECT 
            name,
            current_amount,
            ROUND(avg_daily_usage, 2) as avg_daily_usage,
            CASE 
                WHEN avg_daily_usage > 0 THEN ROUND(current_amount / avg_daily_usage)
                ELSE 999
            END as days_remaining
        FROM avg_usage
        WHERE current_amount > 0
        ORDER BY 
            CASE 
                WHEN avg_daily_usage > 0 THEN current_amount / avg_daily_usage
                ELSE 999
            END ASC
        LIMIT 6
    ''')

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
def dashboard():
    # Werkzeug-Statistiken
    tool_stats = Database.query('''
        WITH valid_tools AS (
            SELECT id, barcode
            FROM tools
            WHERE deleted = 0
        )
        SELECT
            COUNT(*) as total,
            SUM(CASE
                WHEN NOT EXISTS (
                    SELECT 1 FROM lendings l
                    WHERE l.tool_barcode = t.barcode
                    AND l.returned_at IS NULL
                ) AND status = 'verfügbar' THEN 1
                ELSE 0
            END) as available,
            (
                SELECT COUNT(DISTINCT l.tool_barcode)
                FROM lendings l
                JOIN valid_tools vt ON l.tool_barcode = vt.barcode
                WHERE l.returned_at IS NULL
            ) as lent,
            SUM(CASE WHEN status = 'defekt' THEN 1 ELSE 0 END) as defect
        FROM tools t
        WHERE t.deleted = 0
    ''', one=True)
    
    # Verbrauchsmaterial-Statistiken
    consumable_stats = {
        'total': Database.query('SELECT COUNT(*) as count FROM consumables WHERE deleted = 0', one=True)['count'],
        'sufficient': Database.query('''
            SELECT COUNT(*) as count 
            FROM consumables c
            WHERE deleted = 0 
            AND quantity > min_quantity
            AND (
                SELECT COALESCE(CAST(SUM(cu.quantity) AS FLOAT) / 30, 0)
                FROM consumable_usages cu
                WHERE cu.consumable_barcode = c.barcode
                AND cu.used_at >= date('now', '-30 days')
            ) * 7 <= (quantity - min_quantity)
        ''', one=True)['count'],
        'warning': Database.query('''
            SELECT COUNT(*) as count 
            FROM consumables c
            WHERE deleted = 0 
            AND quantity > min_quantity
            AND (
                SELECT COALESCE(CAST(SUM(cu.quantity) AS FLOAT) / 30, 0)
                FROM consumable_usages cu
                WHERE cu.consumable_barcode = c.barcode
                AND cu.used_at >= date('now', '-30 days')
            ) * 7 > (quantity - min_quantity)
        ''', one=True)['count'],
        'critical': Database.query('SELECT COUNT(*) as count FROM consumables WHERE deleted = 0 AND quantity <= min_quantity', one=True)['count']
    }
    
    # Mitarbeiter-Statistiken
    worker_stats = {
        'total': Database.query('SELECT COUNT(*) as count FROM workers WHERE deleted = 0', one=True)['count'],
        'by_department': Database.query('''
            SELECT department as name, COUNT(*) as count 
            FROM workers 
            WHERE deleted = 0 AND department IS NOT NULL 
            GROUP BY department 
            ORDER BY department
        ''')
    }
    
    # Warnungen für defekte Werkzeuge und überfällige Ausleihen
    tool_warnings = Database.query('''
        SELECT 
            name,
            CASE 
                WHEN status = 'defekt' THEN 'defekt'
                ELSE 'überfällig'
            END as status,
            CASE 
                WHEN status = 'defekt' THEN 'error'
                ELSE 'warning'
            END as severity,
            CASE
                WHEN status = 'defekt' THEN 'Werkzeug ist defekt'
                ELSE 'Ausleihe seit ' || ROUND((julianday('now') - julianday(lent_at))) || ' Tagen überfällig'
            END as description
        FROM tools t
        LEFT JOIN lendings l ON t.barcode = l.tool_barcode AND l.returned_at IS NULL
        WHERE (t.status = 'defekt' AND t.deleted = 0)
           OR (l.lent_at IS NOT NULL AND julianday('now') - julianday(lent_at) > 5)
        ORDER BY 
            CASE 
                WHEN status = 'defekt' THEN 0
                ELSE 1
            END,
            name
    ''')
    
    # Warnungen für niedrigen Materialbestand
    consumable_warnings = Database.query('''
        WITH avg_usage AS (
            SELECT 
                c.barcode,
                c.name,
                c.quantity,
                c.min_quantity,
                COALESCE(CAST(SUM(cu.quantity) AS FLOAT) / 30, 0) as avg_daily_usage
            FROM consumables c
            LEFT JOIN consumable_usages cu ON c.barcode = cu.consumable_barcode
                AND cu.used_at >= date('now', '-30 days')
            WHERE c.deleted = 0
            GROUP BY c.barcode, c.name, c.quantity, c.min_quantity
        )
        SELECT
            name as message,
            CASE
                WHEN quantity <= min_quantity THEN 'error'
                ELSE 'warning'
            END as type,
            CASE
                WHEN quantity <= min_quantity THEN 'exclamation-triangle'
                ELSE 'exclamation'
            END as icon,
            CASE
                WHEN quantity <= min_quantity THEN 'Kritischer Bestand'
                ELSE 'Warnung: Bestand wird in ' || 
                     ROUND((quantity - min_quantity) / NULLIF(avg_daily_usage, 0)) || 
                     ' Tagen unter Mindestbestand fallen'
            END as description
        FROM avg_usage
        WHERE quantity <= min_quantity 
           OR (avg_daily_usage > 0 AND (quantity - min_quantity) / avg_daily_usage <= 7)
        ORDER BY 
            CASE 
                WHEN quantity <= min_quantity THEN 0
                ELSE 1
            END,
            quantity / min_quantity ASC
        LIMIT 5
    ''')
    
    # Materialverbrauch-Trend
    consumable_trend = get_consumable_trend()
    
    # Aktuelle Ausleihen
    current_lendings = Database.query('''
        SELECT 
            l.*, 
            t.name as tool_name, 
            w.firstname || ' ' || w.lastname as worker_name,
            datetime(l.lent_at) as lent_at
        FROM lendings l
        JOIN tools t ON l.tool_barcode = t.barcode
        JOIN workers w ON l.worker_barcode = w.barcode
        WHERE l.returned_at IS NULL
        ORDER BY l.lent_at DESC
    ''')
    
    # Letzte Materialentnahmen
    recent_consumable_usage = Database.query('''
        SELECT
            c.name as consumable_name,
            cu.quantity,
            w.firstname || ' ' || w.lastname as worker_name,
            cu.used_at
        FROM consumable_usages cu
        JOIN consumables c ON cu.consumable_barcode = c.barcode
        JOIN workers w ON cu.worker_barcode = w.barcode
        ORDER BY cu.used_at DESC
        LIMIT 10
    ''')
    
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
    trend_data = Database.query('''
        WITH daily_usage AS (
            SELECT 
                c.name,
                date(cu.used_at) as date,
                SUM(CASE WHEN cu.quantity > 0 THEN cu.quantity ELSE 0 END) as daily_quantity
            FROM consumable_usages cu
            JOIN consumables c ON cu.consumable_barcode = c.barcode
            WHERE cu.used_at >= date('now', '-6 days')
            GROUP BY c.name, date(cu.used_at)
        ),
        dates AS (
            SELECT date('now', '-' || n || ' days') as date
            FROM (SELECT 0 as n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 
                 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6)
        ),
        top_consumables AS (
            SELECT 
                c.name,
                SUM(CASE WHEN cu.quantity > 0 THEN cu.quantity ELSE 0 END) as total_quantity
            FROM consumable_usages cu
            JOIN consumables c ON cu.consumable_barcode = c.barcode
            WHERE cu.used_at >= date('now', '-6 days')
            GROUP BY c.name
            ORDER BY total_quantity DESC
            LIMIT 5
        )
        SELECT 
            dates.date as label,
            tc.name,
            COALESCE(du.daily_quantity, 0) as count
        FROM dates
        CROSS JOIN top_consumables tc
        LEFT JOIN daily_usage du ON dates.date = du.date AND tc.name = du.name
        ORDER BY tc.name, dates.date
    ''')
    
    # Daten für das Chart aufbereiten
    labels = []
    datasets = []
    current_name = None
    current_data = []
    
    for row in trend_data:
        if row['label'] not in labels:
            labels.append(row['label'])
        
        if current_name != row['name']:
            if current_name is not None:
                datasets.append({
                    'label': current_name,
                    'data': current_data,
                    'fill': False,
                    'borderColor': f'hsl({(len(datasets) * 60) % 360}, 70%, 50%)',
                    'tension': 0.1
                })
            current_name = row['name']
            current_data = []
        current_data.append(row['count'])
    
    if current_name is not None:
        datasets.append({
            'label': current_name,
            'data': current_data,
            'fill': False,
            'borderColor': f'hsl({(len(datasets) * 60) % 360}, 70%, 50%)',
            'tension': 0.1
        })
    
    return {
        'labels': labels,
        'datasets': datasets
    }

# Manuelle Ausleihe
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
                with Database.get_db() as db:
                    # Prüfe ob der Mitarbeiter existiert
                    if worker_barcode:
                        worker = db.execute('''
                            SELECT * FROM workers 
                            WHERE barcode = ? AND deleted = 0
                        ''', [worker_barcode]).fetchone()
                        
                        if not worker:
                            return jsonify({
                                'success': False,
                                'message': 'Mitarbeiter nicht gefunden'
                            }), 404
                    
                    # Prüfe ob es ein Verbrauchsmaterial ist
                    consumable = db.execute('''
                        SELECT * FROM consumables 
                        WHERE barcode = ? AND deleted = 0
                    ''', [item_barcode]).fetchone()
                    
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
                        db.execute('''
                            INSERT INTO consumable_usages 
                            (consumable_barcode, worker_barcode, quantity, used_at, updated_at, sync_status)
                            VALUES (?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'), 'pending')
                        ''', [item_barcode, worker_barcode, quantity])
                        
                        # Bestand aktualisieren
                        db.execute('''
                            UPDATE consumables
                            SET quantity = quantity - ?,
                                updated_at = datetime('now', 'localtime'),
                                sync_status = 'pending'
                            WHERE barcode = ?
                        ''', [quantity, item_barcode])
                        
                        db.commit()
                        return jsonify({
                            'success': True,
                            'message': f'{quantity}x {consumable["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgegeben'
                        })
                    
                    # Werkzeug-Logik
                    tool = db.execute('''
                        SELECT t.*, 
                               CASE 
                                   WHEN EXISTS (
                                       SELECT 1 FROM lendings l 
                                       WHERE l.tool_barcode = t.barcode 
                                       AND l.returned_at IS NULL
                                   ) THEN 'ausgeliehen'
                                   ELSE t.status
                               END as current_status,
                               (
                                   SELECT w.firstname || ' ' || w.lastname
                                   FROM lendings l
                                   JOIN workers w ON l.worker_barcode = w.barcode
                                   WHERE l.tool_barcode = t.barcode
                                   AND l.returned_at IS NULL
                                   LIMIT 1
                               ) as current_worker_name,
                               (
                                   SELECT l.worker_barcode
                                   FROM lendings l
                                   WHERE l.tool_barcode = t.barcode
                                   AND l.returned_at IS NULL
                                   LIMIT 1
                               ) as current_worker_barcode
                        FROM tools t
                        WHERE t.barcode = ? AND t.deleted = 0
                    ''', [item_barcode]).fetchone()
                    
                    if not tool:
                        return jsonify({
                            'success': False,
                            'message': 'Werkzeug nicht gefunden'
                        }), 404
                    
                    if action == 'lend':
                        if tool['current_status'] == 'ausgeliehen':
                            return jsonify({
                                'success': False,
                                'message': f'Dieses Werkzeug ist bereits an {tool["current_worker_name"]} ausgeliehen'
                            }), 400
                            
                        if tool['current_status'] == 'defekt':
                            return jsonify({
                                'success': False,
                                'message': 'Dieses Werkzeug ist als defekt markiert'
                            }), 400
                        
                        # Neue Ausleihe erstellen (OHNE modified_at und sync_status)
                        db.execute('''
                            INSERT INTO lendings 
                            (tool_barcode, worker_barcode, lent_at)
                            VALUES (?, ?, datetime('now'))
                        ''', [item_barcode, worker_barcode])
                        
                        # Status des Werkzeugs aktualisieren
                        db.execute('''
                            UPDATE tools 
                            SET status = 'ausgeliehen',
                                modified_at = datetime('now'),
                                sync_status = 'pending'
                            WHERE barcode = ?
                        ''', [item_barcode])
                        
                        db.commit()
                        return jsonify({
                            'success': True,
                            'message': f'Werkzeug {tool["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgeliehen'
                        })
                        
                    else:  # action == 'return'
                        if tool['current_status'] != 'ausgeliehen':
                            return jsonify({
                                'success': False,
                                'message': 'Dieses Werkzeug ist nicht ausgeliehen'
                            }), 400
                        
                        # Wenn ein Mitarbeiter angegeben wurde, prüfe ob er berechtigt ist
                        if worker_barcode and tool['current_worker_barcode'] != worker_barcode:
                            return jsonify({
                                'success': False,
                                'message': f'Dieses Werkzeug wurde von {tool["current_worker_name"]} ausgeliehen'
                            }), 403
                        
                        # Rückgabe verarbeiten (OHNE modified_at)
                        db.execute('''
                            UPDATE lendings 
                            SET returned_at = datetime('now')
                            WHERE tool_barcode = ? 
                            AND returned_at IS NULL
                        ''', [item_barcode])
                        
                        # Status des Werkzeugs aktualisieren
                        db.execute('''
                            UPDATE tools 
                            SET status = 'verfügbar',
                                modified_at = datetime('now'),
                                sync_status = 'pending'
                            WHERE barcode = ?
                        ''', [item_barcode])
                        
                        db.commit()
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
    tools = Database.query('''
        SELECT t.*,
               CASE 
                   WHEN EXISTS (
                       SELECT 1 FROM lendings l 
                       WHERE l.tool_barcode = t.barcode 
                       AND l.returned_at IS NULL
                   ) THEN 'ausgeliehen'
                   WHEN t.status = 'defekt' THEN 'defekt'
                   ELSE 'verfügbar'
               END as current_status,
               (
                   SELECT w.firstname || ' ' || w.lastname
                   FROM lendings l
                   JOIN workers w ON l.worker_barcode = w.barcode
                   WHERE l.tool_barcode = t.barcode
                   AND l.returned_at IS NULL
                   LIMIT 1
               ) as current_worker,
               (
                   SELECT l.lent_at
                   FROM lendings l
                   WHERE l.tool_barcode = t.barcode
                   AND l.returned_at IS NULL
                   LIMIT 1
               ) as lending_date
        FROM tools t
        WHERE t.deleted = 0
        ORDER BY t.name
    ''')

    workers = Database.query('''
        SELECT * FROM workers WHERE deleted = 0
        ORDER BY lastname, firstname
    ''')

    consumables = Database.query('''
        SELECT c.*,
               CASE 
                   WHEN quantity <= 0 THEN 'nicht_verfügbar'
                   WHEN quantity <= min_quantity THEN 'kritisch'
                   WHEN quantity <= min_quantity * 2 THEN 'niedrig'
                   ELSE 'verfügbar'
               END as status
        FROM consumables c 
        WHERE deleted = 0
        ORDER BY name
    ''')

    # Aktuelle Ausleihen (Werkzeuge und Verbrauchsmaterial)
    current_lendings = Database.query('''
        WITH RECURSIVE current_tool_lendings AS (
            SELECT 
                l.id,
                t.name as item_name,
                t.barcode as item_barcode,
                w.firstname || ' ' || w.lastname as worker_name,
                w.barcode as worker_barcode,
                'Werkzeug' as category,
                l.lent_at as action_date,
                NULL as amount
            FROM lendings l
            JOIN tools t ON l.tool_barcode = t.barcode
            JOIN workers w ON l.worker_barcode = w.barcode
            WHERE l.returned_at IS NULL
            AND t.deleted = 0
            AND w.deleted = 0
        ),
        current_consumable_usages AS (
            SELECT 
                cu.id,
                c.name as item_name,
                c.barcode as item_barcode,
                w.firstname || ' ' || w.lastname as worker_name,
                w.barcode as worker_barcode,
                'Verbrauchsmaterial' as category,
                cu.used_at as action_date,
                cu.quantity as amount
            FROM consumable_usages cu
            JOIN consumables c ON cu.consumable_barcode = c.barcode
            JOIN workers w ON cu.worker_barcode = w.barcode
            WHERE DATE(cu.used_at) >= DATE('now', '-7 days')
            AND c.deleted = 0
            AND w.deleted = 0
        )
        SELECT * FROM current_tool_lendings
        UNION ALL
        SELECT * FROM current_consumable_usages
        ORDER BY action_date DESC
    ''')

    return render_template('admin/manual_lending.html', 
                          tools=tools,
                          workers=workers,
                          consumables=consumables,
                          current_lendings=current_lendings)

@bp.route('/trash')
@mitarbeiter_required
def trash():
    """Papierkorb mit gelöschten Einträgen"""
    try:
        with Database.get_db() as conn:
            # Gelöschte Werkzeuge
            tools = conn.execute('''
                SELECT * FROM tools 
                WHERE deleted = 1 
                ORDER BY deleted_at DESC
            ''').fetchall()
            
            logger.debug(f"Gelöschte Werkzeuge gefunden: {len(tools)}")
            for tool in tools:
                logger.debug(f"Tool: {dict(tool)}")
            
            # Gelöschte Verbrauchsmaterialien
            consumables = conn.execute('''
                SELECT * FROM consumables 
                WHERE deleted = 1 
                ORDER BY deleted_at DESC
            ''').fetchall()
            
            logger.debug(f"Gelöschte Verbrauchsmaterialien gefunden: {len(consumables)}")
            for consumable in consumables:
                logger.debug(f"Consumable: {dict(consumable)}")
            
            # Gelöschte Mitarbeiter
            workers = conn.execute('''
                SELECT * FROM workers 
                WHERE deleted = 1 
                ORDER BY deleted_at DESC
            ''').fetchall()
            
            logger.debug(f"Gelöschte Mitarbeiter gefunden: {len(workers)}")
            for worker in workers:
                logger.debug(f"Worker: {dict(worker)}")
            
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
        with Database.get_db() as conn:
            if type == 'tool':
                # Prüfe ob das Werkzeug existiert
                tool = conn.execute('''
                    SELECT * FROM tools 
                    WHERE barcode = ? AND deleted = 1
                ''', [barcode]).fetchone()
                
                if not tool:
                    return jsonify({
                        'success': False,
                        'message': 'Werkzeug nicht gefunden'
                    }), 404
                    
                # Stelle das Werkzeug wieder her
                conn.execute('''
                    UPDATE tools 
                    SET deleted = 0,
                        deleted_at = NULL,
                        sync_status = 'pending'
                    WHERE barcode = ?
                ''', [barcode])
                
            elif type == 'consumable':
                # Prüfe ob das Verbrauchsmaterial existiert
                consumable = conn.execute('''
                    SELECT * FROM consumables 
                    WHERE barcode = ? AND deleted = 1
                ''', [barcode]).fetchone()
                
                if not consumable:
                    return jsonify({
                        'success': False,
                        'message': 'Verbrauchsmaterial nicht gefunden'
                    }), 404
                    
                # Stelle das Verbrauchsmaterial wieder her
                conn.execute('''
                    UPDATE consumables 
                    SET deleted = 0,
                        deleted_at = NULL,
                        sync_status = 'pending'
                    WHERE barcode = ?
                ''', [barcode])
                
            elif type == 'worker':
                # Prüfe ob der Mitarbeiter existiert
                worker = conn.execute('''
                    SELECT * FROM workers 
                    WHERE barcode = ? AND deleted = 1
                ''', [barcode]).fetchone()
                
                if not worker:
                    return jsonify({
                        'success': False,
                        'message': 'Mitarbeiter nicht gefunden'
                    }), 404
                    
                # Stelle den Mitarbeiter wieder her
                conn.execute('''
                    UPDATE workers 
                    SET deleted = 0,
                        deleted_at = NULL,
                        sync_status = 'pending'
                    WHERE barcode = ?
                ''', [barcode])
            else:
                return jsonify({
                    'success': False,
                    'message': 'Ungültiger Typ'
                }), 400
                
            conn.commit()
            
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
    """Hole eine Label-Einstellung aus der tickets.db"""
    try:
        ticket_db = TicketDatabase()
        value = ticket_db.query('SELECT value FROM settings WHERE key = ?', [key], one=True)
        return value['value'] if value and value['value'] else default
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Einstellung {key}: {str(e)}")
        return default

def get_app_labels():
    """Hole alle Label-Einstellungen aus der tickets.db"""
    return {
        'tools': {
            'name': get_label_setting('label_tools_name', 'Werkzeuge'),
            'icon': get_label_setting('label_tools_icon', 'fas fa-tools')
        },
        'consumables': {
            'name': get_label_setting('label_consumables_name', 'Verbrauchsmaterial'),
            'icon': get_label_setting('label_consumables_icon', 'fas fa-box-open')
        }
    }

def get_all_users():
    """Hole alle aktiven Benutzer für die Ticket-Zuweisung"""
    return ticket_db.query('''
        SELECT id, username, role
        FROM users
        WHERE is_active = 1
        ORDER BY username
    ''')

@bp.route('/server-settings', methods=['GET', 'POST'])
@admin_required
def server_settings():
    if request.method == 'POST':
        mode = request.form.get('mode')
        server_url = request.form.get('server_url')
        # Neue Felder für Labels/Icons
        label_tools_name = request.form.get('label_tools_name')
        label_tools_icon = request.form.get('label_tools_icon')
        label_consumables_name = request.form.get('label_consumables_name')
        label_consumables_icon = request.form.get('label_consumables_icon')
        try:
            ticket_db = TicketDatabase()
            
            # Speichere die neuen Label/Icons
            ticket_db.query('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', 
                ['label_tools_name', label_tools_name or 'Werkzeuge'])
            ticket_db.query('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', 
                ['label_tools_icon', label_tools_icon or 'fas fa-tools'])
            ticket_db.query('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', 
                ['label_consumables_name', label_consumables_name or 'Verbrauchsmaterial'])
            ticket_db.query('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', 
                ['label_consumables_icon', label_consumables_icon or 'fas fa-box-open'])
            
            # Speichere Server-Einstellungen in der inventory.db
            Database.query('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            ''', ['server_mode', '1' if mode == 'server' else '0'])
            if mode == 'client' and server_url:
                Database.query('''
                    INSERT OR REPLACE INTO settings (key, value)
                    VALUES (?, ?)
                ''', ['server_url', server_url])
            
            if mode == 'server':
                Config.init_server()
                flash('Server-Modus aktiviert', 'success')
            else:
                Config.init_client(server_url)
                flash('Client-Modus aktiviert', 'success')
                
            flash('Einstellungen erfolgreich gespeichert', 'success')
            return redirect(url_for('admin.server_settings'))
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Einstellungen: {str(e)}")
            flash('Fehler beim Speichern der Einstellungen', 'error')
            return redirect(url_for('admin.server_settings'))
    
    # Lade die aktuellen Einstellungen
    app_labels = get_app_labels()
    return render_template('admin/system.html', app_labels=app_labels)

@bp.route('/export/all')
@mitarbeiter_required
def export_all_data():
    """Exportiert alle relevanten Tabellen in eine Excel-Datei mit mehreren Sheets"""
    try:
        with Database.get_db() as conn:
            # Daten abrufen (ähnlich wie in der alten export_table Funktion)
            tools_data = [dict(row) for row in conn.execute("""
                SELECT barcode, name, category, location, status, description 
                FROM tools WHERE deleted = 0 ORDER BY name
            """).fetchall()]
            
            workers_data = [dict(row) for row in conn.execute("""
                SELECT barcode, firstname, lastname, department, email 
                FROM workers WHERE deleted = 0 ORDER BY lastname, firstname
            """).fetchall()]
            
            consumables_data = [dict(row) for row in conn.execute("""
                SELECT barcode, name, category, location, quantity, min_quantity, 
                       description 
                FROM consumables WHERE deleted = 0 ORDER BY name
            """).fetchall()]
            
            history_data = [dict(row) for row in conn.execute("""
                SELECT 
                    l.lent_at, l.returned_at, t.name as tool_name, t.barcode as tool_barcode,
                    w.firstname || ' ' || w.lastname as worker_name, w.barcode as worker_barcode,
                    'Werkzeug Ausleihe' as type, NULL as quantity
                FROM lendings l
                JOIN tools t ON l.tool_barcode = t.barcode
                JOIN workers w ON l.worker_barcode = w.barcode
                UNION ALL
                SELECT 
                    cu.used_at as lent_at, NULL as returned_at, c.name as consumable_name, c.barcode as consumable_barcode, 
                    w.firstname || ' ' || w.lastname as worker_name, w.barcode as worker_barcode,
                    'Material Verbrauch' as type, cu.quantity
                FROM consumable_usages cu
                JOIN consumables c ON cu.consumable_barcode = c.barcode
                JOIN workers w ON cu.worker_barcode = w.barcode
                ORDER BY lent_at DESC
            """).fetchall()]

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
        logger.error(f"Fehler beim Gesamtexport: {str(e)}", exc_info=True)
        flash(f'Fehler beim Erstellen des Gesamtexports: {str(e)}', 'error')
        # Leitet zur Systemseite zurück, falls ein Fehler auftritt
        # Alternativ könnte man zum Dashboard oder einer Fehlerseite leiten
        return redirect(url_for('admin.system')) 

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

                            Database.query('''
                                INSERT OR REPLACE INTO tools
                                (barcode, name, description, category, location, status, deleted)
                                VALUES (?, ?, ?, ?, ?, ?, 0)
                            ''', [row_data['barcode'], row_data['name'], desc, cat, loc, status])
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

                            Database.query('''
                                INSERT OR REPLACE INTO workers
                                (barcode, firstname, lastname, department, email, deleted)
                                VALUES (?, ?, ?, ?, ?, 0)
                            ''', [row_data['barcode'], row_data['firstname'], row_data['lastname'], dept, email])
                            imported_counts["Mitarbeiter"] += 1
                    except Exception as e:
                        errors.append(f"Fehler in Mitarbeiter Zeile {row_idx}: {e}")
        else:
            errors.append("Arbeitsblatt 'Mitarbeiter' nicht gefunden.")

        # --- Verbrauchsmaterial importieren ---
        if "Verbrauchsmaterial" in wb.sheetnames:
            ws_consumables = wb["Verbrauchsmaterial"]
            headers_consumables = [cell.value for cell in ws_consumables[1]]
            required_consumables_cols = ['barcode', 'name', 'quantity', 'min_quantity']
            if not all(col in headers_consumables for col in required_consumables_cols):
                 errors.append("Arbeitsblatt 'Verbrauchsmaterial' hat ungültige Spaltenüberschriften.")
            else:
                for row_idx, row in enumerate(ws_consumables.iter_rows(min_row=2), start=2):
                    row_data = {headers_consumables[i]: cell.value for i, cell in enumerate(row)}
                    try:
                        # Prüfe, ob notwendige Spalten vorhanden sind und konvertiere Typen
                        barcode = row_data.get('barcode')
                        name = row_data.get('name')
                        quantity_val = row_data.get('quantity')
                        min_quantity_val = row_data.get('min_quantity')

                        if barcode and name and quantity_val is not None and min_quantity_val is not None:
                            quantity = int(quantity_val)
                            min_quantity = int(min_quantity_val)
                            desc = row_data.get('description', '')
                            cat = row_data.get('category')
                            loc = row_data.get('location')

                            Database.query('''
                                INSERT OR REPLACE INTO consumables
                                (barcode, name, description, quantity, min_quantity, category, location, deleted)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                            ''', [barcode, name, desc, quantity, min_quantity, cat, loc])
                            imported_counts["Verbrauchsmaterial"] += 1
                    except ValueError:
                        errors.append(f"Fehler in Verbrauchsmaterial Zeile {row_idx}: Menge oder Mindestmenge ist keine Zahl.")
                    except Exception as e:
                        errors.append(f"Fehler in Verbrauchsmaterial Zeile {row_idx}: {e}")
        else:
            errors.append("Arbeitsblatt 'Verbrauchsmaterial' nicht gefunden.")

        # Feedback geben
        if not errors:
            flash(f'Gesamtimport erfolgreich! '
                  f'{imported_counts["Werkzeuge"]} Werkzeuge, '
                  f'{imported_counts["Mitarbeiter"]} Mitarbeiter, '
                  f'{imported_counts["Verbrauchsmaterial"]} Verbrauchsmaterialien importiert/aktualisiert.', 'success')
        else:
            # Zeige nur eine allgemeine Fehlermeldung und spezifische Fehler im Log
            flash(f'Import teilweise fehlgeschlagen. {len(errors)} Fehler aufgetreten (siehe Logs für Details). '
                   f'{imported_counts["Werkzeuge"]} Werkzeuge, '
                   f'{imported_counts["Mitarbeiter"]} Mitarbeiter, '
                   f'{imported_counts["Verbrauchsmaterial"]} Verbrauchsmaterialien importiert/aktualisiert.', 'warning')
            for error in errors:
                logger.error(f"Gesamtimport Fehler: {error}")

    except Exception as e:
        logger.error(f"Schwerwiegender Fehler beim Gesamtimport: {str(e)}", exc_info=True)
        flash(f'Schwerwiegender Fehler beim Import: {str(e)}', 'error')

    return redirect(url_for('admin.system'))

@bp.route('/backup/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Erstelle ein manuelles Backup"""
    try:
        success = backup_manager.create_backup()
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Backup wurde erfolgreich erstellt'
            })
        else:
            logger.error(f"backup_manager.create_backup() returned False in route")
            return jsonify({
                'status': 'error',
                'message': 'Fehler beim Erstellen des Backups. Prüfen Sie die Logs.'
            }), 500
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Backups in Route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Interner Serverfehler: {str(e)}'
        }), 500

@bp.route('/backup/restore/<filename>', methods=['POST'])
@admin_required
def restore_backup(filename):
    """Backup wiederherstellen und Neustart-Trigger setzen."""
    try:
        logger.info(f"Versuche Backup wiederherzustellen: {filename}")
        backup_path = backup_manager.backup_dir / filename
        if not backup_path.exists():
            error_msg = 'Backup-Datei nicht gefunden'
            logger.error(f"{error_msg}: {backup_path}")
            return jsonify({'status': 'error', 'message': error_msg}), 404

        # Datenbank wiederherstellen
        success = backup_manager.restore_backup(filename)
        if success:
            success_msg = 'Backup wurde erfolgreich wiederhergestellt.'
            logger.info(success_msg)

            # Neustart-Trigger setzen
            try:
                project_root = Path(current_app.root_path).parent
                restart_trigger_file = project_root / 'tmp' / 'needs_restart'
                restart_trigger_file.touch()
                logger.info(f"Neustart-Trigger-Datei berührt: {restart_trigger_file}")
                success_msg += " Neustart wurde ausgelöst (erfordert Prozessüberwachung)."
            except Exception as touch_err:
                logger.error(f"Konnte Neustart-Trigger-Datei nicht berühren: {touch_err}")
                success_msg += " Automatischer Neustart konnte nicht ausgelöst werden (Trigger-Datei-Fehler)."

            return jsonify({'status': 'success', 'message': success_msg})
        else:
            error_msg = 'Fehler bei der Wiederherstellung des Backups'
            logger.error(error_msg)
            return jsonify({'status': 'error', 'message': error_msg}), 500
    except Exception as e:
        error_msg = f'Fehler beim Löschen des Backups: {str(e)}'
        logger.error(error_msg, exc_info=True) # exc_info=True hinzugefügt
        # flash(error_msg, 'error') # Entfernt
        # return redirect(url_for('admin.dashboard')) # Entfernt
        return jsonify({'status': 'error', 'message': error_msg}), 500

@bp.route('/departments', methods=['GET'])
@mitarbeiter_required
def get_departments():
    """Hole alle Abteilungen"""
    try:
        departments = Database.query('''
            SELECT value as name
            FROM settings
            WHERE key LIKE 'department_%'
            AND value IS NOT NULL
            AND value != ''
            ORDER BY value
        ''')
        return jsonify({
            'success': True,
            'departments': [dept['name'] for dept in departments]
        })
    except Exception as e:
        print(f"Fehler beim Laden der Abteilungen: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/departments/add', methods=['POST'])
@mitarbeiter_required
def add_department():
    """Füge eine neue Abteilung hinzu"""
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'message': 'Kein Name angegeben'})
    
    try:
        db = Database.get_db()
        # Nächste freie ID finden
        result = db.execute("""
            SELECT MAX(CAST(SUBSTR(key, 12) AS INTEGER)) as max_id 
            FROM settings 
            WHERE key LIKE 'department_%'
        """).fetchone()
        next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
        
        # Neue Abteilung einfügen
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            [f'department_{next_id}', name]
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/departments/<name>', methods=['DELETE'])
@mitarbeiter_required
def delete_department(name):
    """Lösche eine Abteilung, prüft vorher auf Nutzung."""
    logger.info(f"Attempting to delete department: {name}")
    try:
        # Prüfen, ob die Abteilung noch verwendet wird
        usage_count = Database.query(
            "SELECT COUNT(*) as count FROM workers WHERE department = ? AND deleted = 0",
            [name],
            one=True
        )['count']
        
        if usage_count > 0:
            logger.warning(f"Cannot delete department '{name}': Still used by {usage_count} workers.")
            return jsonify({'success': False, 'message': f'Abteilung wird noch von {usage_count} Mitarbeitern verwendet.'}), 409 # 409 Conflict
            
        # Abteilung löschen
        Database.query(
            "DELETE FROM settings WHERE key LIKE 'department_%' AND value = ?",
            [name]
        )
        logger.info(f"Department '{name}' deleted successfully.")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting department '{name}': {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Fehler beim Löschen: {str(e)}'}), 500

# Standortverwaltung
@bp.route('/locations', methods=['GET'])
@mitarbeiter_required
def get_locations():
    """Hole alle Standorte"""
    try:
        locations = Database.query('''
            SELECT value as name, description
            FROM settings
            WHERE key LIKE 'location_%'
            AND value IS NOT NULL
            AND value != ''
            ORDER BY value
        ''')
        return jsonify({
            'success': True,
            'locations': locations
        })
    except Exception as e:
        print(f"Fehler beim Laden der Standorte: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/locations/add', methods=['POST'])
@admin_required
def add_location():
    """Füge einen neuen Standort hinzu"""
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'message': 'Kein Name angegeben'})
    
    try:
        db = Database.get_db()
        # Nächste freie ID finden
        result = db.execute("""
            SELECT MAX(CAST(SUBSTR(key, 10) AS INTEGER)) as max_id 
            FROM settings 
            WHERE key LIKE 'location_%'
            AND key NOT LIKE '%_tools'
            AND key NOT LIKE '%_consumables'
        """).fetchone()
        next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
        
        # Neuen Standort einfügen
        db.execute(
            "INSERT INTO settings (key, value, description) VALUES (?, ?, ?)",
            [f'location_{next_id}', name, 'both']
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/locations/<name>', methods=['DELETE'])
@mitarbeiter_required
def delete_location(name):
    """Lösche einen Standort, prüft vorher auf Nutzung."""
    logger.info(f"Attempting to delete location: {name}")
    try:
        # Prüfen, ob der Standort noch verwendet wird (tools oder consumables)
        tool_usage = Database.query("SELECT COUNT(*) as count FROM tools WHERE location = ? AND deleted = 0", [name], one=True)['count']
        consumable_usage = Database.query("SELECT COUNT(*) as count FROM consumables WHERE location = ? AND deleted = 0", [name], one=True)['count']
        total_usage = tool_usage + consumable_usage
        
        if total_usage > 0:
            logger.warning(f"Cannot delete location '{name}': Still used by {total_usage} items ({tool_usage} tools, {consumable_usage} consumables).")
            return jsonify({'success': False, 'message': f'Standort wird noch von {total_usage} Inventar-Items verwendet.'}), 409 # 409 Conflict

        # Standort löschen
        Database.query(
            "DELETE FROM settings WHERE key LIKE 'location_%' AND value = ?",
            [name]
        )
        logger.info(f"Location '{name}' deleted successfully.")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting location '{name}': {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Fehler beim Löschen: {str(e)}'}), 500

# Kategorieverwaltung
@bp.route('/categories', methods=['GET'])
@mitarbeiter_required
def get_categories():
    """Hole alle Kategorien"""
    try:
        categories = Database.query('''
            SELECT value as name, description
            FROM settings
            WHERE key LIKE 'category_%'
            AND value IS NOT NULL
            AND value != ''
            ORDER BY value
        ''')
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        print(f"Fehler beim Laden der Kategorien: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/categories/add', methods=['POST'])
@mitarbeiter_required
def add_category():
    """Füge eine neue Kategorie hinzu"""
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'message': 'Kein Name angegeben'})
    
    try:
        db = Database.get_db()
        # Nächste freie ID finden
        result = db.execute("""
            SELECT MAX(CAST(SUBSTR(key, 10) AS INTEGER)) as max_id 
            FROM settings 
            WHERE key LIKE 'category_%'
            AND key NOT LIKE '%_tools'
            AND key NOT LIKE '%_consumables'
        """).fetchone()
        next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
        
        # Neue Kategorie einfügen
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            [f'category_{next_id}', name]
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/categories/<name>', methods=['PUT'])
@mitarbeiter_required
def update_category(name):
    """Aktualisiere eine Kategorie"""
    category = request.form.get('category')
    tools = request.form.get('tools') == 'true'
    consumables = request.form.get('consumables') == 'true'
    
    if not category:
        return jsonify({
            'success': False,
            'message': 'Kategoriename fehlt'
        }), 400

    try:
        # Finde den Basis-Schlüssel für die Kategorie
        category_key = Database.query('''
            SELECT key FROM settings 
            WHERE key LIKE 'category_%'
            AND key NOT LIKE '%_tools'
            AND key NOT LIKE '%_consumables'
            AND value = ?
        ''', [name], one=True)
        
        if not category_key:
            return jsonify({
                'success': False,
                'message': 'Kategorie nicht gefunden'
            }), 404
            
        base_key = category_key['key']
        
        # Aktualisiere die Kategorie und ihre Eigenschaften
        Database.query('''
            UPDATE settings 
            SET value = ?, modified_at = datetime('now'), sync_status = 'pending'
            WHERE key = ?
        ''', [category, base_key])
        
        Database.query('''
            UPDATE settings 
            SET value = ?, modified_at = datetime('now'), sync_status = 'pending'
            WHERE key = ?
        ''', ['1' if tools else '0', f'{base_key}_tools'])
        
        Database.query('''
            UPDATE settings 
            SET value = ?, modified_at = datetime('now'), sync_status = 'pending'
            WHERE key = ?
        ''', ['1' if consumables else '0', f'{base_key}_consumables'])

        return jsonify({
            'success': True,
            'message': 'Kategorie erfolgreich aktualisiert'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/categories/<name>', methods=['DELETE'])
@mitarbeiter_required
def delete_category(name):
    """Löscht eine Kategorie, prüft vorher auf Nutzung."""
    logger.info(f"Attempting to delete category: {name}")
    try:
        # Prüfen, ob die Kategorie noch verwendet wird (tools oder consumables)
        tool_usage = Database.query("SELECT COUNT(*) as count FROM tools WHERE category = ? AND deleted = 0", [name], one=True)['count']
        consumable_usage = Database.query("SELECT COUNT(*) as count FROM consumables WHERE category = ? AND deleted = 0", [name], one=True)['count']
        total_usage = tool_usage + consumable_usage
        
        if total_usage > 0:
            logger.warning(f"Cannot delete category '{name}': Still used by {total_usage} items ({tool_usage} tools, {consumable_usage} consumables).")
            return jsonify({'success': False, 'message': f'Kategorie wird noch von {total_usage} Inventar-Items verwendet.'}), 409 # 409 Conflict

        # Kategorie-Key finden (z.B. category_5)
        category_key_row = Database.query(
            "SELECT key FROM settings WHERE key LIKE 'category_%' AND value = ? AND key NOT LIKE '%_tools' AND key NOT LIKE '%_consumables'", 
            [name], 
            one=True
        )
        
        if not category_key_row:
            logger.warning(f"Category '{name}' not found in settings for deletion.")
            return jsonify({'success': False, 'message': 'Kategorie nicht gefunden.'}), 404
        
        base_key = category_key_row['key']
        
        # Alle zugehörigen Einträge löschen (Haupt-Eintrag, _tools, _consumables)
        # Es ist sicherer, die spezifischen Keys zu löschen, falls das LIKE-Muster zu breit ist.
        keys_to_delete = [base_key, f"{base_key}_tools", f"{base_key}_consumables"]
        placeholders = ',' . join('?' * len(keys_to_delete))
        sql = f"DELETE FROM settings WHERE key IN ({placeholders})"
        
        Database.query(sql, keys_to_delete)
        
        logger.info(f"Category '{name}' (keys: {keys_to_delete}) deleted successfully.")
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error deleting category '{name}': {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Fehler beim Löschen: {str(e)}'}), 500

@bp.route('/cleanup-database', methods=['POST'])
@admin_required
def cleanup_database():
    """Bereinigt die Datenbank von ungültigen Einträgen"""
    try:
        print("Starte Datenbankbereinigung...")
        with Database.get_db() as db:
            # Finde Ausleihungen für nicht existierende Werkzeuge
            invalid_lendings = db.execute('''
                SELECT l.*, t.barcode as tool_exists
                FROM lendings l
                LEFT JOIN tools t ON l.tool_barcode = t.barcode
                WHERE t.barcode IS NULL
                AND l.returned_at IS NULL
            ''').fetchall()
            
            print(f"Gefundene ungültige Ausleihungen: {len(invalid_lendings)}")
            for lending in invalid_lendings:
                print(f"Ungültige Ausleihe gefunden: {dict(lending)}")
            
            # Lösche ungültige Ausleihungen
            if invalid_lendings:
                db.execute('''
                    DELETE FROM lendings
                    WHERE id IN (
                        SELECT l.id
                        FROM lendings l
                        LEFT JOIN tools t ON l.tool_barcode = t.barcode
                        WHERE t.barcode IS NULL
                        AND l.returned_at IS NULL
                    )
                ''')
                db.commit()
                print(f"{len(invalid_lendings)} Ausleihungen wurden gelöscht")
                
            return jsonify({
                'success': True,
                'message': f'{len(invalid_lendings)} ungültige Ausleihungen wurden bereinigt'
            })
            
    except Exception as e:
        print(f"Fehler bei der Bereinigung: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Bereinigung: {str(e)}'
        }), 500

@bp.route('/departments/list')
@mitarbeiter_required
def list_departments():
    """Liste alle Abteilungen auf"""
    departments = Database.query("""
        SELECT value as name 
        FROM settings 
        WHERE key LIKE 'department_%'
        AND value IS NOT NULL 
        AND value != ''
        ORDER BY value
    """)
    return jsonify({'success': True, 'departments': [dict(dept) for dept in departments]})

@bp.route('/locations/list')
@mitarbeiter_required
def list_locations():
    """Liste alle Standorte auf"""
    locations = Database.query("""
        SELECT value as name, description as usage
        FROM settings 
        WHERE key LIKE 'location_%'
        AND value IS NOT NULL 
        AND value != ''
        ORDER BY value
    """)
    return jsonify({'success': True, 'locations': [dict(loc) for loc in locations]})

@bp.route('/categories/list')
@admin_required
def list_categories():
    """Liste alle Kategorien auf"""
    categories = Database.query("""
        SELECT value as name, description as usage
        FROM settings 
        WHERE key LIKE 'category_%'
        AND value IS NOT NULL 
        AND value != ''
        ORDER BY value
    """)
    return jsonify({'success': True, 'categories': [dict(cat) for cat in categories]})

@bp.route('/backup/list')
@admin_required
def list_backups():
    """Liste alle verfügbaren Backups auf"""
    try:
        backups = []
        backup_dir = backup_manager.backup_dir
        
        if backup_dir.exists():
            for backup_file in sorted(backup_dir.glob('*.db'), reverse=True):
                backups.append({
                    'name': backup_file.name,
                    'size': backup_file.stat().st_size,
                    'created': backup_file.stat().st_mtime
                })
        
        return jsonify({
            'status': 'success',
            'backups': backups
        })
    except Exception as e:
        logger.error(f"Fehler beim Auflisten der Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/backup/download/backup/<filename>')
@login_required
@admin_required
def download_backup(filename):
    """Lade ein bestimmtes Backup herunter"""
    try:
        backup_path = backup_manager.backup_dir / filename
        
        if not backup_path.exists():
            return jsonify({
                'status': 'error',
                'message': 'Backup nicht gefunden'
            }), 404
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Fehler beim Herunterladen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/backup/download/db')
@admin_required
def download_current_database():
    """Lade die aktuelle Datenbank herunter"""
    try:
        # Verwende den Datenbankpfad aus dem DatabaseBackup Manager
        db_path = backup_manager.db_path
        
        if not os.path.exists(db_path):
            return jsonify({
                'status': 'error',
                'message': 'Datenbank nicht gefunden'
            }), 404
        
        # Erstelle einen temporären Dateinamen mit Zeitstempel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'inventory_{timestamp}.db'
        
        return send_file(
            db_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Fehler beim Herunterladen der Datenbank: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/backup/upload', methods=['POST'])
@admin_required
def upload_backup():
    """Lade ein Backup hoch"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400
        
        if not file.filename.endswith('.db'):
            return jsonify({
                'status': 'error',
                'message': 'Nur .db-Dateien sind erlaubt'
            }), 400
        
        # Erstelle ein Backup der aktuellen Datenbank
        try:
            backup_manager.create_backup()
            logger.info("Backup der aktuellen Datenbank wurde erstellt")
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Fehler beim Erstellen des Backups: {str(e)}'
            }), 500
        
        # Speichere die neue Datenbank
        filename = secure_filename(file.filename)
        file_path = backup_manager.backup_dir / filename
        file.save(str(file_path))
        
        # Aktiviere die neue Datenbank
        try:
            backup_manager.restore_backup(filename)
            logger.info(f"Neue Datenbank {filename} wurde aktiviert")
        except Exception as e:
            logger.error(f"Fehler beim Aktivieren der neuen Datenbank: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Fehler beim Aktivieren der neuen Datenbank: {str(e)}'
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': 'Backup erfolgreich hochgeladen und aktiviert'
        })
    except Exception as e:
        logger.error(f"Fehler beim Hochladen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/notices')
@admin_required
def notices():
    """Zeigt die Verwaltungsseite für Startseiten-Hinweise"""
    with Database.get_db() as db:
        notices = db.execute('''
            SELECT * FROM homepage_notices 
            ORDER BY priority ASC, created_at DESC
        ''').fetchall()
    
    return render_template('admin/notices.html', notices=notices)

@bp.route('/notices/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_notice():
    """Erstellt einen neuen Hinweis"""
    if request.method == 'POST':
        try:
            title = request.form['title']
            content = request.form['content']
            priority = int(request.form.get('priority', 0))
            is_active = 'is_active' in request.form
            
            with Database.get_db() as db:
                db.execute('''
                    INSERT INTO homepage_notices (title, content, priority, is_active)
                    VALUES (?, ?, ?, ?)
                ''', [title, content, priority, is_active])
                db.commit()
            
            flash('Hinweis wurde erfolgreich erstellt', 'success')
            return redirect(url_for('admin.notices'))
        except Exception as e:
            flash(f'Fehler beim Erstellen des Hinweises: {str(e)}', 'error')
    
    return render_template('admin/notice_form.html')

@bp.route('/notices/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_notice(id):
    """Bearbeitet einen bestehenden Hinweis"""
    with Database.get_db() as db:
        notice = db.execute('SELECT * FROM homepage_notices WHERE id = ?', [id]).fetchone()
        
        if not notice:
            flash('Hinweis nicht gefunden', 'error')
            return redirect(url_for('admin.notices'))
        
        if request.method == 'POST':
            try:
                title = request.form['title']
                content = request.form['content']
                priority = int(request.form.get('priority', 0))
                is_active = 'is_active' in request.form
                
                db.execute('''
                    UPDATE homepage_notices 
                    SET title = ?, content = ?, priority = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', [title, content, priority, is_active, id])
                db.commit()
                
                flash('Hinweis wurde erfolgreich aktualisiert', 'success')
                return redirect(url_for('admin.notices'))
            except Exception as e:
                flash(f'Fehler beim Aktualisieren des Hinweises: {str(e)}', 'error')
        
        return render_template('admin/notice_form.html', notice=notice)

@bp.route('/notices/<int:id>/delete', methods=['POST'])
@admin_required
def delete_notice(id):
    """Löscht einen Hinweis"""
    try:
        with Database.get_db() as db:
            db.execute('DELETE FROM homepage_notices WHERE id = ?', [id])
            db.commit()
        
        flash('Hinweis wurde erfolgreich gelöscht', 'success')
    except Exception as e:
        flash(f'Fehler beim Löschen des Hinweises: {str(e)}', 'error')
    
    return redirect(url_for('admin.notices'))

@bp.route('/tickets')
@login_required
@admin_required
def tickets():
    from app.models.ticket_db import TicketDatabase
    ticket_db = TicketDatabase()
    
    # Filter aus Query-Parametern
    status = request.args.get('status')
    priority = request.args.get('priority')
    assigned_to = request.args.get('assigned_to')
    created_by = request.args.get('created_by')
    
    # Basis-Query
    query = """
        SELECT 
            t.*,
            datetime(t.created_at) as created_at,
            datetime(t.updated_at) as updated_at,
            t.due_date
        FROM tickets t
        WHERE 1=1
    """
    params = []
    
    # Filter anwenden
    if status and status != 'alle':
        query += " AND status = ?"
        params.append(status)
    if priority and priority != 'alle':
        query += " AND priority = ?"
        params.append(priority)
    if assigned_to:
        query += " AND assigned_to = ?"
        params.append(assigned_to)
    if created_by:
        query += " AND created_by = ?"
        params.append(created_by)
    
    query += " ORDER BY t.created_at DESC"
    
    tickets = ticket_db.query(query, params)
    
    # Konvertiere due_date in datetime-Objekte
    for ticket in tickets:
        if ticket['due_date']:
            try:
                ticket['due_date'] = datetime.strptime(ticket['due_date'], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket['due_date'] = None
    
    return render_template('tickets/index.html', tickets=tickets, now=datetime.now())

@bp.route('/system', methods=['GET', 'POST'])
@login_required
@admin_required
def system():
    """Zeigt die Systemeinstellungen an."""
    if request.method == 'POST':
        try:
            # Verarbeite Logo-Upload
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    Database.query('''INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)''', ['custom_logo', filename])
                    flash('Logo erfolgreich hochgeladen', 'success')
                else:
                    flash('Ungültiges Dateiformat. Erlaubt sind: PNG, JPG, JPEG, GIF', 'error')
            
            flash('Einstellungen erfolgreich gespeichert', 'success')
            return redirect(url_for('admin.system'))
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Einstellungen: {e}")
            flash('Fehler beim Speichern der Einstellungen', 'error')
            
    return render_template('admin/system.html')


@bp.route('/users')
@admin_required
def manage_users():
    """Zeigt die Benutzerverwaltungsseite."""
    try:
        # Hole alle Benutzer aus der Ticket-Datenbank
        users = ticket_db.query("SELECT id, username, email, role, is_active FROM users ORDER BY username")
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Benutzerliste: {e}", exc_info=True)
        flash("Fehler beim Laden der Benutzerliste.", "error")
        return redirect(url_for('admin.dashboard'))

@bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Zeigt das Formular zum Hinzufügen eines Benutzers oder verarbeitet es."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        role = request.form.get('role')
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')

        # Validierung
        if not all([username, password, password_confirm, role]):
            flash("Bitte alle erforderlichen Felder ausfüllen.", "error")
            return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender']) # Form erneut anzeigen

        if password != password_confirm:
            flash("Passwörter stimmen nicht überein.", "error")
            return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender']) # Form erneut anzeigen
            
        if role not in ['admin', 'mitarbeiter', 'anwender']:
             flash("Ungültige Rolle ausgewählt.", "error")
             return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender'])

        try:
            # User.create prüft bereits auf existierenden Usernamen/Email
            new_user = User.create(username=username, password=password, role=role, email=email or None, firstname=firstname, lastname=lastname)
            if new_user:
                flash(f"Benutzer '{username}' erfolgreich erstellt.", 'success')
                return redirect(url_for('admin.manage_users'))
            else:
                 # Sollte durch Prüfungen in User.create abgedeckt sein, aber sicherheitshalber
                 flash("Benutzer konnte nicht erstellt werden (unbekannter Fehler).", 'error')
        except ValueError as e:
            # Fehler von User.create (z.B. Benutzer existiert)
            flash(str(e), 'error')
        except Exception as e:
            logger.error(f"Fehler beim Erstellen von Benutzer {username}: {e}", exc_info=True)
            flash("Ein unerwarteter Fehler ist aufgetreten.", 'error')
        
        # Bei Fehler: Formular erneut anzeigen mit eingegebenen Daten (außer Passwort)
        return render_template('admin/user_form.html', 
                               roles=['admin', 'mitarbeiter', 'anwender'],
                               username=username, email=email, selected_role=role, firstname=firstname, lastname=lastname)

    # GET Request: Formular anzeigen
    return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender'])

@bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Zeigt das Formular zum Bearbeiten eines Benutzers oder verarbeitet es."""
    user = User.get_by_id(user_id)
    if not user:
        flash('Benutzer nicht gefunden.', 'error')
        return redirect(url_for('admin.manage_users'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        role = request.form.get('role')
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')

        # Validierung
        if not all([username, role]):
            flash("Bitte Benutzername und Rolle ausfüllen.", "error")
            return render_template('admin/user_form.html', 
                                   user=user,
                                   roles=['admin', 'mitarbeiter', 'anwender'],
                                   username=username, email=email, selected_role=role, firstname=firstname, lastname=lastname)

        if password and password != password_confirm:
            flash("Passwörter stimmen nicht überein.", "error")
            return render_template('admin/user_form.html', 
                                   user=user,
                                   roles=['admin', 'mitarbeiter', 'anwender'],
                                   username=username, email=email, selected_role=role, firstname=firstname, lastname=lastname)
        
        if role not in ['admin', 'mitarbeiter', 'anwender']:
             flash("Ungültige Rolle ausgewählt.", "error")
             return render_template('admin/user_form.html', 
                                   user=user,
                                   roles=['admin', 'mitarbeiter', 'anwender'],
                                   username=username, email=email, selected_role=role, firstname=firstname, lastname=lastname)

        try:
            # Prüfen, ob der Benutzername bereits von einem *anderen* Benutzer verwendet wird
            existing_user_by_name = User.get_by_username(username)
            if existing_user_by_name and existing_user_by_name.id != user_id:
                 flash(f"Benutzername '{username}' wird bereits verwendet.", 'error')
                 return render_template('admin/user_form.html', 
                                       user=user,
                                       roles=['admin', 'mitarbeiter', 'anwender'],
                                       username=username, email=email, selected_role=role, firstname=firstname, lastname=lastname)
                 
            # Prüfen, ob die E-Mail bereits von einem *anderen* Benutzer verwendet wird
            if email:
                existing_user_by_email = User.get_by_email(email)
                if existing_user_by_email and existing_user_by_email.id != user_id:
                    flash(f"E-Mail '{email}' wird bereits verwendet.", 'error')
                    return render_template('admin/user_form.html', 
                                           user=user,
                                           roles=['admin', 'mitarbeiter', 'anwender'],
                                           username=username, email=email, selected_role=role, firstname=firstname, lastname=lastname)

            # Update der Benutzerdaten
            update_data = {
                'username': username,
                'email': email or None,
                'role': role,
                'firstname': firstname,
                'lastname': lastname
            }
            
            # Passwort nur aktualisieren, wenn es eingegeben wurde
            if password:
                user.set_password(password)
                update_data['password_hash'] = user.password_hash

            # Aktualisiere die Datenbank (Ticketsystem!)
            ticket_db.query('''
                UPDATE users 
                SET username = :username, email = :email, role = :role, firstname = :firstname, lastname = :lastname
                WHERE id = :id
            ''', {'username': update_data['username'], 'email': update_data['email'], 'role': update_data['role'], 'firstname': update_data['firstname'], 'lastname': update_data['lastname'], 'id': user_id})
            
            # Wenn das Passwort geändert wurde, aktualisiere auch den Hash
            if 'password_hash' in update_data:
                 ticket_db.query('''
                    UPDATE users 
                    SET password_hash = :password_hash
                    WHERE id = :id
                 ''', {'password_hash': update_data['password_hash'], 'id': user_id})

            flash(f"Benutzer '{username}' erfolgreich aktualisiert.", 'success')
            return redirect(url_for('admin.manage_users'))

        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren von Benutzer {user_id}: {e}", exc_info=True)
            flash("Ein unerwarteter Fehler ist aufgetreten.", 'error')
            return render_template('admin/user_form.html', 
                                   user=user, 
                                   roles=['admin', 'mitarbeiter', 'anwender'],
                                   username=username, email=email, selected_role=role, firstname=firstname, lastname=lastname)

    # GET Request: Formular anzeigen
    return render_template('admin/user_form.html', user=user, roles=['admin', 'mitarbeiter', 'anwender'])

@bp.route('/users/toggle_active/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Aktiviert oder deaktiviert einen Benutzer."""
    user_to_toggle = User.get_by_id(user_id)

    if not user_to_toggle:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for('admin.manage_users'))

    # Verhindern, dass der aktuell eingeloggte Admin sich selbst deaktiviert
    if current_user.id == user_to_toggle.id and user_to_toggle.is_active:
        flash("Sie können sich nicht selbst deaktivieren.", "error")
        return redirect(url_for('admin.manage_users'))

    try:
        new_status = not user_to_toggle.is_active
        Database.query('''
            UPDATE users
            SET is_active = ?
            WHERE id = ?
        ''', [new_status, user_id])
        
        action = "aktiviert" if new_status else "deaktiviert"
        flash(f"Benutzer '{user_to_toggle.username}' wurde {action}.", 'success')
    except Exception as e:
        logger.error(f"Fehler beim Ändern des Aktivierungsstatus für Benutzer {user_id}: {e}", exc_info=True)
        flash("Ein Fehler ist beim Ändern des Benutzerstatus aufgetreten.", 'error')

    return redirect(url_for('admin.manage_users'))

@bp.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Löscht einen Benutzer."""
    user_to_delete = User.get_by_id(user_id)

    if not user_to_delete:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for('admin.manage_users'))

    # Verhindern, dass der aktuell eingeloggte Admin sich selbst löscht
    if current_user.id == user_to_delete.id:
        flash("Sie können sich nicht selbst löschen.", "error")
        return redirect(url_for('admin.manage_users'))

    try:
        Database.query('''
            DELETE FROM users
            WHERE id = ?
        ''', [user_id])
        
        flash(f"Benutzer '{user_to_delete.username}' wurde erfolgreich gelöscht.", 'success')
    except Exception as e:
        logger.error(f"Fehler beim Löschen von Benutzer {user_id}: {e}", exc_info=True)
        flash("Ein Fehler ist beim Löschen des Benutzers aufgetreten.", 'error')

    return redirect(url_for('admin.manage_users'))

@bp.app_context_processor
def inject_app_labels():
    return dict(app_labels=get_app_labels())

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
        with Database.get_db() as conn:
            # Prüfe ob das Werkzeug existiert und gelöscht ist
            tool = conn.execute('''
                SELECT * FROM tools 
                WHERE barcode = ? AND deleted = 1
            ''', [barcode]).fetchone()
            
            if not tool:
                return jsonify({
                    'success': False,
                    'message': 'Werkzeug nicht gefunden oder nicht gelöscht'
                }), 404
                
            # Lösche das Werkzeug endgültig
            conn.execute('DELETE FROM tools WHERE barcode = ?', [barcode])
            conn.commit()
            
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
        consumable = Database.query('SELECT * FROM consumables WHERE barcode = ?', [barcode])
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404
            
        # Prüfe ob das Verbrauchsmaterial bereits gelöscht ist
        if consumable[0]['deleted'] == 1:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial ist bereits gelöscht'}), 400
            
        # Führe das Soft-Delete durch
        Database.query('UPDATE consumables SET deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE barcode = ?', [barcode])
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial erfolgreich gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/consumables/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_consumable_permanent(barcode):
    try:
        # Prüfe ob das Verbrauchsmaterial existiert
        consumable = Database.query('SELECT * FROM consumables WHERE barcode = ?', [barcode])
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404
            
        # Prüfe ob das Verbrauchsmaterial bereits gelöscht ist
        if consumable[0]['deleted'] == 0:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial muss zuerst gelöscht werden'}), 400
            
        # Führe das permanente Löschen durch
        Database.query('DELETE FROM consumables WHERE barcode = ?', [barcode])
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial permanent gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Verbrauchsmaterials: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/workers/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_permanent(barcode):
    try:
        # Prüfe ob der Mitarbeiter existiert
        worker = Database.query('SELECT * FROM workers WHERE barcode = ?', [barcode])
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeiter nicht gefunden'}), 404
            
        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings = Database.query('SELECT COUNT(*) as count FROM lendings WHERE worker_barcode = ? AND returned_at IS NULL', [barcode])
        if active_lendings[0]['count'] > 0:
            return jsonify({'success': False, 'message': 'Mitarbeiter hat noch aktive Ausleihen'}), 400
            
        # Führe das permanente Löschen durch
        Database.query('DELETE FROM workers WHERE barcode = ?', [barcode])
        return jsonify({'success': True, 'message': 'Mitarbeiter permanent gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Mitarbeiters: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/tickets/<int:ticket_id>')
@login_required
@admin_required
def ticket_detail(ticket_id):
    """Zeigt die Details eines Tickets für Administratoren."""
    print(f"DEBUG: Ticket-Detail-Ansicht für Ticket {ticket_id} wird geladen")
    
    # Hole das Ticket
    ticket = ticket_db.query(
        """
        SELECT *
        FROM tickets
        WHERE id = ?
        """,
        [ticket_id],
        one=True
    )
    
    if not ticket:
        print(f"DEBUG: Ticket {ticket_id} nicht gefunden")
        flash('Ticket nicht gefunden', 'error')
        return redirect(url_for('admin.tickets'))
    
    print(f"DEBUG: Ticket gefunden: {ticket}")
    
    # Konvertiere Datumsfelder
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None
    
    # Hole die Notizen für das Ticket
    notes = ticket_db.get_ticket_notes(ticket_id)
    print(f"DEBUG: Gefundene Notizen: {notes}")
    
    # Hole die Nachrichten für das Ticket
    messages = ticket_db.get_ticket_messages(ticket_id)
    print(f"DEBUG: Gefundene Nachrichten: {messages}")
    
    # Hole die Historie des Tickets
    history = ticket_db.get_ticket_history(ticket_id)
    print(f"DEBUG: Gefundene Historie: {history}")
    
    # Hole alle Benutzer für die Zuweisung
    users = get_all_users()
    
    # Definiere die Kategorien
    categories = ['Hardware', 'Software', 'Netzwerk', 'Drucker', 'Sonstiges']
    
    # Definiere die Status-Farben
    status_colors = {
        'offen': 'danger',
        'in_bearbeitung': 'warning',
        'wartet_auf_antwort': 'info',
        'gelöst': 'success',
        'geschlossen': 'secondary'
    }
    
    return render_template('admin/ticket_detail.html',
                         ticket=ticket,
                         notes=notes,
                         messages=messages,
                         history=history,
                         users=users,
                         categories=categories,
                         status_colors=status_colors)

@bp.route('/tickets/<int:ticket_id>/message', methods=['POST'])
@login_required
@admin_required
def add_ticket_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu."""
    try:
        # Prüfe ob das Ticket existiert
        ticket = ticket_db.query(
            "SELECT * FROM tickets WHERE id = ?",
            [ticket_id],
            one=True
        )
        
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
        ticket_db.add_ticket_message(
            ticket_id=ticket_id,
            message=message,
            sender=current_user.username,
            is_admin=True
        )

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

@bp.route('/tickets/<int:ticket_id>/note', methods=['POST'])
@login_required
@admin_required
def add_ticket_note(ticket_id):
    """Fügt eine neue Notiz zu einem Ticket hinzu (immer öffentlich, keine Unterscheidung mehr)."""
    try:
        print(f"DEBUG: Notiz-Anfrage für Ticket {ticket_id} erhalten")
        # Hole das Ticket
        ticket = ticket_db.query(
            """
            SELECT *
            FROM tickets
            WHERE id = ?
            """,
            [ticket_id],
            one=True
        )
        
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
        # is_private wird ignoriert, alle Notizen sind öffentlich
        
        if not note or not note.strip():
            print("DEBUG: Notiz ist leer")
            return jsonify({
                'success': False,
                'message': 'Notiz ist erforderlich'
            }), 400

        print(f"DEBUG: Notiz hinzufügen: {note}")
        # Füge die Notiz hinzu (immer is_private=0)
        with ticket_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ticket_notes (ticket_id, note, created_by, is_private, created_at)
                VALUES (?, ?, ?, 0, datetime('now'))
                """,
                [ticket_id, note.strip(), current_user.username]
            )
            
            # Aktualisiere das updated_at Feld des Tickets
            cursor.execute(
                """
                UPDATE tickets
                SET updated_at = datetime('now')
                WHERE id = ?
                """,
                [ticket_id]
            )
            
            conn.commit()

            # Hole die eingefügte Notiz
            cursor.execute(
                """
                SELECT id, note, created_by, is_private, created_at
                FROM ticket_notes
                WHERE ticket_id = ? AND created_by = ? AND note = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                [ticket_id, current_user.username, note.strip()]
            )
            new_note = cursor.fetchone()

            if not new_note:
                print("DEBUG: Fehler beim Abrufen der neuen Notiz")
                return jsonify({
                    'success': False,
                    'message': 'Fehler beim Abrufen der Notiz'
                }), 500

            print(f"DEBUG: Notiz erfolgreich hinzugefügt: {new_note}")
            return jsonify({
                'success': True,
                'message': 'Notiz wurde gespeichert',
                'note': {
                    'id': new_note['id'],
                    'note': new_note['note'],
                    'created_by': new_note['created_by'],
                    'is_private': 0,
                    'created_at': new_note['created_at']
                }
            })

    except Exception as e:
        print(f"DEBUG: Fehler beim Hinzufügen der Notiz: {e}")
        logging.error(f"Fehler beim Hinzufügen der Notiz: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Speichern der Notiz: {str(e)}'
        }), 500

@bp.route('/tickets/<int:ticket_id>/update', methods=['POST'])
@login_required
@admin_required
def update_ticket(ticket_id):
    """Aktualisiert ein Ticket."""
    try:
        print(f"DEBUG: Update-Ticket-Anfrage für Ticket {ticket_id} erhalten")
        status = request.form.get('status')
        assigned_to = request.form.get('assigned_to')
        category = request.form.get('category')
        due_date = request.form.get('due_date')
        estimated_time = request.form.get('estimated_time')
        actual_time = request.form.get('actual_time')
        
        print(f"DEBUG: Empfangene Daten: status={status}, assigned_to={assigned_to}, category={category}, due_date={due_date}, estimated_time={estimated_time}, actual_time={actual_time}")
        
        # Konvertiere due_date in datetime wenn vorhanden
        if due_date:
            try:
                # Füge die Uhrzeit 23:59:59 hinzu, wenn nur das Datum angegeben wurde
                if len(due_date) == 10:  # Format: YYYY-MM-DD
                    due_date = f"{due_date} 23:59:59"
                due_date = datetime.strptime(due_date, '%Y-%m-%d %H:%M:%S')
                print(f"DEBUG: due_date konvertiert: {due_date}")
            except ValueError as e:
                print(f"DEBUG: Fehler bei der Konvertierung von due_date: {e}")
                due_date = None
        else:
            due_date = None
        
        # Konvertiere Zeitfelder in Integer
        if estimated_time:
            try:
                estimated_time = int(estimated_time)
                print(f"DEBUG: estimated_time konvertiert: {estimated_time}")
            except ValueError as e:
                print(f"DEBUG: Fehler bei der Konvertierung von estimated_time: {e}")
                estimated_time = None
        if actual_time:
            try:
                actual_time = int(actual_time)
                print(f"DEBUG: actual_time konvertiert: {actual_time}")
            except ValueError as e:
                print(f"DEBUG: Fehler bei der Konvertierung von actual_time: {e}")
                actual_time = None
        
        # Aktualisiere das Ticket
        with ticket_db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Hole das alte Ticket für die Historie
            cursor.execute("SELECT * FROM tickets WHERE id = ?", [ticket_id])
            old_ticket = cursor.fetchone()
            
            if not old_ticket:
                raise ValueError("Ticket nicht gefunden")
            
            # Aktualisiere das Ticket
            cursor.execute("""
                UPDATE tickets 
                SET status = ?,
                    assigned_to = ?,
                    category = ?,
                    due_date = ?,
                    estimated_time = ?,
                    actual_time = ?,
                    last_modified_by = ?,
                    last_modified_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    resolved_at = CASE 
                        WHEN ? = 'gelöst' THEN CURRENT_TIMESTAMP 
                        ELSE NULL 
                    END
                WHERE id = ?
            """, [status, assigned_to, category, due_date, estimated_time, actual_time, 
                  current_user.username, status, ticket_id])
            
            # Erstelle Historie-Einträge für geänderte Felder
            changes = []
            if old_ticket['status'] != status:
                changes.append(('status', old_ticket['status'], status))
            if old_ticket['assigned_to'] != assigned_to:
                changes.append(('assigned_to', old_ticket['assigned_to'], assigned_to))
            if old_ticket['category'] != category:
                changes.append(('category', old_ticket['category'], category))
            if old_ticket['due_date'] != due_date:
                changes.append(('due_date', old_ticket['due_date'], due_date))
            if old_ticket['estimated_time'] != estimated_time:
                changes.append(('estimated_time', old_ticket['estimated_time'], estimated_time))
            if old_ticket['actual_time'] != actual_time:
                changes.append(('actual_time', old_ticket['actual_time'], actual_time))
            
            # Füge Historie-Einträge hinzu
            for field_name, old_value, new_value in changes:
                cursor.execute("""
                    INSERT INTO ticket_history 
                    (ticket_id, field_name, old_value, new_value, changed_by)
                    VALUES (?, ?, ?, ?, ?)
                """, [ticket_id, field_name, str(old_value), str(new_value), current_user.username])
            
            conn.commit()
        
        print(f"DEBUG: Ticket {ticket_id} erfolgreich aktualisiert")
        flash('Ticket wurde erfolgreich aktualisiert', 'success')
    except Exception as e:
        print(f"DEBUG: Fehler beim Aktualisieren des Tickets: {e}")
        flash(f'Fehler beim Aktualisieren des Tickets: {str(e)}', 'error')
    
    return redirect(url_for('admin.ticket_detail', ticket_id=ticket_id))

@bp.route('/tools/add', methods=['POST'])
@mitarbeiter_required
def add_tool():
    """Fügt ein neues Werkzeug hinzu"""
    try:
        data = {
            'barcode': request.form.get('barcode'),
            'name': request.form.get('name'),
            'category': request.form.get('category'),
            'location': request.form.get('location'),
            'status': request.form.get('status', 'verfügbar'),
            'description': request.form.get('description')
        }
        
        # Validiere die Eingabedaten
        is_valid, error_message = validate_input('tools', data)
        if not is_valid:
            flash(error_message, 'error')
            return redirect(url_for('admin.tools'))
            
        # Validiere die Länge des Namens
        if len(data['name']) > 50:
            flash('Der Name darf maximal 50 Zeichen lang sein', 'error')
            return redirect(url_for('admin.tools'))
        
        # Kürze die Felder auf die maximale Länge
        for field in data:
            if isinstance(data[field], str):
                data[field] = truncate_field('tools', field, data[field])
        
        with Database.get_db() as conn:
            # Prüfe ob der Barcode bereits existiert
            existing = conn.execute('''
                SELECT barcode FROM tools 
                WHERE barcode = ? AND deleted = 0
            ''', [data['barcode']]).fetchone()
            
            if existing:
                flash('Ein Werkzeug mit diesem Barcode existiert bereits', 'error')
                return redirect(url_for('admin.tools'))
            
            # Füge das Werkzeug hinzu
            conn.execute('''
                INSERT INTO tools (
                    barcode, name, category, location, status, description,
                    created_at, updated_at, sync_status
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 'pending')
            ''', [
                data['barcode'], data['name'], data['category'],
                data['location'], data['status'], data['description']
            ])
            
            conn.commit()
            flash('Werkzeug wurde erfolgreich hinzugefügt', 'success')
            
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Werkzeugs: {str(e)}")
        flash(f'Fehler beim Hinzufügen des Werkzeugs: {str(e)}', 'error')
    
    return redirect(url_for('admin.tools'))

@bp.route('/tools/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_tool():
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400
            
        barcode = data['barcode']
        
        # Validiere Barcode-Länge
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode ist zu lang (maximal 50 Zeichen)'}), 400
            
        # Prüfe ob das Werkzeug existiert
        tool = Database.query('SELECT * FROM tools WHERE barcode = ?', [barcode])
        if not tool:
            return jsonify({'success': False, 'message': 'Werkzeug nicht gefunden'}), 404
            
        # Prüfe ob das Werkzeug ausgeliehen ist
        if tool[0]['status'] == 'ausgeliehen':
            return jsonify({'success': False, 'message': 'Werkzeug kann nicht gelöscht werden, da es ausgeliehen ist'}), 400
            
        # Führe das Soft-Delete durch
        Database.query('UPDATE tools SET deleted = 1 WHERE barcode = ?', [barcode])
        return jsonify({'success': True, 'message': 'Werkzeug erfolgreich gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen des Werkzeugs'}), 500

@bp.route('/workers/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_soft():
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400
            
        barcode = data['barcode']
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode zu lang (max. 50 Zeichen)'}), 400
            
        # Prüfe ob der Mitarbeiter existiert
        worker = Database.query('SELECT * FROM workers WHERE barcode = ?', [barcode])
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeiter nicht gefunden'}), 404
            
        # Prüfe ob der Mitarbeiter bereits gelöscht ist
        if worker[0]['deleted'] == 1:
            return jsonify({'success': False, 'message': 'Mitarbeiter ist bereits gelöscht'}), 400
            
        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings = Database.query('SELECT COUNT(*) as count FROM lendings WHERE worker_barcode = ? AND returned_at IS NULL', [barcode])
        if active_lendings[0]['count'] > 0:
            return jsonify({'success': False, 'message': 'Mitarbeiter hat noch aktive Ausleihen'}), 400
            
        # Führe das Soft-Delete durch
        Database.query('UPDATE workers SET deleted = 1, deleted_at = CURRENT_TIMESTAMP WHERE barcode = ?', [barcode])
        return jsonify({'success': True, 'message': 'Mitarbeiter erfolgreich gelöscht'})
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Mitarbeiters: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/available-logos')
@login_required
@admin_required
def available_logos():
    try:
        # Stelle sicher, dass der Ordner existiert
        logos_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
        os.makedirs(logos_dir, exist_ok=True)
        
        logos = []
        if os.path.exists(logos_dir):
            for filename in os.listdir(logos_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                    logos.append({
                        'name': filename,
                        'path': f'uploads/logos/{filename}'
                    })
        
        return jsonify({
            'success': True,
            'logos': logos
        })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Logos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Laden der Logos: {str(e)}'
        }), 500

@bp.route('/select-logo', methods=['POST'])
@login_required
@admin_required
def select_logo():
    data = request.get_json()
    if not data or 'path' not in data:
        return jsonify({'success': False, 'message': 'Kein Logo-Pfad angegeben'})
    
    logo_path = data['path']
    # Speichere den Pfad in der Datenbank
    Database.query('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
                  ['custom_logo', logo_path])
    
    return jsonify({
        'success': True,
        'message': 'Logo erfolgreich ausgewählt'
    })

@bp.route('/upload-logo', methods=['POST'])
@login_required
@admin_required
def upload_logo():
    if 'logo' not in request.files:
        return jsonify({'success': False, 'message': 'Keine Datei hochgeladen'}), 400
        
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Keine Datei ausgewählt'}), 400
        
    if file and allowed_file(file.filename):
        try:
            # Erstelle den Logos-Ordner, falls er nicht existiert
            logos_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
            os.makedirs(logos_dir, exist_ok=True)
            
            # Generiere einen eindeutigen Dateinamen
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            
            # Speichere die Datei
            file_path = os.path.join(logos_dir, filename)
            file.save(file_path)
            
            # Gib den relativen Pfad zurück
            relative_path = f"uploads/logos/{filename}"
            return jsonify({
                'success': True,
                'message': 'Logo erfolgreich hochgeladen',
                'path': relative_path
            })
            
        except Exception as e:
            current_app.logger.error(f'Fehler beim Hochladen des Logos: {str(e)}')
            return jsonify({'success': False, 'message': 'Fehler beim Hochladen des Logos'}), 500
            
    return jsonify({'success': False, 'message': 'Ungültiges Dateiformat'}), 400

@bp.route('/delete-logo', methods=['POST'])
@login_required
@admin_required
def delete_logo():
    try:
        data = request.get_json()
        if not data or 'path' not in data:
            return jsonify({'success': False, 'message': 'Kein Logo-Pfad angegeben'}), 400
            
        logo_path = data['path']
        
        # Verhindere das Löschen des BTZ-Logos
        if logo_path == 'uploads/logos/btz-logo.png':
            return jsonify({'success': False, 'message': 'Das BTZ-Logo kann nicht gelöscht werden'}), 400
            
        # Konstruiere den vollständigen Pfad
        full_path = os.path.join(current_app.root_path, 'static', logo_path)
        
        # Prüfe ob die Datei existiert
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'message': 'Logo nicht gefunden'}), 404
            
        # Lösche die Datei
        os.remove(full_path)
        
        return jsonify({'success': True, 'message': 'Logo erfolgreich gelöscht'})
        
    except Exception as e:
        current_app.logger.error(f'Fehler beim Löschen des Logos: {str(e)}')
        return jsonify({'success': False, 'message': 'Fehler beim Löschen des Logos'}), 500

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS