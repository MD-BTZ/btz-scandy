from .database import BaseModel, Database
from datetime import datetime

def get_consumables():
    """Holt alle aktiven Verbrauchsmaterialien aus der Datenbank"""
    results = Database.query('''
        SELECT c.*, 
               c.quantity as current_stock,
               CASE 
                   WHEN c.quantity = 0 THEN 'Leer'
                   WHEN c.quantity <= c.min_quantity * 0.5 THEN 'Kritisch'
                   WHEN c.quantity <= c.min_quantity THEN 'Nachbestellen'
                   ELSE 'Verfügbar'
               END as stock_status
        FROM consumables c
        WHERE c.deleted = 0
        ORDER BY c.name
    ''')
    return [dict(row) for row in results] if results else []

class Consumable(BaseModel):
    TABLE_NAME = 'consumables'

    @staticmethod
    def get_all():
        sql = '''
        SELECT 
            c.*,
            CASE 
                WHEN c.quantity <= c.min_quantity THEN 'Nachbestellen'
                ELSE 'OK'
            END as stock_status
        FROM consumables c
        WHERE c.deleted = 0
        ORDER BY c.name
        '''
        return Database.query(sql)

    @staticmethod
    def get_by_barcode(barcode):
        sql = '''
        SELECT 
            c.*,
            CASE 
                WHEN c.quantity <= c.min_quantity THEN 'Nachbestellen'
                ELSE 'OK'
            END as stock_status
        FROM consumables c
        WHERE c.barcode = ? 
        AND c.deleted = 0
        '''
        with Database.get_db() as conn:
            result = conn.execute(sql, [barcode]).fetchone()
            return result

    def __init__(self, data):
        self.id = data.get('id')