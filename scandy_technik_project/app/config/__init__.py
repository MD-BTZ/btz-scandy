"""
Konfigurationspaket für Scandy
"""
from .config import config, Config
from .version import VERSION

__all__ = ['config', 'Config', 'VERSION']

# Importiere die Basis-Config-Klasse
from .config import Config as BaseConfig

class Config(BaseConfig):
    """Erweiterte Konfigurationsklasse"""
    @staticmethod
    def init_server():
        pass

    @staticmethod
    def init_client(server_url=None):
        pass

    @staticmethod
    def is_pythonanywhere():
        # This is a placeholder implementation. You might want to implement a more robust check for PythonAnywhere
        return False 