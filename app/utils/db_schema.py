import sqlite3

class SchemaManager:
    def __init__(self, db):
        self.db = db
        self.current_version = 4  # Aktuelle Schema-Version
        self.schema_version_table = 'schema_version'

    def init_schema(self):
        """Initialisiert das Datenbankschema"""
        try:
            conn = self.db.get_db_connection()
            cursor = conn.cursor()
            
            # Schema-Versionstabelle erstellen
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.schema_version_table} (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Aktuelle Version prüfen
            cursor.execute(f'SELECT version FROM {self.schema_version_table} ORDER BY version DESC LIMIT 1')
            current_version = cursor.fetchone()
            
            if not current_version:
                # Erste Version einfügen
                cursor.execute(f'INSERT INTO {self.schema_version_table} (version) VALUES (?)', (self.current_version,))
                self._create_initial_schema(cursor)
            elif current_version[0] < self.current_version:
                # Schema-Updates durchführen
                self._update_schema(cursor, current_version[0])
            
            conn.commit()
            print(f"Datenbankschema auf Version {self.current_version} aktualisiert")
            
        except Exception as e:
            print(f"Fehler beim Initialisieren des Schemas: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_initial_schema(self, cursor):
        """Erstellt das initiale Datenbankschema"""
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
        
        cursor.executemany('''
            INSERT OR IGNORE INTO access_settings (route, is_public, description)
            VALUES (?, ?, ?)
        ''', default_settings)

        # Tools Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                category TEXT,
                location TEXT,
                status TEXT DEFAULT 'available',
                last_maintenance DATE,
                next_maintenance DATE,
                notes TEXT,
                deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Consumables Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consumables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                category TEXT,
                location TEXT,
                quantity INTEGER DEFAULT 0,
                min_quantity INTEGER DEFAULT 0,
                unit TEXT,
                notes TEXT,
                deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Workers Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                department TEXT,
                email TEXT,
                phone TEXT,
                notes TEXT,
                deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Lendings Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lendings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_id INTEGER NOT NULL,
                worker_barcode TEXT NOT NULL,
                lent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                returned_at TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (tool_id) REFERENCES tools(id),
                FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
            )
        ''')

        # Consumable Usage Tabelle
        cursor.execute('''
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

        # Settings Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Users Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

    def _update_schema(self, cursor, from_version):
        """Führt Schema-Updates durch"""
        def insert_version_if_not_exists(version):
            cursor.execute(f'SELECT 1 FROM {self.schema_version_table} WHERE version = ?', [version])
            if not cursor.fetchone():
                cursor.execute(f'INSERT INTO {self.schema_version_table} (version) VALUES (?)', [version])

        if from_version < 2:
            # Update auf Version 2
            try:
                cursor.execute('ALTER TABLE tools ADD COLUMN maintenance_interval INTEGER')
                cursor.execute('ALTER TABLE tools ADD COLUMN last_checked TIMESTAMP')
            except sqlite3.OperationalError as e:
                if 'duplicate column name' not in str(e):
                    raise
            insert_version_if_not_exists(2)

        if from_version < 3:
            # Update auf Version 3
            try:
                cursor.execute('ALTER TABLE consumables ADD COLUMN supplier TEXT')
                cursor.execute('ALTER TABLE consumables ADD COLUMN reorder_point INTEGER')
            except sqlite3.OperationalError as e:
                if 'duplicate column name' not in str(e):
                    raise
            insert_version_if_not_exists(3)

        if from_version < 4:
            # Update auf Version 4 - Papierkorb-Funktionalität
            try:
                cursor.execute('ALTER TABLE tools ADD COLUMN deleted BOOLEAN DEFAULT 0')
                cursor.execute('ALTER TABLE tools ADD COLUMN deleted_at TIMESTAMP')
                cursor.execute('ALTER TABLE consumables ADD COLUMN deleted BOOLEAN DEFAULT 0')
                cursor.execute('ALTER TABLE consumables ADD COLUMN deleted_at TIMESTAMP')
                cursor.execute('ALTER TABLE workers ADD COLUMN deleted BOOLEAN DEFAULT 0')
                cursor.execute('ALTER TABLE workers ADD COLUMN deleted_at TIMESTAMP')
            except sqlite3.OperationalError as e:
                if 'duplicate column name' not in str(e):
                    raise
            insert_version_if_not_exists(4)

        # Weitere Versionen hier hinzufügen...

    def validate_schema(self):
        """Validiert das aktuelle Schema"""
        try:
            conn = self.db.get_db_connection()
            cursor = conn.cursor()
            
            # Prüfe ob alle erforderlichen Tabellen existieren
            required_tables = [
                'tools', 'consumables', 'workers', 'lendings',
                'consumable_usage', 'settings', 'users', 'access_settings'
            ]
            
            for table in required_tables:
                cursor.execute(f'''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                ''', (table,))
                if not cursor.fetchone():
                    raise Exception(f"Fehlende Tabelle: {table}")
            
            # Prüfe ob die Schema-Versionstabelle existiert
            cursor.execute(f'''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            ''', (self.schema_version_table,))
            if not cursor.fetchone():
                raise Exception("Schema-Versionstabelle fehlt")
            
            # Prüfe die aktuelle Version
            cursor.execute(f'SELECT version FROM {self.schema_version_table} ORDER BY version DESC LIMIT 1')
            version = cursor.fetchone()
            if not version or version[0] != self.current_version:
                raise Exception(f"Falsche Schema-Version: {version[0] if version else 'keine'} (erwartet: {self.current_version})")
            
            return True
            
        except Exception as e:
            print(f"Schema-Validierung fehlgeschlagen: {e}")
            return False
        finally:
            conn.close()

    def get_schema_version(self):
        """Gibt die aktuelle Schema-Version zurück"""
        try:
            conn = self.db.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(f'SELECT version FROM {self.schema_version_table} ORDER BY version DESC LIMIT 1')
            version = cursor.fetchone()
            return version[0] if version else 0
            
        except Exception as e:
            print(f"Fehler beim Abrufen der Schema-Version: {e}")
            return 0
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