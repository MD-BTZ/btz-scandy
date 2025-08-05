"""
Kantinenplan Routes für Scandy
Verwaltet Mahlzeiten und API-Zugriff
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import admin_required, mitarbeiter_required
from app.services.canteen_service import CanteenService
from app.models.mongodb_database import is_feature_enabled
from app.config.config import config
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

bp = Blueprint('canteen', __name__)

@bp.route('/canteen')
@login_required
def index():
    """Hauptseite für Kantinenplan"""
    if not is_feature_enabled('canteen_plan'):
        flash('Kantinenplan-Feature ist nicht aktiviert', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Prüfe Benutzerberechtigung
    if not hasattr(current_user, 'canteen_plan_enabled') or not current_user.canteen_plan_enabled:
        flash('Sie haben keine Berechtigung für den Kantinenplan', 'error')
        return redirect(url_for('dashboard.index'))
    
    try:
        service = CanteenService()
        meals = service.get_current_week_meals()
        credentials_status = service.get_credentials_status()
        
        meals = service.get_two_weeks_meals()  # Hole 2 Wochen Daten
        return render_template('canteen/index.html', 
                             meals=meals, 
                             credentials_status=credentials_status)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Kantinenplan-Seite: {e}")
        flash('Fehler beim Laden der Daten', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/canteen/update', methods=['POST'])
@login_required
def update_canteen_plan():
    """Aktualisiert den Kantinenplan (2 Wochen)"""
    if not current_user.canteen_plan_enabled:
        flash('Keine Berechtigung für Kantinenplan-Eingabe', 'error')
        return redirect(url_for('canteen.index'))
    
    try:
        service = CanteenService()
        
        # Sammle Daten für 2 Wochen (10 Tage)
        meals_data = []
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()  # Neues Dessert-Feld
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert  # Neues Dessert-Feld
                })
        
        # Speichere in Datenbank
        success, message = service.save_meals(meals_data)
        
        if success:
            flash('Kantinenplan erfolgreich aktualisiert!', 'success')
        else:
            flash(f'Fehler beim Speichern: {message}', 'error')
        
        return redirect(url_for('canteen.index'))
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Kantinenplans: {e}")
        flash(f'Fehler beim Speichern: {str(e)}', 'error')
        return redirect(url_for('canteen.index'))

@bp.route('/admin/canteen_status')
@admin_required
def canteen_status():
    """Gibt Status der Kantinenplan-Konfiguration zurück"""
    if not is_feature_enabled('canteen_plan'):
        return jsonify({'enabled': False})
    
    try:
        service = CanteenService()
        
        return jsonify({
            'enabled': True,
            'api_configured': True,
            'message': 'API-basierte Kantinenplan-Verwaltung aktiv'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Kantinenplan-Status: {e}")
        return jsonify({'enabled': True, 'error': str(e)})

@bp.route('/api/canteen/current_week', methods=['GET'])
def api_current_week():
    """API-Endpunkt für aktuelle Woche (WordPress-kompatibel)"""
    try:
        # Optional API Key Check
        api_key = request.args.get('api_key')
        if config.get('CANTEEN_API_KEY') and api_key != config.get('CANTEEN_API_KEY'):
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        service = CanteenService()
        meals = service.get_current_week_meals()
        
        # Formatiere für WordPress-Kompatibilität
        week_data = []
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
        
        for i, meal in enumerate(meals):
            date = meal.get('date', '')
            meat_dish = meal.get('meat_dish', '').strip()
            vegan_dish = meal.get('vegan_dish', '').strip()
            dessert = meal.get('dessert', '').strip()  # Neues Dessert-Feld
            
            # Formatiere Datum für WordPress (z.B. "Montag, 15.01.2024")
            if date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    formatted_date = f"{weekdays[i % 5]}, {date_obj.strftime('%d.%m.%Y')}"
                except:
                    formatted_date = f"{weekdays[i % 5]}, {date}"
            else:
                # Fallback: Verwende aktuelles Datum für diese Woche
                today = datetime.now()
                monday = today - timedelta(days=today.weekday())
                target_date = monday + timedelta(days=i)
                formatted_date = f"{weekdays[i % 5]}, {target_date.strftime('%d.%m.%Y')}"
            
            week_data.append({
                'date': formatted_date,
                'meat_dish': meat_dish,
                'vegan_dish': vegan_dish,
                'dessert': dessert,  # Neues Dessert-Feld
                'weekday': weekdays[i % 5]
            })
        
        return jsonify({
            'success': True,
            'week': week_data,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API-Fehler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/canteen/two_weeks', methods=['GET'])
def api_two_weeks():
    """API-Endpunkt für 2 Wochen (WordPress-kompatibel)"""
    try:
        # Optional API Key Check
        api_key = request.args.get('api_key')
        if config.get('CANTEEN_API_KEY') and api_key != config.get('CANTEEN_API_KEY'):
            return jsonify({'success': False, 'error': 'Invalid API key'}), 401
        
        service = CanteenService()
        meals = service.get_two_weeks_meals()
        
        # Formatiere für WordPress-Kompatibilität
        two_weeks_data = []
        weekdays = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag']
        
        for i, meal in enumerate(meals):
            date = meal.get('date', '')
            meat_dish = meal.get('meat_dish', '').strip()
            vegan_dish = meal.get('vegan_dish', '').strip()
            dessert = meal.get('dessert', '').strip()  # Neues Dessert-Feld
            
            # Formatiere Datum für WordPress (z.B. "Montag, 15.01.2024")
            if date:
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    formatted_date = f"{weekdays[i % 5]}, {date_obj.strftime('%d.%m.%Y')}"
                except:
                    formatted_date = f"{weekdays[i % 5]}, {date}"
            else:
                # Fallback: Verwende aktuelles Datum für diese Woche
                today = datetime.now()
                monday = today - timedelta(days=today.weekday())
                target_date = monday + timedelta(days=i)
                formatted_date = f"{weekdays[i % 5]}, {target_date.strftime('%d.%m.%Y')}"
            
            two_weeks_data.append({
                'date': formatted_date,
                'meat_dish': meat_dish,
                'vegan_dish': vegan_dish,
                'dessert': dessert,  # Neues Dessert-Feld
                'weekday': weekdays[i % 5]
            })
        
        return jsonify({
            'success': True,
            'two_weeks': two_weeks_data,
            'generated_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"API-Fehler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/canteen/status', methods=['GET'])
def api_status():
    """API-Endpoint für Status-Informationen"""
    try:
        service = CanteenService()
        status = service.get_credentials_status()
        
        return jsonify({
            'success': True,
            'feature_enabled': is_feature_enabled('canteen_plan'),
            'sftp_configured': status.get('configured', False),
            'last_update': status.get('last_update'),
            'server_info': {
                'host': status.get('host'),
                'path': status.get('path')
            }
        })
        
    except Exception as e:
        logger.error(f"Status-API-Fehler: {e}")
        return jsonify({'error': 'Interner Server-Fehler'}), 500

@bp.route('/canteen/debug', methods=['GET'])
def debug_canteen():
    """Debug-Route für Kantinenplan-Probleme"""
    try:
        from app.models.mongodb_database import mongodb
        
        # Prüfe Datenbank-Verbindung
        db_status = "OK"
        try:
            mongodb.find_one('users', {})
        except Exception as e:
            db_status = f"Fehler: {e}"
        
        # Prüfe Feature-Status
        feature_enabled = is_feature_enabled('canteen_plan')
        
        # Prüfe Benutzer-Status
        user_status = "Nicht eingeloggt"
        if current_user.is_authenticated:
            user_status = f"Eingeloggt: {current_user.username} (Role: {current_user.role})"
            if hasattr(current_user, 'canteen_plan_enabled'):
                user_status += f", Canteen enabled: {current_user.canteen_plan_enabled}"
        
        return jsonify({
            'database_status': db_status,
            'feature_enabled': feature_enabled,
            'user_status': user_status,
            'current_user_id': str(current_user.get_id()) if current_user.is_authenticated else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/canteen/test_save', methods=['POST'])
def test_save():
    """Test-Route für Kantinenplan-Speicherung (ohne Authentifizierung)"""
    try:
        from app.models.mongodb_database import mongodb
        
        # Test-Daten
        test_meal = {
            'date': '2025-08-04',
            'meat_dish': 'Test Schnitzel',
            'vegan_dish': 'Test Vegan',
            'dessert': 'Test Dessert',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Speichere Test-Daten
        result = mongodb.insert_one('canteen_meals', test_meal)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Test-Daten erfolgreich gespeichert',
                'id': str(result)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Fehler beim Speichern'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/canteen/temp_save', methods=['POST'])
def temp_save():
    """Temporäre Route für Kantinenplan-Speicherung (ohne Authentifizierung)"""
    try:
        service = CanteenService()
        
        # Sammle Daten für 2 Wochen (10 Tage)
        meals_data = []
        for i in range(10):  # 2 Wochen = 10 Tage
            date = request.form.get(f'date_{i}')
            meat_dish = request.form.get(f'meat_dish_{i}', '').strip()
            vegan_dish = request.form.get(f'vegan_dish_{i}', '').strip()
            dessert = request.form.get(f'dessert_{i}', '').strip()  # Neues Dessert-Feld
            
            if date:
                meals_data.append({
                    'date': date,
                    'meat_dish': meat_dish,
                    'vegan_dish': vegan_dish,
                    'dessert': dessert  # Neues Dessert-Feld
                })
        
        # Speichere in Datenbank
        success, message = service.save_meals(meals_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Kantinenplan erfolgreich aktualisiert!'
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Kantinenplans: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/canteen/test_week', methods=['GET'])
def test_week():
    """Test-Route für Kalenderwoche-Berechnung"""
    try:
        from datetime import datetime
        
        # Teste Kalenderwoche-Berechnung
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        
        test_dates = []
        for week in range(2):
            for day in range(5):
                date = monday + timedelta(days=(week * 7) + day)
                calendar_week = date.isocalendar()[1]
                test_dates.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'calendar_week': calendar_week,
                    'weekday': ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag'][day]
                })
        
        return jsonify({
            'success': True,
            'test_dates': test_dates,
            'current_week': today.isocalendar()[1]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500