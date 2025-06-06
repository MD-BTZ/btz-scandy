from typing import List, Dict, Any, Optional
from .base_model import BaseModel


class Worker(BaseModel):
    """Model for workers in the inventory system."""
    
    TABLE_NAME = 'workers'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    @classmethod
    def get_all_with_lendings(cls) -> List[Dict[str, Any]]:
        """Get all workers with their active lendings count."""
        query = '''
        SELECT w.*, 
               COUNT(CASE WHEN l.returned_at IS NULL THEN 1 END) as active_lendings
        FROM workers w
        LEFT JOIN lendings l ON w.barcode = l.worker_barcode
        WHERE w.deleted = 0
        GROUP BY w.id
        ORDER BY w.lastname, w.firstname
        '''
        return cls.query_all(query)
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional['Worker']:
        """Get a worker by their barcode."""
        query = 'SELECT * FROM workers WHERE barcode = ? AND deleted = 0'
        result = cls.query_one(query, (barcode,))
        return cls(**result) if result else None
    
    @classmethod
    def get_active_tools(cls, worker_barcode: str) -> List[Dict[str, Any]]:
        """Get all tools currently lent to a worker."""
        query = '''
        SELECT t.*, 
               strftime('%d.%m.%Y %H:%M', l.lent_at, 'localtime') as lent_at_formatted,
               l.lent_at as raw_lent_at
        FROM tools t
        JOIN lendings l ON t.barcode = l.tool_barcode
        WHERE l.worker_barcode = ? 
        AND l.returned_at IS NULL
        AND t.deleted = 0
        ORDER BY l.lent_at DESC
        '''
        return cls.query_all(query, (worker_barcode,))