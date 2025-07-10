"""
Zentraler Statistics Service für Scandy
Berechnet alle Statistiken an einem Ort und macht sie wiederverwendbar
"""
from typing import Dict, Any, List
from datetime import datetime
from app.models.mongodb_database import mongodb
from app.models.mongodb_models import MongoDBTool
import logging

logger = logging.getLogger(__name__)

class StatisticsService:
    """Zentraler Service für alle Statistiken"""
    
    @staticmethod
    def get_all_statistics() -> Dict[str, Any]:
        """
        Lädt alle Statistiken auf einmal.
        Wiederverwendbar für Dashboard, Admin-Dashboard und Startseite.
        """
        try:
            # Basis-Statistiken von MongoDBTool
            base_stats = MongoDBTool.get_statistics()
            
            # Ticket-Statistiken
            ticket_stats = StatisticsService._get_ticket_statistics()
            
            # Duplikat-Barcodes
            duplicate_barcodes = MongoDBTool.get_duplicate_barcodes()
            
            # Bestandsprognose
            consumables_forecast = MongoDBTool.get_consumables_forecast()
            
            return {
                'tool_stats': base_stats['tool_stats'],
                'consumable_stats': base_stats['consumable_stats'],
                'worker_stats': base_stats['worker_stats'],
                'ticket_stats': ticket_stats,
                'duplicate_barcodes': duplicate_barcodes,
                'consumables_forecast': consumables_forecast
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Statistiken: {str(e)}")
            return StatisticsService._get_fallback_statistics()
    
    @staticmethod
    def _get_ticket_statistics() -> Dict[str, int]:
        """Berechnet Ticket-Statistiken"""
        try:
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
            return ticket_stats_result[0] if ticket_stats_result else {
                'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0
            }
            
        except Exception as e:
            logger.error(f"Fehler bei Ticket-Statistiken: {str(e)}")
            return {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
    
    @staticmethod
    def _get_fallback_statistics() -> Dict[str, Any]:
        """Fallback-Statistiken bei Fehlern"""
        return {
            'tool_stats': {'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
            'consumable_stats': {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
            'worker_stats': {'total': 0, 'by_department': []},
            'ticket_stats': {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0},
            'duplicate_barcodes': [],
            'consumables_forecast': []
        }
    
    @staticmethod
    def get_notices() -> List[Dict[str, Any]]:
        """Lädt aktive Hinweise aus der Datenbank"""
        try:
            notices = mongodb.find('homepage_notices', {'is_active': True})
            # Sortiere nach Priorität und Erstellungsdatum
            notices.sort(key=lambda x: (x.get('priority', 0), x.get('created_at', datetime.min)), reverse=True)
            return notices
        except Exception as e:
            logger.error(f"Fehler beim Laden der Hinweise: {str(e)}")
            return [] 