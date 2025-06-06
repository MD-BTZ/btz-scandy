from typing import List, Dict, Any, Optional
from .base_model import BaseModel


class Tool(BaseModel):
    """Model for tools in the inventory system."""
    
    TABLE_NAME = 'tools'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    @classmethod
    def get_all_with_status(cls) -> List[Dict[str, Any]]:
        """Get all tools with their current status and lending information."""
        query = '''
        SELECT t.*, 
               l.worker_barcode,
               strftime('%d.%m.%Y %H:%M', l.lent_at, 'localtime') as formatted_lent_at,
               strftime('%d.%m.%Y %H:%M', l.returned_at, 'localtime') as formatted_returned_at,
               w.firstname || ' ' || w.lastname as current_borrower,
               t.location,
               t.category
        FROM tools t
        LEFT JOIN (
            SELECT tool_barcode, worker_barcode, lent_at, returned_at
            FROM lendings l1
            WHERE NOT EXISTS (
                SELECT 1 FROM lendings l2
                WHERE l2.tool_barcode = l1.tool_barcode
                AND l2.lent_at > l1.lent_at
            )
            AND returned_at IS NULL
        ) l ON t.barcode = l.tool_barcode
        LEFT JOIN workers w ON l.worker_barcode = w.barcode
        WHERE t.deleted = 0
        ORDER BY t.name
        '''
        return cls.query_all(query)
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional['Tool']:
        """Get a tool by its barcode."""
        query = 'SELECT * FROM tools WHERE barcode = ? AND deleted = 0'
        result = cls.query_one(query, (barcode,))
        return cls(**result) if result else None
    
    @classmethod
    def get_lending_history(cls, barcode: str) -> List[Dict[str, Any]]:
        """Get the lending history for a tool."""
        query = '''
        WITH lending_history AS (
            SELECT 
                l.*,
                w.firstname || ' ' || w.lastname as worker_name,
                CASE
                    WHEN l.returned_at IS NULL THEN 'Ausgeliehen'
                    ELSE 'Zurückgegeben'
                END as action,
                'Ausleihe/Rückgabe' as action_type,
                strftime('%d.%m.%Y %H:%M', l.lent_at, 'localtime') as formatted_lent_at,
                strftime('%d.%m.%Y %H:%M', l.returned_at, 'localtime') as formatted_returned_at,
                l.lent_at as raw_lent_at,
                l.returned_at as raw_returned_at
            FROM lendings l
            LEFT JOIN workers w ON w.barcode = l.worker_barcode
            WHERE l.tool_barcode = ?
            ORDER BY 
                CASE 
                    WHEN l.returned_at IS NULL THEN l.lent_at
                    ELSE l.returned_at 
                END DESC
        )
        SELECT 
            action_type,
            CASE 
                WHEN action = 'Ausgeliehen' THEN formatted_lent_at
                ELSE formatted_returned_at
            END as action_date,
            worker_name as worker,
            action,
            NULL as reason,
            CASE 
                WHEN action = 'Ausgeliehen' THEN raw_lent_at
                ELSE raw_returned_at
            END as raw_date,
            formatted_lent_at as lent_at,
            formatted_returned_at as returned_at
        FROM lending_history
        '''
        return cls.query_all(query, (barcode,))