from flask import Blueprint, render_template, g
from app.models.database import Database
from app.utils.decorators import login_required

bp = Blueprint('index', __name__)

@bp.route('/')
def index():
    """Startseite anzeigen"""
    
    # Werkzeug-Statistiken mit verbesserter Abfrage
    tool_stats = Database.query('''
        WITH valid_tools AS (
            SELECT barcode 
            FROM tools 
            WHERE deleted = 0
        )
        SELECT 
            COUNT(*) as total,
            SUM(CASE 
                WHEN NOT EXISTS (
                    SELECT 1 FROM lendings l 
                    WHERE l.tool_barcode = t.barcode 
                    AND l.returned_at IS NULL
                ) AND status = 'verfügbar' THEN 1 
                ELSE 0 
            END) as available,
            (
                SELECT COUNT(DISTINCT l.tool_barcode) 
                FROM lendings l
                JOIN valid_tools vt ON l.tool_barcode = vt.barcode
                WHERE l.returned_at IS NULL
            ) as lent,
            SUM(CASE WHEN status = 'defekt' THEN 1 ELSE 0 END) as defect
        FROM tools t
        WHERE t.deleted = 0
    ''', one=True)
    
    # Debug-Ausgabe
    print("Tool Stats:", tool_stats)
    
    # Verbrauchsmaterial-Statistiken
    consumable_stats = Database.query('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN quantity > min_quantity THEN 1 ELSE 0 END) as sufficient,
            SUM(CASE WHEN quantity <= min_quantity AND quantity > min_quantity * 0.5 THEN 1 ELSE 0 END) as warning,
            SUM(CASE WHEN quantity <= min_quantity * 0.5 THEN 1 ELSE 0 END) as critical
        FROM consumables
        WHERE deleted = 0
    ''', one=True)
    
    # Mitarbeiter-Statistiken
    worker_stats = {
        'total': Database.query('SELECT COUNT(*) as count FROM workers WHERE deleted = 0', one=True)['count'],
        'by_department': Database.query('''
            SELECT department as name, COUNT(*) as count 
            FROM workers 
            WHERE deleted = 0 AND department IS NOT NULL
            GROUP BY department
            ORDER BY count DESC
        ''')
    }
    
    return render_template('index.html',
                         tool_stats=tool_stats,
                         consumable_stats=consumable_stats,
                         worker_stats=worker_stats) 