import requests
import subprocess
import logging
import os
from pathlib import Path
import json
from datetime import datetime
import docker
import shutil

logger = logging.getLogger(__name__)

class UpdateManager:
    def __init__(self, app_path):
        self.app_path = Path(app_path)
        self.github_api_url = "https://api.github.com/repos/woschj/scandy2/releases/latest"
        self.current_version = self._get_current_version()
        self.container_name = os.environ.get('CONTAINER_NAME', 'scandy')
        self.update_log_file = self.app_path / 'logs' / 'updates.log'
        
    def _log_update(self, message, level='info'):
        """Loggt Update-Aktionen in eine Datei"""
        self.update_log_file.parent.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        with open(self.update_log_file, 'a', encoding='utf-8') as f:
            f.write(log_message)
        
        if level == 'error':
            logger.error(message)
        else:
            logger.info(message)
    
    def _get_current_version(self):
        """Liest die aktuelle Version aus der Version-Datei"""
        try:
            from app.config.version import VERSION
            return VERSION
        except ImportError:
            logger.error("Konnte Version nicht lesen")
            return "0.0.0"
    
    def _get_docker_client(self):
        """Erstellt einen Docker-Client"""
        try:
            return docker.from_env()
        except Exception as e:
            self._log_update(f"Fehler beim Erstellen des Docker-Clients: {str(e)}", 'error')
            raise
    
    def _create_backup(self, container):
        """Erstellt ein Backup der Anwendung"""
        try:
            backup_dir = self.app_path / 'backups'
            backup_dir.mkdir(exist_ok=True)
            backup_file = backup_dir / f"pre_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            # Backup erstellen
            result = container.exec_run(
                f"zip -r /app/backups/{backup_file.name} /app -x '*/venv/*' '*/__pycache__/*' '*/node_modules/*'"
            )
            
            if result.exit_code != 0:
                raise Exception(f"Backup fehlgeschlagen: {result.output.decode()}")
            
            self._log_update(f"Backup erstellt: {backup_file.name}")
            return backup_file
            
        except Exception as e:
            self._log_update(f"Fehler beim Erstellen des Backups: {str(e)}", 'error')
            raise
    
    def _rollback(self, container, backup_file):
        """Führt ein Rollback durch"""
        try:
            self._log_update(f"Starte Rollback mit Backup: {backup_file.name}")
            
            # Entpacke Backup
            container.exec_run(f"unzip -o /app/backups/{backup_file.name} -d /")
            
            # Requirements neu installieren
            container.exec_run("cd /app && pip install -r requirements.txt")
            
            # Container neu starten
            container.restart()
            
            self._log_update("Rollback erfolgreich durchgeführt")
            return True
            
        except Exception as e:
            self._log_update(f"Fehler beim Rollback: {str(e)}", 'error')
            return False
    
    def check_for_updates(self):
        """Prüft auf GitHub nach Updates"""
        try:
            response = requests.get(self.github_api_url)
            if response.status_code == 200:
                latest_release = response.json()
                latest_version = latest_release['tag_name'].lstrip('v')
                
                if latest_version > self.current_version:
                    self._log_update(f"Update verfügbar: {self.current_version} -> {latest_version}")
                    return {
                        'update_available': True,
                        'current_version': self.current_version,
                        'latest_version': latest_version,
                        'release_notes': latest_release['body'],
                        'download_url': latest_release['zipball_url']
                    }
            
            return {
                'update_available': False,
                'current_version': self.current_version,
                'latest_version': self.current_version
            }
            
        except Exception as e:
            self._log_update(f"Fehler beim Prüfen auf Updates: {str(e)}", 'error')
            return {
                'update_available': False,
                'error': str(e)
            }
    
    def perform_update(self):
        """Führt das Update durch"""
        try:
            # Docker-Client erstellen
            docker_client = self._get_docker_client()
            container = docker_client.containers.get(self.container_name)
            
            # Backup erstellen
            backup_file = self._create_backup(container)
            
            try:
                # Repository aktualisieren
                self._log_update("Aktualisiere Repository...")
                container.exec_run("cd /app && git fetch --all")
                container.exec_run("cd /app && git reset --hard origin/main")
                
                # Requirements aktualisieren
                self._log_update("Aktualisiere Python-Abhängigkeiten...")
                container.exec_run("cd /app && pip install -r requirements.txt")
                
                # Neustart-Signal setzen
                container.exec_run("touch /app/tmp/needs_restart")
                
                # Container neu starten
                self._log_update("Starte Container neu...")
                container.restart()
                
                self._log_update("Update erfolgreich durchgeführt")
                return {
                    'success': True,
                    'message': 'Update erfolgreich durchgeführt',
                    'backup_file': str(backup_file)
                }
                
            except Exception as e:
                self._log_update(f"Fehler während des Updates: {str(e)}", 'error')
                # Rollback durchführen
                if self._rollback(container, backup_file):
                    return {
                        'success': False,
                        'error': str(e),
                        'message': 'Update fehlgeschlagen, Rollback durchgeführt'
                    }
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'message': 'Update und Rollback fehlgeschlagen!'
                    }
            
        except Exception as e:
            self._log_update(f"Kritischer Fehler beim Update: {str(e)}", 'error')
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_update_status(self):
        """Gibt den aktuellen Update-Status zurück"""
        try:
            docker_client = self._get_docker_client()
            container = docker_client.containers.get(self.container_name)
            
            # Prüfe ob Container läuft
            if container.status != 'running':
                return {
                    'status': 'error',
                    'message': 'Container läuft nicht'
                }
            
            # Prüfe ob Update-Signal existiert
            result = container.exec_run("test -f /app/tmp/needs_restart")
            needs_restart = result.exit_code == 0
            
            # Prüfe Container-Gesundheit
            health = container.attrs.get('State', {}).get('Health', {}).get('Status', 'unknown')
            
            return {
                'status': 'running',
                'needs_restart': needs_restart,
                'container_name': self.container_name,
                'current_version': self.current_version,
                'health': health
            }
            
        except Exception as e:
            self._log_update(f"Fehler beim Prüfen des Update-Status: {str(e)}", 'error')
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_update_history(self, limit=10):
        """Gibt die letzten Update-Logs zurück"""
        try:
            if not self.update_log_file.exists():
                return []
            
            with open(self.update_log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            
            return logs[-limit:]
            
        except Exception as e:
            self._log_update(f"Fehler beim Lesen der Update-Historie: {str(e)}", 'error')
            return [] 