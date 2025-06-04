import logging
import os
import sys

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.utils.auto_migrate import auto_migrate_and_check

logging.basicConfig(level=logging.INFO)
auto_migrate_and_check("app/database/tickets.db") 