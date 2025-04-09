from .database import BaseModel, Database

class Tool(BaseModel):
    TABLE_NAME = 'tools'

    @staticmethod
    def get_all_with_status():
        sql = '''
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
        return Database.query(sql)

    @staticmethod
    def get_lending_history(barcode):
        """Holt die Ausleihhistorie für ein Werkzeug"""
        sql = '''
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
        return Database.query(sql, [barcode])