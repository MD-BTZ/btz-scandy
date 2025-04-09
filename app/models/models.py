from app.models.database import Database

class Tool:
    @staticmethod
    def count_active():
        """Zählt alle aktiven (nicht gelöschten) Werkzeuge"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM tools WHERE deleted = 0')
            return cursor.fetchone()[0]
    
    @staticmethod
    def count_by_status(status):
        """Zählt Werkzeuge nach Status"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            # Status-Mapping für Konsistenz
            status_map = {
                'verfügbar': ['verfügbar', 'available', 'Verfügbar'],
                'verliehen': ['verliehen', 'borrowed', 'Verliehen'],
                'defekt': ['defekt', 'broken', 'Defekt']
            }
            
            # SQL mit CASE für verschiedene Status-Schreibweisen
            sql = '''
                SELECT COUNT(*) FROM tools 
                WHERE deleted = 0 AND LOWER(status) IN (
            '''
            status_values = status_map.get(status.lower(), [status.lower()])
            placeholders = ','.join(['?' for _ in status_values])
            sql += placeholders + ')'
            
            cursor.execute(sql, status_values)
            return cursor.fetchone()[0]

class Consumable:
    @staticmethod
    def count_active():
        """Zählt alle aktiven (nicht gelöschten) Verbrauchsmaterialien"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM consumables WHERE deleted = 0')
            return cursor.fetchone()[0]
    
    @staticmethod
    def count_by_stock_status(status):
        """Zählt Verbrauchsmaterialien nach Bestandsstatus"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            if status == 'sufficient':
                sql = '''
                    SELECT COUNT(*) FROM consumables 
                    WHERE deleted = 0 AND quantity > min_quantity
                '''
            elif status == 'low':
                sql = '''
                    SELECT COUNT(*) FROM consumables 
                    WHERE deleted = 0 
                    AND quantity <= min_quantity 
                    AND quantity > 0
                '''
            else:  # empty
                sql = '''
                    SELECT COUNT(*) FROM consumables 
                    WHERE deleted = 0 AND quantity = 0
                '''
            cursor.execute(sql)
            return cursor.fetchone()[0]

class Worker:
    @staticmethod
    def count_active():
        """Zählt alle aktiven (nicht gelöschten) Mitarbeiter"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM workers WHERE deleted = 0')
            return cursor.fetchone()[0]
    
    @staticmethod
    def count_by_department():
        """Gruppiert Mitarbeiter nach Abteilung"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COALESCE(department, 'Keine Abteilung') as name,
                    COUNT(*) as count
                FROM workers 
                WHERE deleted = 0 
                GROUP BY department
                ORDER BY 
                    CASE WHEN department IS NULL THEN 1 ELSE 0 END,
                    department
            ''')
            return [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()] 