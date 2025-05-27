import sqlite3
from werkzeug.security import generate_password_hash
from app.models.database import Database
import logging
import os
import shutil
from datetime import datetime
import stat

logger = logging.getLogger(__name__)

class SchemaManager:
    _initialized_dbs = set()  # Klassen-Variable für alle initialisierten Datenbanken
    
    def __init__(self, db_path):
        self.db_path = db_path
        self.current_version = self._get_current_version()
        self.expected_version = 5
        self._initialized = False
        self._backup_path = f"{db_path}.backup"

    def _check_and_fix_permissions(self):
        """Überprüft und korrigiert die Dateiberechtigungen"""
        try:
            if os.path.exists(self.db_path):
                current_perms = stat.S_IMODE(os.lstat(self.db_path).st_mode)
                # Setze Berechtigungen auf rw-rw-r--
                desired_perms = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
                
                if current_perms != desired_perms:
                    logger.info(f"Korrigiere Berechtigungen für {self.db_path}")
                    os.chmod(self.db_path, desired_perms)
                    logger.info("Berechtigungen erfolgreich korrigiert")
            else:
                logger.info(f"Datenbank {self.db_path} existiert noch nicht")
        except Exception as e:
            logger.error(f"Fehler beim Überprüfen/Korrigieren der Berechtigungen: {str(e)}")

    def _create_backup(self):
        """Erstellt ein Backup der Datenbank vor Änderungen"""
        if os.path.exists(self.db_path):
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.{backup_time}"
            try:
                shutil.copy2(self.db_path, backup_path)
                logger.info(f"Datenbank-Backup erstellt: {backup_path}")
                return True
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
                return False
        return True

    def _restore_backup(self):
        """Stellt das letzte Backup wieder her"""
        if os.path.exists(self._backup_path):
            try:
                shutil.copy2(self._backup_path, self.db_path)
                logger.info("Datenbank aus Backup wiederhergestellt")
                return True
            except Exception as e:
                logger.error(f"Fehler beim Wiederherstellen des Backups: {str(e)}")
                return False
        return False

    def _get_current_version(self):
        """Ermittelt die aktuelle Schema-Version"""
        try:
            if not os.path.exists(self.db_path):
                return 0
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln der Schema-Version: {str(e)}")
            return 0

    def initialize(self):
        """Initialisiert die Datenbank mit allen notwendigen Tabellen"""
        if self.db_path in self._initialized_dbs:
            logger.info(f"Datenbank {self.db_path} wurde bereits initialisiert")
            return True

        try:
            # Erstelle Backup vor Änderungen
            if not self._create_backup():
                logger.error("Konnte kein Backup erstellen - Initialisierung abgebrochen")
                return False

            # Stelle sicher, dass das Verzeichnis existiert
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            # Überprüfe und korrigiere Berechtigungen
            self._check_and_fix_permissions()

            with sqlite3.connect(self.db_path) as conn:
                # Aktiviere Foreign Keys
                conn.execute("PRAGMA foreign_keys = ON")
                
                # Aktiviere WAL-Modus für bessere Performance
                conn.execute("PRAGMA journal_mode = WAL")
                
                # Setze Busy-Timeout
                conn.execute("PRAGMA busy_timeout = 5000")
                
                # Aktiviere Synchronisierung
                conn.execute("PRAGMA synchronous = NORMAL")
                
                # Setze Cache-Größe
                conn.execute("PRAGMA cache_size = -2000")  # 2MB Cache

                # Erstelle Schema-Version Tabelle
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Erstelle alle Tabellen
                self._create_tables(conn)

                # Setze Schema-Version
                current_version = self._get_current_version()
                if current_version < self.expected_version:
                    conn.execute(
                        "INSERT INTO schema_version (version) VALUES (?)",
                        [self.expected_version]
                    )

                # Füge Standarddaten ein, falls noch keine vorhanden sind
                self._insert_default_data(conn)

                conn.commit()
                logger.info(f"Datenbank {self.db_path} erfolgreich initialisiert")
                self._initialized_dbs.add(self.db_path)
                return True

        except Exception as e:
            logger.error(f"Fehler bei der Datenbankinitialisierung: {str(e)}")
            # Versuche Backup wiederherzustellen
            self._restore_backup()
            return False

    def _create_tables(self, conn):
        """Erstellt alle notwendigen Tabellen"""
        try:
            # Users Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    firstname TEXT,
                    lastname TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')

            # Tools Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'verfügbar',
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

            # Workers Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    firstname TEXT NOT NULL,
                    lastname TEXT NOT NULL,
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

            # Consumables Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consumables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    quantity INTEGER DEFAULT 0,
                    min_quantity INTEGER DEFAULT 0,
                    category TEXT,
                    location TEXT,
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

            # Consumable Usages Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consumable_usages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumable_barcode TEXT NOT NULL,
                    worker_barcode TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Kategorien Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'ticket',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at DATETIME,
                    UNIQUE(name, type)
                )
            ''')

            # Standorte Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP
                )
            ''')

            # Abteilungen Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP
                )
            ''')

            # History Tabelle
            conn.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    user_id INTEGER,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            # Erstelle Indizes für bessere Performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tools_barcode ON tools(barcode)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_workers_barcode ON workers(barcode)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_consumables_barcode ON consumables(barcode)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_lendings_tool_barcode ON lendings(tool_barcode)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_lendings_worker_barcode ON lendings(worker_barcode)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_consumable_usages_consumable_barcode ON consumable_usages(consumable_barcode)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_consumable_usages_worker_barcode ON consumable_usages(worker_barcode)')

            logger.info("Alle Tabellen und Indizes erfolgreich erstellt")
            return True

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Tabellen: {str(e)}")
            raise

    def _insert_default_data(self, conn):
        """Fügt Standarddaten in die Datenbank ein"""
        try:
            # Nur Grundeinstellungen werden hier eingefügt
            default_settings = {
                'theme': 'light',
                'language': 'de',
                'items_per_page': '10',
                'primary_color': '259 94% 51%',    # Standard Blau
                'secondary_color': '314 100% 47%',  # Standard Pink
                'accent_color': '174 60% 51%'       # Standard Türkis
            }
            
            for key, value in default_settings.items():
                conn.execute("""
                    INSERT OR IGNORE INTO settings (key, value)
                    VALUES (?, ?)
                """, (key, value))
            
            logger.info("Grundeinstellungen wurden erfolgreich eingefügt")
            
        except Exception as e:
            logger.error(f"Fehler beim Einfügen der Grundeinstellungen: {e}")
            raise

    def create_admin_user(self, password):
        """Erstellt den Admin-Benutzer mit dem angegebenen Passwort"""
        try:
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
                    logger.info("Admin-Benutzer erfolgreich erstellt")
                    return True
                return False
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}")
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
                cursor = conn.cursor()
                
                # Führe Updates basierend auf der aktuellen Version durch
                if self.current_version < 1:
                    self._create_tables(conn)
                    self._insert_default_data(conn)
                    cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (1)')
                
                if self.current_version < 2:
                    # Füge maintenance_interval und last_checked zur tools Tabelle hinzu
                    try:
                        conn.execute('ALTER TABLE tools ADD COLUMN maintenance_interval INTEGER')
                    except sqlite3.OperationalError:
                        pass  # Spalte existiert bereits
                    try:
                        conn.execute('ALTER TABLE tools ADD COLUMN last_checked TIMESTAMP')
                    except sqlite3.OperationalError:
                        pass  # Spalte existiert bereits
                    cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (2)')
                
                if self.current_version < 3:
                    # Füge maintenance_interval und last_checked zur tools Tabelle hinzu
                    try:
                        conn.execute('ALTER TABLE tools ADD COLUMN maintenance_interval INTEGER')
                    except sqlite3.OperationalError:
                        pass  # Spalte existiert bereits
                    try:
                        conn.execute('ALTER TABLE tools ADD COLUMN last_checked TIMESTAMP')
                    except sqlite3.OperationalError:
                        pass  # Spalte existiert bereits
                    cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (3)')
                
                if self.current_version < 4:
                    # Erstelle ticket_messages Tabelle
                    conn.execute('''
                        CREATE TABLE IF NOT EXISTS ticket_messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ticket_id INTEGER NOT NULL,
                            message TEXT NOT NULL,
                            sender TEXT NOT NULL,
                            is_admin BOOLEAN DEFAULT 0,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                            FOREIGN KEY (sender) REFERENCES users(username)
                        )
                    ''')
                    cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (4)')
                
                if self.current_version < 5:
                    # Füge firstname und lastname zur users Tabelle hinzu
                    try:
                        conn.execute('ALTER TABLE users ADD COLUMN firstname TEXT')
                    except sqlite3.OperationalError:
                        pass  # Spalte existiert bereits
                    try:
                        conn.execute('ALTER TABLE users ADD COLUMN lastname TEXT')
                    except sqlite3.OperationalError:
                        pass  # Spalte existiert bereits
                    cursor.execute('INSERT OR IGNORE INTO schema_version (version) VALUES (5)')
                
                conn.commit()
                self._initialized = True
                logger.info(f"Datenbankschema auf Version {self.expected_version} aktualisiert")
                return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Datenbank: {str(e)}")
            return False

    def _validate_table_columns(self, conn, table_name):
        """Validiert die Spalten einer Tabelle gegen das erwartete Schema"""
        cursor = conn.cursor()
        
        # Hole das aktuelle Tabellenschema
        cursor.execute(f"PRAGMA table_info({table_name})")
        current_columns = {row[1]: {'type': row[2], 'notnull': row[3], 'pk': row[5]} for row in cursor.fetchall()}
        
        # Hole das erwartete Schema aus der CREATE TABLE Anweisung
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        create_statement = cursor.fetchone()[0]
        
        # Extrahiere die Spaltendefinitionen aus der CREATE TABLE Anweisung
        import re
        # Ignoriere SQL-Schlüsselwörter und extrahiere nur die tatsächlichen Spaltennamen
        column_defs = re.findall(r'(\w+)\s+([A-Z]+)(?:\s+NOT\s+NULL)?(?:\s+DEFAULT\s+[^,]+)?(?:\s+PRIMARY\s+KEY)?', create_statement)
        expected_columns = {}
        
        # SQLite-Datentyp-Mapping
        sqlite_type_mapping = {
            'INTEGER': ['INTEGER', 'INT', 'TINYINT', 'SMALLINT', 'MEDIUMINT', 'BIGINT', 'UNSIGNED BIG INT', 'INT2', 'INT8'],
            'TEXT': ['TEXT', 'CHARACTER', 'VARCHAR', 'VARYING CHARACTER', 'NCHAR', 'NATIVE CHARACTER', 'NVARCHAR', 'CLOB'],
            'REAL': ['REAL', 'DOUBLE', 'DOUBLE PRECISION', 'FLOAT'],
            'BLOB': ['BLOB'],
            'BOOLEAN': ['BOOLEAN', 'BOOL']
        }
        
        for name, type_ in column_defs:
            # Ignoriere SQL-Schlüsselwörter
            if name.upper() not in ['CREATE', 'TABLE', 'IF', 'NOT', 'EXISTS', 'FOREIGN', 'KEY', 'ON', 'DELETE', 'CASCADE', 'UNIQUE']:
                # Normalisiere den Datentyp
                normalized_type = None
                for sqlite_type, aliases in sqlite_type_mapping.items():
                    if type_.upper() in aliases:
                        normalized_type = sqlite_type
                        break
                if normalized_type:
                    expected_columns[name] = {'type': normalized_type}
        
        # Validiere jede Spalte
        missing_columns = []
        wrong_type_columns = []
        
        for col_name, col_info in expected_columns.items():
            if col_name not in current_columns:
                missing_columns.append(col_name)
            else:
                current_type = current_columns[col_name]['type'].upper()
                expected_type = col_info['type'].upper()
                
                # Prüfe ob der aktuelle Typ mit dem erwarteten Typ kompatibel ist
                type_compatible = False
                for sqlite_type, aliases in sqlite_type_mapping.items():
                    if current_type in aliases and expected_type == sqlite_type:
                        type_compatible = True
                        break
                
                if not type_compatible:
                    wrong_type_columns.append((col_name, current_type, expected_type))
        
        return missing_columns, wrong_type_columns

    def validate_schema(self):
        """Validiert das aktuelle Schema und fügt fehlende Spalten hinzu"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prüfe ob alle erforderlichen Tabellen existieren
            required_tables = [
                'tools', 'consumables', 'workers', 'lendings',
                'consumable_usages', 'settings', 'users', 'access_settings',
                'tickets', 'ticket_notes', 'ticket_history', 'ticket_messages'
            ]
            
            missing_tables = []
            for table in required_tables:
                cursor.execute(f'''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                ''', (table,))
                if not cursor.fetchone():
                    missing_tables.append(table)
            
            if missing_tables:
                raise Exception(f"Fehlende Tabellen: {', '.join(missing_tables)}")
            
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
            
            # Validiere die Spalten jeder Tabelle und füge fehlende Spalten hinzu
            schema_errors = []
            for table in required_tables:
                missing_cols, wrong_type_cols = self._validate_table_columns(conn, table)
                
                # Füge fehlende Spalten hinzu
                if missing_cols:
                    print(f"Füge fehlende Spalten zur Tabelle {table} hinzu: {', '.join(missing_cols)}")
                    for col in missing_cols:
                        try:
                            # Hole die Spaltendefinition aus der CREATE TABLE Anweisung
                            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
                            create_statement = cursor.fetchone()[0]
                            
                            # Extrahiere die Spaltendefinition
                            import re
                            col_def = re.search(f"{col}\\s+([^,]+)(?:,|$)", create_statement)
                            if col_def:
                                col_type = col_def.group(1)
                                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                                print(f"Spalte {col} zur Tabelle {table} hinzugefügt")
                        except Exception as e:
                            schema_errors.append(f"Fehler beim Hinzufügen der Spalte {col} zur Tabelle {table}: {str(e)}")
                
                if wrong_type_cols:
                    for col_name, current_type, expected_type in wrong_type_cols:
                        schema_errors.append(f"Tabelle {table}: Falscher Datentyp für Spalte {col_name} (aktuell: {current_type}, erwartet: {expected_type})")
            
            if schema_errors:
                raise Exception("Schema-Validierungsfehler:\n" + "\n".join(schema_errors))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Schema-Validierung fehlgeschlagen: {e}")
            return False
        finally:
            conn.close()

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
                    firstname TEXT,
                    lastname TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
            
            conn.commit()

    def _get_db_connection(self):
        """Gibt eine Datenbankverbindung zurück"""
        return sqlite3.connect(self.db_path)

# Maximale Längen für Textfelder
FIELD_LENGTHS = {
    'tools': {
        'barcode': 50,
        'name': 100,
        'category': 50,
        'location': 50,
        'status': 20,
        'description': 500
    },
    'consumables': {
        'barcode': 50,
        'name': 100,
        'category': 50,
        'location': 50,
        'description': 500
    },
    'workers': {
        'barcode': 50,
        'firstname': 50,
        'lastname': 50,
        'department': 50,
        'email': 100
    },
    'users': {
        'username': 50,
        'email': 100,
        'role': 20
    },
    'tickets': {
        'title': 200,
        'description': 2000,
        'category': 50,
        'status': 20,
        'priority': 20
    }
}

# Numerische Limits
NUMERIC_LIMITS = {
    'consumables': {
        'quantity': 1000000,  # Max 1 Million Stück
        'min_quantity': 100000  # Max 100.000 als Mindestbestand
    },
    'tickets': {
        'estimated_time': 1000,  # Max 1000 Stunden
        'actual_time': 1000
    }
}

def validate_field_length(table: str, field: str, value: str) -> bool:
    """Überprüft, ob ein Textfeld die maximale Länge nicht überschreitet."""
    if not value:
        return True
    
    max_length = FIELD_LENGTHS.get(table, {}).get(field)
    if max_length and len(str(value)) > max_length:
        logger.warning(f"Feld {field} in Tabelle {table} überschreitet maximale Länge von {max_length}")
        return False
    return True

def validate_numeric_limit(table: str, field: str, value: int) -> bool:
    """Überprüft, ob ein numerisches Feld die Limits nicht überschreitet."""
    if value is None:
        return True
    
    max_value = NUMERIC_LIMITS.get(table, {}).get(field)
    if max_value and value > max_value:
        logger.warning(f"Feld {field} in Tabelle {table} überschreitet maximalen Wert von {max_value}")
        return False
    return True

def truncate_field(table: str, field: str, value: str) -> str:
    """Kürzt einen Text auf die maximale Länge."""
    if not value:
        return value
    
    max_length = FIELD_LENGTHS.get(table, {}).get(field)
    if max_length and len(str(value)) > max_length:
        logger.warning(f"Feld {field} in Tabelle {table} wurde auf {max_length} Zeichen gekürzt")
        return str(value)[:max_length]
    return value

def apply_schema_constraints():
    """Wendet die Schema-Einschränkungen auf die Datenbank an."""
    try:
        with Database.get_db() as conn:
            # Tools
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tools (
                    barcode TEXT PRIMARY KEY CHECK(length(barcode) <= 50),
                    name TEXT NOT NULL CHECK(length(name) <= 100),
                    category TEXT CHECK(length(category) <= 50),
                    location TEXT CHECK(length(location) <= 50),
                    status TEXT CHECK(length(status) <= 20),
                    description TEXT CHECK(length(description) <= 500),
                    deleted INTEGER DEFAULT 0,
                    deleted_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending'
                )
            ''')

            # Consumables
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consumables (
                    barcode TEXT PRIMARY KEY CHECK(length(barcode) <= 50),
                    name TEXT NOT NULL CHECK(length(name) <= 100),
                    category TEXT CHECK(length(category) <= 50),
                    location TEXT CHECK(length(location) <= 50),
                    quantity INTEGER NOT NULL CHECK(quantity >= 0 AND quantity <= 1000000),
                    min_quantity INTEGER NOT NULL CHECK(min_quantity >= 0 AND min_quantity <= 100000),
                    description TEXT CHECK(length(description) <= 500),
                    deleted INTEGER DEFAULT 0,
                    deleted_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending'
                )
            ''')

            # Workers
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workers (
                    barcode TEXT PRIMARY KEY CHECK(length(barcode) <= 50),
                    firstname TEXT NOT NULL CHECK(length(firstname) <= 50),
                    lastname TEXT NOT NULL CHECK(length(lastname) <= 50),
                    department TEXT CHECK(length(department) <= 50),
                    email TEXT CHECK(length(email) <= 100),
                    deleted INTEGER DEFAULT 0,
                    deleted_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending'
                )
            ''')

            # Users
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL CHECK(length(username) <= 50),
                    email TEXT UNIQUE CHECK(length(email) <= 100),
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(length(role) <= 20),
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tickets
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK(length(title) <= 200),
                    description TEXT CHECK(length(description) <= 2000),
                    category TEXT CHECK(length(category) <= 50),
                    status TEXT NOT NULL CHECK(length(status) <= 20),
                    priority TEXT NOT NULL CHECK(length(priority) <= 20),
                    created_by TEXT NOT NULL,
                    assigned_to TEXT,
                    estimated_time INTEGER CHECK(estimated_time >= 0 AND estimated_time <= 1000),
                    actual_time INTEGER CHECK(actual_time >= 0 AND actual_time <= 1000),
                    due_date DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME
                )
            ''')

            conn.commit()
            logger.info("Datenbank-Schema-Einschränkungen wurden erfolgreich angewendet")
            return True

    except Exception as e:
        logger.error(f"Fehler beim Anwenden der Schema-Einschränkungen: {str(e)}")
        return False

def validate_input(table: str, data: dict) -> tuple[bool, str]:
    """
    Validiert Eingabedaten gegen die Schema-Definitionen.
    Returns: (is_valid, error_message)
    """
    try:
        # Textfelder validieren
        for field, value in data.items():
            if isinstance(value, str):
                if not validate_field_length(table, field, value):
                    return False, f"Feld {field} ist zu lang (max {FIELD_LENGTHS.get(table, {}).get(field)} Zeichen)"
            
            # Numerische Felder validieren
            elif isinstance(value, (int, float)):
                if not validate_numeric_limit(table, field, value):
                    return False, f"Feld {field} überschreitet den maximalen Wert von {NUMERIC_LIMITS.get(table, {}).get(field)}"
        
        return True, ""
    
    except Exception as e:
        logger.error(f"Fehler bei der Eingabevalidierung: {str(e)}")
        return False, f"Validierungsfehler: {str(e)}"

def create_categories_table(conn):
    """Erstellt die Kategorien-Tabelle."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'ticket',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deleted INTEGER DEFAULT 0,
            deleted_at DATETIME,
            UNIQUE(name, type)
        )
    ''')