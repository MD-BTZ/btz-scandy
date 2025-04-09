from datetime import datetime, timedelta
from app.models.database import Database
from app.models.init_db import init_users
from werkzeug.security import generate_password_hash

def load_demo_data():
    """Lädt Testdaten in die Datenbank"""
    with Database.get_db() as db:
        # Lösche existierende Daten außer users
        tables = ['settings', 'tools', 'consumables', 'workers', 'lendings', 'consumable_usages', 'tool_status_changes']
        for table in tables:
            db.execute(f"DELETE FROM {table}")
            
        # Rest der Demo-Daten-Ladung wie gehabt
        # ... existing code ... 