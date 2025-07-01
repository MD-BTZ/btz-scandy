"""
Automatisches Backup-System für Scandy
Führt 2 Backups pro Tag zu festen Zeiten aus
"""
import os
import time
import threading
import logging
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from app.utils.backup_manager import BackupManager

logger = logging.getLogger(__name__)

class AutoBackupScheduler:
    """Automatischer Backup-Scheduler"""
    
    def __init__(self):
        self.backup_manager = BackupManager()
        self.running = False
        self.thread = None
        
        # Standard-Backup-Zeiten (24h Format) - werden aus DB überschrieben
        self.backup_times = [
            dt_time(6, 0),   # 06:00 Uhr
            dt_time(18, 0)   # 18:00 Uhr
        ]
        
        # Backup-Log-Datei
        self.log_file = Path(__file__).parent.parent.parent / 'logs' / 'auto_backup.log'
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Lade konfigurierte Zeiten beim Start
        self._load_backup_times()
        
    def _load_backup_times(self):
        """Lädt die konfigurierten Backup-Zeiten aus der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Lade konfigurierte Backup-Zeiten
            backup_times_setting = mongodb.find_one('settings', {'key': 'auto_backup_times'})
            
            if backup_times_setting and backup_times_setting.get('value'):
                # Parse die Zeiten aus dem String-Format "06:00,18:00"
                time_strings = backup_times_setting['value'].split(',')
                self.backup_times = []
                
                for time_str in time_strings:
                    time_str = time_str.strip()
                    if ':' in time_str:
                        try:
                            hour, minute = map(int, time_str.split(':'))
                            if 0 <= hour <= 23 and 0 <= minute <= 59:
                                self.backup_times.append(dt_time(hour, minute))
                        except ValueError:
                            logger.warning(f"Ungültige Backup-Zeit: {time_str}")
                
                # Stelle sicher, dass mindestens eine Zeit vorhanden ist
                if not self.backup_times:
                    self.backup_times = [dt_time(6, 0), dt_time(18, 0)]
                    
                logger.info(f"Backup-Zeiten geladen: {[t.strftime('%H:%M') for t in self.backup_times]}")
            else:
                logger.info("Keine konfigurierten Backup-Zeiten gefunden, verwende Standard-Zeiten")
                
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Zeiten: {e}")
            # Verwende Standard-Zeiten bei Fehlern
            self.backup_times = [dt_time(6, 0), dt_time(18, 0)]
    
    def save_backup_times(self, times_list):
        """Speichert neue Backup-Zeiten in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Validiere und konvertiere Zeiten
            valid_times = []
            for time_str in times_list:
                time_str = time_str.strip()
                if ':' in time_str:
                    try:
                        hour, minute = map(int, time_str.split(':'))
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            valid_times.append(f"{hour:02d}:{minute:02d}")
                    except ValueError:
                        logger.warning(f"Ungültige Backup-Zeit übersprungen: {time_str}")
            
            if valid_times:
                # Speichere in Datenbank
                times_string = ','.join(valid_times)
                mongodb.update_one('settings', 
                                 {'key': 'auto_backup_times'}, 
                                 {'$set': {'value': times_string}}, 
                                 upsert=True)
                
                # Aktualisiere lokale Zeiten
                self.backup_times = [dt_time(int(t.split(':')[0]), int(t.split(':')[1])) for t in valid_times]
                
                logger.info(f"Backup-Zeiten aktualisiert: {valid_times}")
                return True, "Backup-Zeiten erfolgreich gespeichert"
            else:
                return False, "Keine gültigen Zeiten gefunden"
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Backup-Zeiten: {e}")
            return False, f"Fehler beim Speichern: {str(e)}"
    
    def get_backup_times(self):
        """Gibt die aktuellen Backup-Zeiten zurück"""
        return [t.strftime('%H:%M') for t in self.backup_times]
    
    def start(self):
        """Startet den automatischen Backup-Scheduler"""
        if self.running:
            logger.info("Auto-Backup-Scheduler läuft bereits")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        logger.info("Auto-Backup-Scheduler gestartet")
        self._log_backup_event("Auto-Backup-Scheduler gestartet")
        
    def stop(self):
        """Stoppt den automatischen Backup-Scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Auto-Backup-Scheduler gestoppt")
        self._log_backup_event("Auto-Backup-Scheduler gestoppt")
        
    def _scheduler_loop(self):
        """Hauptschleife des Schedulers"""
        while self.running:
            try:
                now = datetime.now()
                current_time = now.time()
                
                # Prüfe ob es Zeit für ein Backup ist
                for backup_time in self.backup_times:
                    if (current_time.hour == backup_time.hour and 
                        current_time.minute == backup_time.minute):
                        
                        self._create_scheduled_backup()
                        # Warte 1 Minute um doppelte Backups zu vermeiden
                        time.sleep(60)
                        break
                
                # Warte 30 Sekunden bis zur nächsten Prüfung
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Fehler im Auto-Backup-Scheduler: {e}")
                self._log_backup_event(f"FEHLER: {e}")
                time.sleep(60)  # Warte 1 Minute bei Fehlern
                
    def _create_scheduled_backup(self):
        """Erstellt ein geplantes Backup"""
        try:
            logger.info("Erstelle automatisches Backup...")
            self._log_backup_event("Starte automatisches Backup")
            
            # Backup erstellen
            backup_filename = self.backup_manager.create_backup()
            
            if backup_filename:
                logger.info(f"Automatisches Backup erfolgreich erstellt: {backup_filename}")
                self._log_backup_event(f"Backup erfolgreich: {backup_filename}")
                
                # Optional: E-Mail-Benachrichtigung
                self._send_backup_notification(backup_filename, success=True)
            else:
                logger.error("Automatisches Backup fehlgeschlagen")
                self._log_backup_event("Backup fehlgeschlagen")
                self._send_backup_notification(None, success=False)
                
        except Exception as e:
            logger.error(f"Fehler beim automatischen Backup: {e}")
            self._log_backup_event(f"Backup-Fehler: {e}")
            self._send_backup_notification(None, success=False)
            
    def _log_backup_event(self, message):
        """Loggt Backup-Ereignisse in eine separate Datei"""
        try:
            timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            log_entry = f"[{timestamp}] {message}\n"
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Fehler beim Loggen des Backup-Ereignisses: {e}")
            
    def _send_backup_notification(self, backup_filename, success=True):
        """Sendet E-Mail-Benachrichtigung über Backup-Status"""
        try:
            from app.utils.email_utils import send_backup_mail
            
            if success and backup_filename:
                # Backup-Pfad ermitteln
                backup_path = self.backup_manager.get_backup_path(backup_filename)
                
                # E-Mail an Admin senden
                admin_email = self._get_admin_email()
                if admin_email:
                    send_backup_mail(admin_email, str(backup_path))
                    logger.info(f"Backup-Benachrichtigung an {admin_email} gesendet")
                    
        except Exception as e:
            logger.error(f"Fehler beim Senden der Backup-Benachrichtigung: {e}")
            
    def _get_admin_email(self):
        """Ermittelt die Admin-E-Mail-Adresse aus den Einstellungen"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Suche nach Admin-Benutzer
            admin_user = mongodb.find_one('users', {'role': 'admin'})
            if admin_user and admin_user.get('email'):
                return admin_user['email']
                
            # Fallback: Suche nach erster E-Mail in Settings
            email_setting = mongodb.find_one('settings', {'key': 'admin_email'})
            if email_setting and email_setting.get('value'):
                return email_setting['value']
                
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln der Admin-E-Mail: {e}")
            return None
            
    def get_status(self):
        """Gibt den aktuellen Status des Schedulers zurück"""
        try:
            return {
                'running': self.running,
                'backup_times': [t.strftime('%H:%M') for t in self.backup_times],
                'next_backup': self._get_next_backup_time(),
                'log_file': str(self.log_file)
            }
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Auto-Backup-Status: {e}")
            return {
                'running': self.running,
                'backup_times': [t.strftime('%H:%M') for t in self.backup_times],
                'next_backup': 'Fehler beim Berechnen',
                'log_file': str(self.log_file)
            }
        
    def _get_next_backup_time(self):
        """Ermittelt die nächste Backup-Zeit"""
        now = datetime.now()
        current_time = now.time()
        
        for backup_time in self.backup_times:
            if current_time < backup_time:
                # Heute noch
                next_backup = datetime.combine(now.date(), backup_time)
                return next_backup.strftime('%d.%m.%Y %H:%M')
            else:
                # Morgen - verwende timedelta für sicheres Datum
                tomorrow = now.date() + timedelta(days=1)
                next_backup = datetime.combine(tomorrow, backup_time)
                return next_backup.strftime('%d.%m.%Y %H:%M')
                
        return "Unbekannt"

# Globale Instanz
auto_backup_scheduler = AutoBackupScheduler()

def start_auto_backup():
    """Startet das automatische Backup-System"""
    auto_backup_scheduler.start()

def stop_auto_backup():
    """Stoppt das automatische Backup-System"""
    auto_backup_scheduler.stop()

def get_auto_backup_status():
    """Gibt den Status des automatischen Backup-Systems zurück"""
    return auto_backup_scheduler.get_status() 