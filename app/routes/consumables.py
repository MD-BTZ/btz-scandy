from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, abort
from flask_login import current_user
from ..models.database import Database
from ..utils.decorators import login_required, admin_required, mitarbeiter_required
from datetime import datetime
import logging # Import logging

bp = Blueprint('consumables', __name__, url_prefix='/consumables')
logger = logging.getLogger(__name__) # Logger für dieses Modul

@bp.route('/')
@login_required
def index():
    """Zeigt alle aktiven Verbrauchsmaterialien"""
    logger.debug(f"[ROUTE] consumables.index: Entered route. User: {current_user.id}, Role: {current_user.role}")
    try:
        with Database.get_db() as conn:
            consumables = conn.execute('''
                SELECT c.*,
                       CASE 
                           WHEN c.quantity <= 0 THEN 'nicht_verfügbar'
                           WHEN c.quantity <= c.min_quantity THEN 'kritisch'
                           WHEN c.quantity <= c.min_quantity * 2 THEN 'niedrig'
                           ELSE 'verfügbar'
                       END as current_status
                FROM consumables c
                WHERE c.deleted = 0
                ORDER BY c.name
            ''').fetchall()
            
            categories = conn.execute('''
                SELECT DISTINCT category FROM consumables
                WHERE deleted = 0 AND category IS NOT NULL
                ORDER BY category
            ''').fetchall()
            
            locations = conn.execute('''
                SELECT DISTINCT location FROM consumables
                WHERE deleted = 0 AND location IS NOT NULL
                ORDER BY location
            ''').fetchall()
            
            logger.debug(f"[ROUTE] consumables.index: Preparing template. User is Admin: {current_user.is_admin}")
            
            return render_template('consumables/index.html',
                               consumables=consumables,
                               categories=[c['category'] for c in categories],
                               locations=[l['location'] for l in locations],
                               is_admin=current_user.is_admin)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Verbrauchsmaterialien: {str(e)}", exc_info=True)
        return render_template('consumables/index.html',
                           consumables=[],
                           categories=[],
                           locations=[],
                           is_admin=current_user.is_admin)

@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Fügt ein neues Verbrauchsmaterial hinzu (für alle eingeloggten Nutzer)"""
    logger.debug(f"[ROUTE] consumables.add: Entered route (Method: {request.method}). User: {current_user.id}")
    if request.method == 'POST':
        name = request.form.get('name')
        barcode = request.form.get('barcode')
        description = request.form.get('description')
        category = request.form.get('category')
        location = request.form.get('location')
        quantity = request.form.get('quantity', type=int)
        min_quantity = request.form.get('min_quantity', type=int)
        
        try:
            # Prüfe ob der Barcode bereits existiert
            exists_count = Database.query('''
                SELECT COUNT(*) as count FROM (
                    SELECT barcode FROM tools WHERE barcode = ? AND deleted = 0
                    UNION ALL 
                    SELECT barcode FROM consumables WHERE barcode = ? AND deleted = 0
                    UNION ALL
                    SELECT barcode FROM workers WHERE barcode = ? AND deleted = 0
                )
            ''', [barcode, barcode, barcode], one=True)['count']
            
            if exists_count > 0:
                flash('Dieser Barcode existiert bereits', 'error')
                # Hole Kategorien und Standorte für das Template
                categories = Database.query('''
                    SELECT name FROM categories 
                    WHERE deleted = 0 
                    ORDER BY name
                ''')
                
                locations = Database.query('''
                    SELECT name FROM locations 
                    WHERE deleted = 0 
                    ORDER BY name
                ''')
                
                # Gebe die Formulardaten zurück an das Template
                return render_template('consumables/add.html',
                                   categories=[c['name'] for c in categories],
                                   locations=[l['name'] for l in locations],
                                   form_data={
                                       'name': name,
                                       'barcode': barcode,
                                       'description': description,
                                       'category': category,
                                       'location': location,
                                       'quantity': quantity,
                                       'min_quantity': min_quantity
                                   })
            
            # Wenn Barcode eindeutig ist, füge das Verbrauchsmaterial hinzu
            Database.query('''
                INSERT INTO consumables 
                (name, barcode, description, category, location, quantity, min_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [name, barcode, description, category, location, quantity, min_quantity])
            
            flash('Verbrauchsmaterial erfolgreich hinzugefügt', 'success')
            return redirect(url_for('consumables.index'))
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Verbrauchsmaterials: {str(e)}", exc_info=True)
            flash('Fehler beim Hinzufügen des Verbrauchsmaterials', 'error')
            # Hole Kategorien und Standorte für das Template
            categories = Database.query('''
                SELECT name FROM categories 
                WHERE deleted = 0 
                ORDER BY name
            ''')
            
            locations = Database.query('''
                SELECT name FROM locations 
                WHERE deleted = 0 
                ORDER BY name
            ''')
            
            # Gebe die Formulardaten zurück an das Template
            return render_template('consumables/add.html',
                               categories=[c['name'] for c in categories],
                               locations=[l['name'] for l in locations],
                               form_data={
                                   'name': name,
                                   'barcode': barcode,
                                   'description': description,
                                   'category': category,
                                   'location': location,
                                   'quantity': quantity,
                                   'min_quantity': min_quantity
                               })
            
    else:
        # GET: Zeige Formular
        categories = Database.query('''
            SELECT name FROM categories 
            WHERE deleted = 0 
            ORDER BY name
        ''')
        
        locations = Database.query('''
            SELECT name FROM locations 
            WHERE deleted = 0 
            ORDER BY name
        ''')
        
        return render_template('consumables/add.html',
                           categories=[c['name'] for c in categories],
                           locations=[l['name'] for l in locations])

@bp.route('/<string:barcode>', methods=['GET', 'POST'])
@mitarbeiter_required
def detail(barcode):
    """Zeigt die Details eines Verbrauchsmaterials und verarbeitet Updates"""
    if request.method == 'POST':
        try:
            data = request.form
            new_barcode = data.get('barcode')  # Neuer Barcode aus dem Formular
            
            with Database.get_db() as conn:
                # Prüfe ob das Verbrauchsmaterial existiert
                current = conn.execute('''
                    SELECT * FROM consumables 
                    WHERE barcode = ? AND deleted = 0
                ''', [barcode]).fetchone()
                
                if not current:
                    return jsonify({
                        'success': False,
                        'message': 'Verbrauchsmaterial nicht gefunden'
                    }), 404
                
                # Prüfe ob der neue Barcode bereits existiert (wenn er sich geändert hat)
                if new_barcode != barcode:
                    exists_count = conn.execute("""
                        SELECT COUNT(*) as count FROM (
                            SELECT barcode FROM tools WHERE barcode = ? AND deleted = 0
                            UNION ALL 
                            SELECT barcode FROM consumables WHERE barcode = ? AND barcode != ? AND deleted = 0
                            UNION ALL
                            SELECT barcode FROM workers WHERE barcode = ? AND deleted = 0
                        )
                    """, [new_barcode, new_barcode, barcode, new_barcode]).fetchone()['count']
                    
                    if exists_count > 0:
                        return jsonify({
                            'success': False,
                            'message': f'Der Barcode "{new_barcode}" existiert bereits'
                        }), 400
                
                # Update durchführen
                conn.execute('''
                    UPDATE consumables 
                    SET name = ?,
                        description = ?,
                        category = ?,
                        location = ?,
                        quantity = ?,
                        min_quantity = ?,
                        barcode = ?,
                        sync_status = 'pending'
                    WHERE barcode = ?
                ''', [
                    data.get('name'),
                    data.get('description'),
                    data.get('category'),
                    data.get('location'),
                    int(data.get('quantity', current['quantity'])),
                    int(data.get('min_quantity', current['min_quantity'])),
                    new_barcode,
                    barcode
                ])
                
                # Bestandsänderung protokollieren
                if int(data.get('quantity', current['quantity'])) != current['quantity']:
                    conn.execute('''
                        INSERT INTO consumable_usages 
                        (consumable_barcode, worker_barcode, quantity, used_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ''', [new_barcode, 'admin', int(data.get('quantity', current['quantity'])) - current['quantity']])
                
                conn.commit()
                
            return jsonify({'success': True, 'redirect': url_for('consumables.detail', barcode=new_barcode)})
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Verbrauchsmaterials: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    # GET-Methode: Details anzeigen
    consumable = Database.query('''
        SELECT * FROM consumables WHERE barcode = ? AND deleted = 0
    ''', [barcode], one=True)
    
    if not consumable:
        flash('Verbrauchsmaterial nicht gefunden', 'error')
        return redirect(url_for('consumables.index'))
    
    # Hole vordefinierte Kategorien und Standorte aus den Einstellungen
    categories = Database.get_categories('consumables')
    locations = Database.get_locations()
    
    # Hole Bestandsänderungen
    history = Database.query('''
        SELECT 
            'Bestandsänderung' as action_type,
            strftime('%d.%m.%Y %H:%M', datetime(cu.used_at, 'localtime')) as action_date,
            CASE 
                WHEN cu.worker_barcode = 'admin' THEN 'Admin'
                ELSE w.firstname || ' ' || w.lastname 
            END as worker_name,
            CASE
                WHEN cu.worker_barcode = 'admin' THEN cu.quantity
                ELSE -ABS(cu.quantity)  -- Für Mitarbeiter immer negativ machen
            END as quantity
        FROM consumable_usages cu
        LEFT JOIN workers w ON cu.worker_barcode = w.barcode
        WHERE cu.consumable_barcode = ?
        ORDER BY cu.used_at DESC
    ''', [barcode])
    
    return render_template('consumables/details.html',
                         consumable=consumable,
                         categories=[c['name'] for c in categories],
                         locations=[l['name'] for l in locations],
                         history=history)

@bp.route('/<int:id>/update', methods=['POST'])
@mitarbeiter_required
def update(id):
    """Aktualisiert ein Verbrauchsmaterial"""
    try:
        data = request.form
        
        Database.query('''
            UPDATE consumables 
            SET name = ?,
                barcode = ?,
                category = ?,
                location = ?,
                description = ?,
                quantity = ?,
                min_quantity = ?
            WHERE id = ?
        ''', [
            data.get('name'),
            data.get('barcode'),
            data.get('category'),
            data.get('location'),
            data.get('description'),
            data.get('quantity', type=int),
            data.get('min_quantity', type=int),
            id
        ])
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Verbrauchsmaterials: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<int:id>/delete', methods=['POST'])
@mitarbeiter_required
def delete(id):
    """Löscht ein Verbrauchsmaterial (Soft Delete)"""
    try:
        Database.query('''
            UPDATE consumables 
            SET deleted = 1,
                deleted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', [id])
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/<barcode>/adjust-stock', methods=['POST'])
@login_required
def adjust_stock(barcode):
    """Passt den Bestand eines Verbrauchsmaterials an"""
    try:
        quantity = request.form.get('quantity', type=int)
        
        if quantity is None:
            return jsonify({'success': False, 'message': 'Menge muss angegeben werden'}), 400
            
        with Database.get_db() as conn:
            # Aktuellen Bestand abrufen
            current = conn.execute('''
                SELECT quantity FROM consumables 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode]).fetchone()
            
            if not current:
                return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404
            
            # Bestand aktualisieren (OHNE modified_at)
            conn.execute('''
                UPDATE consumables 
                SET quantity = ?
                WHERE barcode = ?
            ''', [quantity, barcode])
            
            # Änderung protokollieren
            conn.execute('''
                INSERT INTO consumable_usages 
                (consumable_barcode, worker_barcode, quantity, used_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', [barcode, 'admin', quantity - current['quantity']])
            
            conn.commit()
            
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Fehler bei der Bestandsanpassung: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/<barcode>')
@login_required
def view_consumable(barcode):
    try:
        consumable = Database.query('''
            SELECT * FROM consumables 
            WHERE barcode = ? AND deleted = 0
        ''', [barcode], one=True)
        
        if not consumable:
            flash('Verbrauchsmaterial nicht gefunden', 'error')
            return redirect(url_for('consumables.index'))
        
        # Hole Verbrauchshistorie
        history = Database.query('''
            SELECT
                'Bestandsänderung' as action_type,
                strftime('%d.%m.%Y %H:%M', cu.used_at) as action_date,
                CASE
                    WHEN cu.worker_barcode = 'admin' THEN 'Admin'
                    ELSE w.firstname || ' ' || w.lastname
                END as worker_name,
                CASE
                    WHEN cu.worker_barcode = 'admin' THEN cu.quantity
                    ELSE -cu.quantity  -- Für Mitarbeiter immer negativ machen
                END as quantity
            FROM consumable_usages cu
            LEFT JOIN workers w ON cu.worker_barcode = w.barcode
            WHERE cu.consumable_barcode = ?
            ORDER BY cu.used_at DESC
        ''', [barcode])
        
        # Berechne Gesamtverbrauch
        total_usage = sum(entry['quantity'] for entry in history)
        
        # Berechne aktuellen Bestand
        current_stock = consumable['quantity']
        
        return render_template('consumables/view.html',
                            consumable=consumable,
                            history=history,
                            total_usage=total_usage,
                            current_stock=current_stock)
        
    except Exception as e:
        flash(f'Fehler beim Laden des Verbrauchsmaterials: {str(e)}', 'error')
        return redirect(url_for('consumables.index'))

@bp.route('/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_by_barcode(barcode):
    """Löscht ein Verbrauchsmaterial anhand des Barcodes (Soft Delete)"""
    try:
        with Database.get_db() as conn:
            # Prüfe ob das Verbrauchsmaterial existiert
            consumable = conn.execute(
                'SELECT * FROM consumables WHERE barcode = ? AND deleted = 0',
                [barcode]
            ).fetchone()
            
            if not consumable:
                return jsonify({
                    'success': False, 
                    'message': 'Verbrauchsmaterial nicht gefunden'
                }), 404
            
            # In den Papierkorb verschieben (soft delete)
            conn.execute('''
                UPDATE consumables 
                SET deleted = 1,
                    deleted_at = datetime('now', 'localtime'),
                    modified_at = datetime('now', 'localtime')
                WHERE barcode = ?
            ''', [barcode])
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Verbrauchsmaterial wurde in den Papierkorb verschoben'
            })
            
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/<barcode>/forecast')
@login_required
def forecast(barcode):
    """Berechnet eine Bestandsprognose für ein Verbrauchsmaterial"""
    try:
        with Database.get_db() as conn:
            # Hole das Verbrauchsmaterial
            consumable = conn.execute('''
                SELECT * FROM consumables 
                WHERE barcode = ? AND deleted = 0
            ''', [barcode]).fetchone()
            
            if not consumable:
                return jsonify({
                    'success': False,
                    'message': 'Verbrauchsmaterial nicht gefunden'
                }), 404
            
            # Berechne durchschnittlichen Verbrauch pro Tag
            usage_stats = conn.execute('''
                WITH daily_usage AS (
                    SELECT 
                        date(used_at) as usage_date,
                        SUM(CASE
                            WHEN worker_barcode = 'admin' THEN quantity
                            ELSE -ABS(quantity)
                        END) as daily_quantity
                    FROM consumable_usages
                    WHERE consumable_barcode = ?
                    GROUP BY date(used_at)
                )
                SELECT 
                    COUNT(DISTINCT usage_date) as days_with_usage,
                    AVG(CASE WHEN daily_quantity < 0 THEN ABS(daily_quantity) ELSE 0 END) as avg_daily_usage,
                    MAX(ABS(daily_quantity)) as max_daily_usage,
                    MIN(usage_date) as first_usage,
                    MAX(usage_date) as last_usage
                FROM daily_usage
            ''', [barcode]).fetchone()
            
            if not usage_stats['days_with_usage']:
                return jsonify({
                    'success': True,
                    'message': 'Keine Verbrauchsdaten verfügbar',
                    'data': {
                        'current_stock': consumable['quantity'],
                        'min_stock': consumable['min_quantity'],
                        'avg_daily_usage': 0,
                        'days_until_min': None,
                        'days_until_empty': None
                    }
                })
            
            avg_daily_usage = usage_stats['avg_daily_usage'] or 0
            current_stock = consumable['quantity']
            min_stock = consumable['min_quantity']
            
            # Berechne Tage bis Mindestbestand und bis leer
            days_until_min = None if avg_daily_usage == 0 else int((current_stock - min_stock) / avg_daily_usage)
            days_until_empty = None if avg_daily_usage == 0 else int(current_stock / avg_daily_usage)
            
            return jsonify({
                'success': True,
                'data': {
                    'current_stock': current_stock,
                    'min_stock': min_stock,
                    'avg_daily_usage': round(avg_daily_usage, 2),
                    'days_until_min': days_until_min,
                    'days_until_empty': days_until_empty,
                    'first_usage': usage_stats['first_usage'],
                    'last_usage': usage_stats['last_usage'],
                    'max_daily_usage': usage_stats['max_daily_usage']
                }
            })
            
    except Exception as e:
        logger.error(f"Fehler bei der Bestandsprognose: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Bestandsprognose: {str(e)}'
        }), 500