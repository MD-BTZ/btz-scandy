from flask import Blueprint, render_template
from app.models.database import Database

bp = Blueprint('history', __name__)

@bp.route('/history')
def history():
    """Zeigt die Historie der Ausleihen an"""
    with Database.get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Hole die letzten 50 Ausleihen mit Details
        cursor.execute("""
            SELECT 
                l.id,
                l.lent_at,
                l.returned_at,
                t.name as tool_name,
                t.barcode as tool_barcode,
                w.firstname || ' ' || w.lastname as worker_name,
                w.barcode as worker_barcode
            FROM lendings l
            JOIN tools t ON l.tool_barcode = t.barcode
            JOIN workers w ON l.worker_barcode = w.barcode
            ORDER BY l.lent_at DESC
            LIMIT 50
        """)
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'id': row[0],
                'lent_at': row[1],
                'returned_at': row[2],
                'tool_name': row[3],
                'tool_barcode': row[4],
                'worker_name': row[5],
                'worker_barcode': row[6]
            })
            
    return render_template('history.html', history=history) 