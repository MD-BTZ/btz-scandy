from .database import BaseModel, Database

class Worker(BaseModel):
    TABLE_NAME = 'workers'

    @staticmethod
    def get_all_with_lendings():
        sql = '''
        SELECT w.*, 
               COUNT(CASE WHEN l.returned_at IS NULL THEN 1 END) as active_lendings
        FROM workers w
        LEFT JOIN lendings l ON w.barcode = l.worker_barcode
        WHERE w.deleted = 0
        GROUP BY w.id
        ORDER BY w.lastname, w.firstname
        '''
        return Database.query(sql)