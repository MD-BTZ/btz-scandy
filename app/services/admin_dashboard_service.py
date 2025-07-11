"""
Admin Dashboard Service

Dieser Service enthält alle Funktionen für das Admin-Dashboard,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class AdminDashboardService:
    """Service für Admin-Dashboard-Funktionen"""
    
    @staticmethod
    def get_recent_activity() -> List[Dict[str, Any]]:
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
                    # Konvertiere lent_at zu datetime falls es ein String ist
                    lent_at = lending['lent_at']
                    if isinstance(lent_at, str):
                        try:
                            lent_at = datetime.fromisoformat(lent_at.replace('Z', '+00:00'))
                        except:
                            lent_at = datetime.now()
                    
                    activities.append({
                        'type': 'lending',
                        'timestamp': lent_at,
                        'description': f'Werkzeug "{tool["name"]}" an {worker["firstname"]} {worker["lastname"]} ausgeliehen',
                        'icon': 'fas fa-tools'
                    })
            
            # Verbrauchsmaterial verarbeiten
            for usage in recent_usages:
                consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
                worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
                
                if consumable and worker:
                    # Konvertiere used_at zu datetime falls es ein String ist
                    used_at = usage['used_at']
                    if isinstance(used_at, str):
                        try:
                            used_at = datetime.fromisoformat(used_at.replace('Z', '+00:00'))
                        except:
                            used_at = datetime.now()
                    
                    activities.append({
                        'type': 'usage',
                        'timestamp': used_at,
                        'description': f'{usage["quantity"]}x "{consumable["name"]}" an {worker["firstname"]} {worker["lastname"]} ausgegeben',
                        'icon': 'fas fa-box-open'
                    })
            
            # Nach Zeitstempel sortieren und die letzten 10 zurückgeben
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            return activities[:10]
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der letzten Aktivitäten: {str(e)}")
            return []

    @staticmethod
    def get_material_usage() -> Dict[str, Any]:
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
                        '_id': '$consumable.name',
                        'total_quantity': {'$sum': '$quantity'},
                        'usage_count': {'$sum': 1}
                    }
                },
                {
                    '$sort': {'total_quantity': -1}
                },
                {
                    '$limit': 10
                }
            ]
            
            usage_data = list(mongodb.aggregate('consumable_usages', pipeline))
            
            return {
                'usage_data': usage_data,
                'period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Materialnutzung: {str(e)}")
            return {'usage_data': [], 'period_days': 30}

    @staticmethod
    def get_warnings() -> Dict[str, List[Dict[str, Any]]]:
        """Hole alle Warnungen für das Dashboard"""
        try:
            warnings = {
                'defect_tools': [],
                'overdue_lendings': [],
                'low_stock_consumables': []
            }
            
            # Defekte Werkzeuge
            defect_tools = list(mongodb.find('tools', {'status': 'defekt', 'deleted': {'$ne': True}}))
            for tool in defect_tools:
                warnings['defect_tools'].append({
                    'name': tool['name'],
                    'barcode': tool['barcode'],
                    'status': 'defekt',
                    'severity': 'error'
                })
            
            # Überfällige Ausleihen (mehr als 5 Tage)
            overdue_date = datetime.now() - timedelta(days=5)
            overdue_lendings = list(mongodb.find('lendings', {
                'returned_at': None,
                'lent_at': {'$lt': overdue_date}
            }))
            
            for lending in overdue_lendings:
                tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
                worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
                
                if tool and worker:
                    days_overdue = (datetime.now() - lending['lent_at']).days
                    warnings['overdue_lendings'].append({
                        'tool_name': tool['name'],
                        'worker_name': f"{worker['firstname']} {worker['lastname']}",
                        'days_overdue': days_overdue,
                        'lent_at': lending['lent_at'],
                        'severity': 'warning' if days_overdue <= 7 else 'error'
                    })
            
            # Niedrige Bestände bei Verbrauchsmaterial
            low_stock_consumables = list(mongodb.find('consumables', {
                'deleted': {'$ne': True},
                '$expr': {'$lte': ['$quantity', '$min_quantity']}
            }))
            
            for consumable in low_stock_consumables:
                warnings['low_stock_consumables'].append({
                    'name': consumable['name'],
                    'barcode': consumable['barcode'],
                    'current_quantity': consumable['quantity'],
                    'min_quantity': consumable['min_quantity'],
                    'severity': 'error' if consumable['quantity'] == 0 else 'warning'
                })
            
            return warnings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Warnungen: {str(e)}")
            return {'defect_tools': [], 'overdue_lendings': [], 'low_stock_consumables': []}

    @staticmethod
    def get_backup_info() -> Dict[str, Any]:
        """Hole Backup-Informationen"""
        try:
            from app.utils.backup_manager import backup_manager
            
            backup_dir = backup_manager.backup_dir
            backups = []
            
            if backup_dir.exists():
                for backup_file in backup_dir.glob('*.json'):
                    if backup_file.is_file():
                        stat = backup_file.stat()
                        backups.append({
                            'filename': backup_file.name,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'size_mb': round(stat.st_size / (1024 * 1024), 2)
                        })
            
            # Sortiere nach Änderungsdatum (neueste zuerst)
            backups.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                'backups': backups,
                'total_count': len(backups),
                'total_size_mb': sum(b['size_mb'] for b in backups)
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Informationen: {str(e)}")
            return {'backups': [], 'total_count': 0, 'total_size_mb': 0}

    @staticmethod
    def get_consumables_forecast() -> List[Dict[str, Any]]:
        """Hole Verbrauchsmaterial-Prognosen"""
        try:
            # Verwende den zentralen Statistics Service
            from app.services.statistics_service import StatisticsService
            stats = StatisticsService.get_all_statistics()
            return stats.get('consumables_forecast', [])
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Prognosen: {str(e)}")
            return []

    @staticmethod
    def get_consumable_trend() -> Dict[str, Any]:
        """Hole Verbrauchsmaterial-Trends für Charts"""
        try:
            # Berechne Trend der letzten 30 Tage
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            pipeline = [
                {
                    '$match': {
                        'used_at': {'$gte': thirty_days_ago}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$used_at'}},
                            'consumable': '$consumable_barcode'
                        },
                        'total_quantity': {'$sum': '$quantity'}
                    }
                },
                {
                    '$group': {
                        '_id': '$_id.date',
                        'total_usage': {'$sum': '$total_quantity'}
                    }
                },
                {
                    '$sort': {'_id': 1}
                }
            ]
            
            trend_data = list(mongodb.aggregate('consumable_usages', pipeline))
            
            # Formatiere Daten für Chart.js
            labels = [item['_id'] for item in trend_data]
            data = [abs(item['total_usage']) for item in trend_data]  # Absolutwert da quantity negativ ist
            
            return {
                'labels': labels,
                'datasets': [{
                    'label': 'Täglicher Verbrauch',
                    'data': data,
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'tension': 0.1
                }]
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Trends: {str(e)}")
            return {'labels': [], 'datasets': []} 