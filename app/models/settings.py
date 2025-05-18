from app.models.database import Database

class Settings:
    @staticmethod
    def init_access_settings():
        """Initialisiert die Zugriffseinstellungen in der Datenbank"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            
            # Tabelle für Zugriffseinstellungen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access_settings (
                    route TEXT PRIMARY KEY,
                    is_public BOOLEAN DEFAULT 0,
                    description TEXT
                )
            ''')
            
            # Standard-Einstellungen
            default_settings = [
                ('tools.index', 1, 'Werkzeug-Übersicht'),
                ('tools.details', 1, 'Werkzeug-Details'),
                ('consumables.index', 1, 'Verbrauchsmaterial-Übersicht'),
                ('consumables.details', 1, 'Verbrauchsmaterial-Details'),
                ('workers.index', 0, 'Mitarbeiter-Übersicht'),
                ('workers.details', 0, 'Mitarbeiter-Details'),
                ('admin.dashboard', 0, 'Admin-Dashboard'),
                ('admin.trash', 0, 'Papierkorb'),
                ('history.view', 0, 'Verlauf')
            ]
            
            # Füge Standardeinstellungen ein
            cursor.executemany('''
                INSERT OR IGNORE INTO access_settings (route, is_public, description)
                VALUES (?, ?, ?)
            ''', default_settings)
            
            conn.commit()

    @staticmethod
    def get_public_routes():
        """Holt alle als öffentlich markierten Routen"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT route FROM access_settings WHERE is_public = 1')
            return [row['route'] for row in cursor.fetchall()]

    @staticmethod
    def update_route_access(route, is_public):
        """Aktualisiert den Zugriffsstatus einer Route"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE access_settings 
                SET is_public = ? 
                WHERE route = ?
            ''', [is_public, route])
            conn.commit()

    @staticmethod
    def get_all_settings():
        """Holt alle Zugriffseinstellungen"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT route, is_public, description 
                FROM access_settings 
                ORDER BY description
            ''')
            return cursor.fetchall() 