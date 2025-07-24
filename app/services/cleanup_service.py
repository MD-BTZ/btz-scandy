"""
Cleanup Service für automatische Bereinigung abgelaufener Daten
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from app.services.admin_user_service import AdminUserService
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

class CleanupService:
    """Service für automatische Bereinigung abgelaufener Daten"""
    
    @staticmethod
    def cleanup_all() -> Dict[str, Any]:
        """
        Führt alle Cleanup-Operationen aus
        
        Returns:
            Dictionary mit Ergebnissen aller Cleanup-Operationen
        """
        try:
            results = {}
            
            # Benutzer bereinigen
            user_count, user_message = AdminUserService.cleanup_expired_users()
            results['users'] = {
                'deleted_count': user_count,
                'message': user_message
            }
            
            # Jobs bereinigen
            job_count, job_message = JobService.cleanup_expired_jobs()
            results['jobs'] = {
                'deleted_count': job_count,
                'message': job_message
            }
            
            # Gesamtstatistik
            total_deleted = user_count + job_count
            results['total'] = {
                'deleted_count': total_deleted,
                'message': f"Insgesamt {total_deleted} abgelaufene Einträge bereinigt"
            }
            
            logger.info(f"Cleanup abgeschlossen: {user_count} Benutzer, {job_count} Jobs gelöscht")
            return results
            
        except Exception as e:
            logger.error(f"Fehler beim Cleanup: {e}")
            return {
                'error': str(e),
                'users': {'deleted_count': 0, 'message': 'Fehler'},
                'jobs': {'deleted_count': 0, 'message': 'Fehler'},
                'total': {'deleted_count': 0, 'message': 'Fehler beim Cleanup'}
            }
    
    @staticmethod
    def get_expiry_warnings() -> Dict[str, Any]:
        """
        Gibt Warnungen für bald ablaufende Accounts und Jobs zurück
        
        Returns:
            Dictionary mit Warnungen
        """
        try:
            from app.models.mongodb_database import mongodb
            
            now = datetime.now()
            warnings = {
                'users': [],
                'jobs': [],
                'total_warnings': 0
            }
            
            # Benutzer die bald ablaufen (in den nächsten 7 Tagen)
            soon_expiring_users = list(mongodb.find('users', {
                'expires_at': {
                    '$exists': True,
                    '$ne': None,
                    '$gt': now,
                    '$lt': now + timedelta(days=7)
                }
            }))
            
            for user in soon_expiring_users:
                expiry_date = user['expires_at']
                if isinstance(expiry_date, str):
                    try:
                        expiry_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    except:
                        continue
                
                days_left = (expiry_date - now).days
                warnings['users'].append({
                    'id': str(user['_id']),
                    'username': user.get('username', 'Unknown'),
                    'role': user.get('role', 'Unknown'),
                    'expires_at': expiry_date.isoformat() if isinstance(expiry_date, datetime) else str(expiry_date),
                    'days_left': days_left
                })
            
            # Jobs die bald ablaufen (in den nächsten 7 Tagen)
            soon_expiring_jobs = list(mongodb.find('jobs', {
                'expires_at': {
                    '$exists': True,
                    '$ne': None,
                    '$gt': now,
                    '$lt': now + timedelta(days=7)
                }
            }))
            
            for job in soon_expiring_jobs:
                expiry_date = job['expires_at']
                if isinstance(expiry_date, str):
                    try:
                        expiry_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    except:
                        continue
                
                days_left = (expiry_date - now).days
                warnings['jobs'].append({
                    'id': str(job['_id']),
                    'title': job.get('title', 'Unknown'),
                    'company': job.get('company', 'Unknown'),
                    'expires_at': expiry_date.isoformat() if isinstance(expiry_date, datetime) else str(expiry_date),
                    'days_left': days_left
                })
            
            warnings['total_warnings'] = len(warnings['users']) + len(warnings['jobs'])
            
            return warnings
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Ablaufwarnungen: {e}")
            return {
                'users': [],
                'jobs': [],
                'total_warnings': 0,
                'error': str(e)
            }
    
    @staticmethod
    def get_expiry_statistics() -> Dict[str, Any]:
        """
        Gibt Statistiken zu ablaufenden Accounts und Jobs zurück
        
        Returns:
            Dictionary mit Statistiken
        """
        try:
            from app.models.mongodb_database import mongodb
            
            now = datetime.now()
            stats = {}
            
            # Benutzer-Statistiken
            total_users = mongodb.count_documents('users', {})
            expired_users = mongodb.count_documents('users', {
                'expires_at': {'$exists': True, '$ne': None, '$lt': now}
            })
            soon_expiring_users = mongodb.count_documents('users', {
                'expires_at': {
                    '$exists': True,
                    '$ne': None,
                    '$gt': now,
                    '$lt': now + timedelta(days=30)
                }
            })
            
            stats['users'] = {
                'total': total_users,
                'expired': expired_users,
                'soon_expiring': soon_expiring_users
            }
            
            # Job-Statistiken
            total_jobs = mongodb.count_documents('jobs', {'is_active': True})
            expired_jobs = mongodb.count_documents('jobs', {
                'expires_at': {'$exists': True, '$ne': None, '$lt': now}
            })
            soon_expiring_jobs = mongodb.count_documents('jobs', {
                'expires_at': {
                    '$exists': True,
                    '$ne': None,
                    '$gt': now,
                    '$lt': now + timedelta(days=30)
                }
            })
            
            stats['jobs'] = {
                'total': total_jobs,
                'expired': expired_jobs,
                'soon_expiring': soon_expiring_jobs
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Ablauf-Statistiken: {e}")
            return {
                'users': {'total': 0, 'expired': 0, 'soon_expiring': 0},
                'jobs': {'total': 0, 'expired': 0, 'soon_expiring': 0},
                'error': str(e)
            } 