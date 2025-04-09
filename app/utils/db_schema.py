class SchemaManager:
    def __init__(self, db):
        self.db = db

    def init_schema(self):
        """Initialisiert das Datenbankschema"""
        try:
            conn = self.db.get_db_connection()
            cursor = conn.cursor()
            
            # Access Settings Tabelle
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
            print("Zugriffseinstellungen initialisiert")
            
        except Exception as e:
            print(f"Fehler beim Initialisieren des Schemas: {e}")
            conn.rollback()
        finally:
            conn.close()
        
    def init_settings(self):
        """Initialisiert die Grundeinstellungen in der Datenbank"""
        default_settings = {
            'theme': 'light',
            'language': 'de',
            'items_per_page': '10',
            'primary_color': '259 94% 51%',    # Standard Blau
            'secondary_color': '314 100% 47%',  # Standard Pink
            'accent_color': '174 60% 51%'       # Standard Türkis
        }
        
        try:
            conn = self.db.get_db_connection()
            cursor = conn.cursor()
            
            for key, value in default_settings.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO settings (key, value)
                    VALUES (?, ?)
                """, (key, value))
            conn.commit()
            
        except Exception as e:
            print(f"Fehler beim Initialisieren der Einstellungen: {e}")
            conn.rollback()
        finally:
            conn.close()
        
    def reset_schema(self):
        """Löscht und erstellt das Schema neu"""
        try:
            conn = self.db.get_db_connection()
            cursor = conn.cursor()
            
            # Vorsicht: Dies löscht alle Daten!
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
            """)
            tables = cursor.fetchall()
            
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
            
            conn.commit()
            self.init_schema()
            
        except Exception as e:
            print(f"Fehler beim Zurücksetzen des Schemas: {e}")
            conn.rollback()
        finally:
            conn.close()
        
    def init_tables(self):
        """Initialisiert alle Tabellen"""
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ...
            )
        ''')
        
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS consumable_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consumable_id INTEGER NOT NULL,
                worker_barcode TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consumable_id) REFERENCES consumables(id),
                FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
            )
        ''')

    def init_users_table(self):
        """Initialisiert die Users-Tabelle"""
        with Database.get_db() as conn:
            cursor = conn.cursor()
            
            # Users-Tabelle erstellen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Standard Admin-Account erstellen
            admin_exists = cursor.execute(
                'SELECT 1 FROM users WHERE username = ?', 
                ['admin']
            ).fetchone()
            
            if not admin_exists:
                cursor.execute('''
                    INSERT INTO users (username, password, role)
                    VALUES (?, ?, ?)
                ''', [
                    'admin',
                    generate_password_hash('admin'),
                    'admin'
                ])
            
            conn.commit()