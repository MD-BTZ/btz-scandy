import sqlite3
from werkzeug.security import generate_password_hash

class SchemaManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.current_version = self._get_current_version()
        self.expected_version = 3  # Setze die erwartete Version auf 3

    def _get_current_version(self):
        """Hole die aktuelle Schema-Version"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.OperationalError:
            return 0

    def _create_schema_version_table(self, conn):
        """Erstelle die schema_version Tabelle"""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    def _create_tables(self, conn):
        """Erstelle alle Basis-Tabellen"""
        # Schema Version Tabelle
        self._create_schema_version_table(conn)
            
        # Access Settings Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS access_settings (
                route TEXT PRIMARY KEY,
                is_public BOOLEAN DEFAULT 0,
                description TEXT
            )
        ''')
            
        # Tools Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                category TEXT,
                location TEXT,
                status TEXT DEFAULT 'verfügbar',
                description TEXT,
                last_maintenance DATE,
                next_maintenance DATE,
                maintenance_interval INTEGER,
                last_checked TIMESTAMP,
                supplier TEXT,
                reorder_point INTEGER,
                notes TEXT,
                deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Consumables Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS consumables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                description TEXT,
                category TEXT,
                location TEXT,
                quantity INTEGER DEFAULT 0,
                min_quantity INTEGER DEFAULT 0,
                unit TEXT,
                supplier TEXT,
                reorder_point INTEGER,
                notes TEXT,
                deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Workers Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                barcode TEXT UNIQUE NOT NULL,
                department TEXT,
                email TEXT,
                phone TEXT,
                notes TEXT,
                deleted BOOLEAN DEFAULT 0,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Lendings Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS lendings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_barcode TEXT NOT NULL,
                worker_barcode TEXT NOT NULL,
                lent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                returned_at TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tool_barcode) REFERENCES tools(barcode),
                FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
            )
        ''')
        
        # Consumable Usage Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS consumable_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consumable_barcode TEXT NOT NULL,
                worker_barcode TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_status TEXT DEFAULT 'pending',
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
                FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
            )
        ''')
        
        # Settings Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Users Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                role TEXT NOT NULL DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')

        # Homepage Notices Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS homepage_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                priority INTEGER,
                is_active BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Sync Status Tabelle
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sync_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_sync TIMESTAMP,
                status TEXT,
                error TEXT
            )
        ''')

    def _insert_default_data(self, conn):
        """Fügt Standarddaten in die Datenbank ein."""
        with conn:
            cursor = conn.cursor()
            
            # Standard-Einstellungen
            default_settings = [
                ('label_tools_name', 'Werkzeuge', 'Anzeigename für Werkzeuge'),
                ('label_tools_icon', 'fas fa-tools', 'Icon für Werkzeuge'),
                ('label_consumables_name', 'Material', 'Anzeigename für Material'),
                ('label_consumables_icon', 'fas fa-box', 'Icon für Material'),
                ('color_primary', '#1a73e8', 'Primäre Farbe'),
                ('color_secondary', '#5f6368', 'Sekundäre Farbe'),
                ('color_success', '#34a853', 'Erfolgsfarbe'),
                ('color_warning', '#fbbc04', 'Warnfarbe'),
                ('color_error', '#ea4335', 'Fehlerfarbe'),
                ('default_tool_icon', 'fas fa-tools', 'Standard-Icon für Werkzeuge'),
                ('default_consumable_icon', 'fas fa-box', 'Standard-Icon für Verbrauchsmaterial')
            ]
            
            # Einstellungen einfügen
            cursor.executemany('''
                INSERT OR IGNORE INTO settings (key, value, description)
                VALUES (?, ?, ?)
            ''', default_settings)

    def initialize(self):
        """Initialisiere die Datenbank"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Erstelle alle Tabellen
                self._create_tables(conn)
                
                # Füge Standard-Daten ein
                self._insert_default_data(conn)
                
                # Initialisiere die Users-Tabelle
                self.init_users_table()
                
                # Setze die Schema-Version
                conn.execute('INSERT INTO schema_version (version) VALUES (?)', (self.expected_version,))
                conn.commit()
                
                print(f"Datenbankschema auf Version {self.expected_version} aktualisiert")
                return True
        except Exception as e:
            print(f"Fehler beim Initialisieren der Datenbank: {str(e)}")
            return False

    def needs_update(self):
        """Prüfe, ob ein Update notwendig ist"""
        return self.current_version < self.expected_version

    def update(self):
        """Führe Schema-Updates durch"""
        if not self.needs_update():
            return True
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Führe Updates basierend auf der aktuellen Version durch
                if self.current_version < 1:
                    self._create_tables(conn)
                    self._insert_default_data(conn)
                    conn.execute('INSERT INTO schema_version (version) VALUES (1)')
                
                if self.current_version < 2:
                    # Füge maintenance_interval und last_checked zur tools Tabelle hinzu
                    conn.execute('ALTER TABLE tools ADD COLUMN maintenance_interval INTEGER')
                    conn.execute('ALTER TABLE tools ADD COLUMN last_checked TIMESTAMP')
                    conn.execute('INSERT INTO schema_version (version) VALUES (2)')
                
                if self.current_version < 3:
                    # Füge maintenance_interval und last_checked zur tools Tabelle hinzu
                    conn.execute('ALTER TABLE tools ADD COLUMN maintenance_interval INTEGER')
                    conn.execute('ALTER TABLE tools ADD COLUMN last_checked TIMESTAMP')
                    conn.execute('INSERT INTO schema_version (version) VALUES (3)')
                
                conn.commit()
            print(f"Datenbankschema auf Version {self.expected_version} aktualisiert")
            return True
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Datenbank: {str(e)}")
            return False

    def validate_schema(self):
        """Validiert das aktuelle Schema"""
        try:
            conn = sqlite3.connect(self.db_path)
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
            ''', ('schema_version',))
            if not cursor.fetchone():
                raise Exception("Schema-Versionstabelle fehlt")
            
            # Prüfe die aktuelle Version
            cursor.execute(f'SELECT version FROM schema_version ORDER BY version DESC LIMIT 1')
            version = cursor.fetchone()
            if not version or version[0] != self.expected_version:
                raise Exception(f"Falsche Schema-Version: {version[0] if version else 'keine'} (erwartet: {self.expected_version})")
            
            return True
            
        except Exception as e:
            print(f"Schema-Validierung fehlgeschlagen: {e}")
            return False

    def get_schema_version(self):
        """Gibt die aktuelle Schema-Version zurück"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(f'SELECT version FROM schema_version ORDER BY version DESC LIMIT 1')
            version = cursor.fetchone()
            return version[0] if version else 0
            
        except Exception as e:
            print(f"Fehler beim Abrufen der Schema-Version: {e}")
            return 0
        
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
            conn = sqlite3.connect(self.db_path)
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
            conn = sqlite3.connect(self.db_path)
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
            self.initialize()
            
        except Exception as e:
            print(f"Fehler beim Zurücksetzen des Schemas: {e}")
            conn.rollback()
        finally:
            conn.close()
        
    def init_tables(self):
        """Initialisiert alle Tabellen"""
        # Diese Methode wird nicht mehr benötigt, da die Tabellen bereits in _create_tables erstellt werden
        pass

    def _prompt_admin_password(self):
        """Fragt nach einem Admin-Passwort beim ersten Start"""
        import getpass
        print("\n=== Erster Start - Admin-Konto einrichten ===")
        print("Bitte geben Sie ein Passwort für den Admin-Benutzer ein.")
        while True:
            password = getpass.getpass("Passwort: ")
            if len(password) < 8:
                print("Das Passwort muss mindestens 8 Zeichen lang sein.")
                continue
            confirm = getpass.getpass("Passwort bestätigen: ")
            if password != confirm:
                print("Die Passwörter stimmen nicht überein.")
                continue
            return password

    def init_users_table(self):
        """Initialisiert die Users-Tabelle"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users-Tabelle erstellen
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            conn.commit()

    def create_admin_user(self, password):
        """Erstellt den Admin-Benutzer mit dem angegebenen Passwort"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Prüfe ob es bereits Benutzer gibt
            cursor.execute('SELECT COUNT(*) FROM users')
            user_count = cursor.fetchone()[0]
            
            # Wenn keine Benutzer existieren, erstelle Admin-Account
            if user_count == 0:
                cursor.execute('''
                    INSERT INTO users (username, password_hash, role)
                    VALUES (?, ?, ?)
                ''', [
                    'admin',
                    generate_password_hash(password),
                    'admin'
                ])
                conn.commit()
                return True
            return False

    def _get_db_connection(self):
        """Gibt eine Datenbankverbindung zurück"""
        return sqlite3.connect(self.db_path)