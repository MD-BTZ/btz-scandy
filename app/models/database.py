"""
Database module for Scandy application.

This module provides database connection handling and base model functionality.
New code should use the BaseModel class as the base for all database models.
"""
import sqlite3
from datetime import datetime
import os
import sys
import logging
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple, TypeVar
from contextlib import contextmanager
from app.config import Config

logger = logging.getLogger(__name__)

# Type variable for type hints
T = TypeVar('T', bound='BaseModel')


class Database:
    """Database connection handler using singleton pattern.
    
    This class manages database connections and provides thread-safe access
    to the SQLite database. It implements connection pooling with timeout
    and automatic reconnection.
    
    Note: New code should prefer using the BaseModel class for database operations.
    """
    _instance = None
    _lock = threading.Lock()
    _connection = None
    _last_used = None
    _timeout = 300  # 5 minutes timeout for connections
    _max_retries = 3  # Maximum number of retry attempts
    _retry_delay = 1  # Delay between retry attempts in seconds
    _db_path = None  # Will be set during initialization

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None):
        """Get or create a database instance (singleton pattern).
        
        Args:
            db_path: Optional path to the SQLite database file.
                    If not provided, uses the default path 'app/database/inventory.db'.
                    
        Returns:
            Database: The database instance
        """
        # If no instance exists, create one
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-checked locking pattern
                    cls._instance = cls(db_path)
        else:
            # If a new db_path is provided and it's different from the current one,
            # close the existing connection and create a new one
            current_path = getattr(cls._instance, '_db_path', None)
            if db_path is not None and db_path != current_path:
                with cls._lock:
                    # Double-check after acquiring the lock
                    current_path = getattr(cls._instance, '_db_path', None)
                    if db_path != current_path:
                        logger.info(f"Changing database path from {current_path} to {db_path}")
                        if hasattr(cls._instance, '_connection') and cls._instance._connection is not None:
                            try:
                                cls._instance._connection.close()
                            except Exception as e:
                                logger.warning(f"Error closing database connection: {e}")
                        # Create a new instance with the new path
                        cls._instance = cls(db_path)
        
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the database connection.
        
        Args:
            db_path: Optional path to the SQLite database file.
                    If not provided, uses the default path 'app/database/inventory.db'.
        """
        # Use provided db_path or construct default path
        if db_path is None:
            # Get the base directory of the project (one level up from app/)
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            db_path = os.path.join(base_dir, 'app', 'database', 'inventory.db')
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Store the database path
        self._db_path = db_path
        
        # Initialize the connection
        self._ensure_connection()
        
        # Set up WAL mode for better concurrency
        self._setup_wal_mode()
    
    def _setup_wal_mode(self):
        """Set up Write-Ahead Logging (WAL) mode for better concurrency."""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                conn.commit()
                logger.debug("Database configured with WAL mode")
        except Exception as e:
            logger.error(f"Error setting up WAL mode: {e}")

    def _ensure_connection(self):
        """Ensure a valid database connection exists."""
        current_time = datetime.now()
        
        # Check if connection has timed out
        if (self._last_used and 
            (current_time - self._last_used).total_seconds() > self._timeout):
            self.close_connection()
        
        # Create new connection if necessary
        if not self._connection:
            for attempt in range(self._max_retries):
                try:
                    self._connection = sqlite3.connect(
                        self._db_path,  # Use _db_path instead of db_path
                        timeout=20.0,  # Timeout für Locks
                        check_same_thread=False  # Erlaubt Zugriff von verschiedenen Threads
                    )
                    self._connection.row_factory = sqlite3.Row
                    
                    # Aktiviere Foreign Keys
                    self._connection.execute("PRAGMA foreign_keys = ON")
                    
                    # Aktiviere WAL-Modus für bessere Performance
                    self._connection.execute("PRAGMA journal_mode = WAL")
                    
                    # Setze Busy-Timeout
                    self._connection.execute("PRAGMA busy_timeout = 5000")
                    
                    # Aktiviere Synchronisierung
                    self._connection.execute("PRAGMA synchronous = NORMAL")
                    
                    # Setze Cache-Größe
                    self._connection.execute("PRAGMA cache_size = -2000")  # 2MB Cache
                    
                    logger.info("Neue Datenbankverbindung erstellt")
                    break
                except Exception as e:
                    if attempt < self._max_retries - 1:
                        logger.warning(f"Verbindungsversuch {attempt + 1} fehlgeschlagen: {str(e)}")
                        time.sleep(self._retry_delay)
                    else:
                        logger.error(f"Fehler beim Erstellen der Datenbankverbindung nach {self._max_retries} Versuchen: {str(e)}")
                        raise

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        try:
            self._ensure_connection()
            self._last_used = datetime.now()
            yield self._connection
        except Exception as e:
            logger.error(f"Database operation failed: {str(e)}")
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {str(rollback_error)}")
            raise
        finally:
            self._last_used = datetime.now()

    def close_connection(self):
        """Close the current database connection."""
        if self._connection:
            try:
                # Perform WAL checkpoint
                self._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database connection: {str(e)}")
            finally:
                self._connection = None

    def execute_query(self, query, params=None):
        """Execute a SQL query."""
        for attempt in range(self._max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    conn.commit()
                    return cursor.fetchall()
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self._max_retries - 1:
                    logger.warning(f"Database locked, attempt {attempt + 1} of {self._max_retries}")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"Error executing query: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                raise

    def execute_many(self, query, params_list):
        """Execute multiple SQL queries."""
        for attempt in range(self._max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self._max_retries - 1:
                    logger.warning(f"Database locked, attempt {attempt + 1} of {self._max_retries}")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"Error executing multiple queries: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Error executing multiple queries: {str(e)}")
                raise

    def backup_database(self):
        """Create a backup of the database."""
        backup_path = f"{self._db_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            with self.get_connection() as conn:
                # Sync WAL file
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                
                # Create backup
                with sqlite3.connect(backup_path) as backup_conn:
                    conn.backup(backup_conn)
                
                logger.info(f"Database backup created: {backup_path}")
                return backup_path
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            raise

    def vacuum(self):
        """Run VACUUM on the database."""
        with self.get_connection() as conn:
            try:
                # Perform WAL checkpoint
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                
                # Run VACUUM
                conn.execute("VACUUM")
                logger.info("Database VACUUM completed")
            except Exception as e:
                logger.error(f"Error running VACUUM: {str(e)}")
                raise

    def check_integrity(self):
        """Check database integrity."""
        with self.get_connection() as conn:
            try:
                # Perform WAL checkpoint
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                
                # Check integrity
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result[0] == "ok":
                    logger.info("Database integrity check passed")
                    return True
                else:
                    logger.error(f"Database integrity check failed: {result[0]}")
                    return False
            except Exception as e:
                logger.error(f"Error during integrity check: {str(e)}")
                raise

    @classmethod
    def print_database_contents(cls):
        """Print contents of all tables in the main database (inventory.db) for debugging.

        Lists tables, columns, and the first few rows of each table.
        Passwords are censored for security.
        """
        logger.info("\n=== DATABASE CONTENTS ===")
        try:
            conn = cls.get_db_connection()
            cursor = conn.cursor()
            
            # Liste alle Tabellen
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table'
                ORDER BY name
            """)
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                logger.info(f"\nTable: {table_name}")
                
                try:
                    # Hole alle Einträge
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    if not rows:
                        logger.info("  [EMPTY]")
                        continue
                    
                    # Hole Spaltennamen
                    columns = [description[0] for description in cursor.description]
                    logger.info(f"  Columns: {', '.join(columns)}")
                    logger.info(f"  Number of entries: {len(rows)}")
                    
                    # Zeige die ersten 5 Einträge
                    for i, row in enumerate(rows[:5]):
                        row_dict = dict(row)
                        # Verstecke Passwörter
                        if 'password' in row_dict:
                            row_dict['password'] = '[VERSTECKT]'
                        logger.info(f"  {i+1}. {row_dict}")
                    
                    if len(rows) > 5:
                        logger.info(f"  ... und {len(rows) - 5} weitere Einträge")
                        
                except Exception as e:
                    logger.error(f"  Fehler beim Lesen der Tabelle {table_name}: {str(e)}")
            
            logger.info("\n=== ENDE DATENBANK INHALTE ===\n")
            
        except Exception as e:
            logger.error(f"Fehler beim Ausgeben der Datenbankinhalte: {str(e)}")
        finally:
            conn.close()

    @classmethod
    def ensure_db_exists(cls):
        """Stellt sicher, dass die Hauptdatenbankdatei (inventory.db) existiert.

        Prüft den Pfad aus der Config, erstellt das Verzeichnis bei Bedarf.
        Prüft, ob die DB lesbar ist und Tabellen enthält, wenn sie existiert.
        Erstellt eine leere DB-Datei, falls sie nicht existiert.

        Returns:
            bool: True, wenn die Datenbank existiert oder erfolgreich erstellt wurde,
                  False bei Fehlern.
        """
        logging.info("=== CHECKING DATABASE AT STARTUP ===")
        
        # Verwende den korrekten Pfad aus der Config
        db_path = Config.DATABASE
        
        logging.info(f"Configured database path: {db_path}")
        logging.info(f"Absolute database path: {os.path.abspath(db_path)}")
        
        # Stelle sicher, dass das Verzeichnis existiert
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        db_exists = os.path.exists(db_path)
        logging.info(f"Database exists: {db_exists}")
        
        if db_exists:
            # Prüfe ob die Datenbank lesbar ist und Daten enthält
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Prüfe Tabellen
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                table_names = [t[0] for t in tables]
                logging.info(f"Found tables: {table_names}")
                
                # Prüfe Inhalte und gib sie aus
                cls.print_database_contents()
                
                conn.close()
                
                if not tables:
                    logging.warning("Database exists but contains no tables")
                    return False
                    
                return True
                
            except Exception as e:
                logging.error(f"Error reading database: {str(e)}")
                return False
        else:
            logging.info("Creating new database")
            try:
                conn = sqlite3.connect(db_path)
                conn.close()
                return True
            except Exception as e:
                logging.error(f"Error creating database: {str(e)}")
                return False
    
    @classmethod
    def get_db_connection(cls):
        """Erstellt und gibt eine *neue*, unabhängige Verbindung zur Hauptdatenbank (inventory.db) zurück.

        Verwendet den Pfad aus der aktuellen Flask-Konfiguration.
        Setzt conn.row_factory = sqlite3.Row für Dictionary-ähnlichen Zugriff.

        Returns:
            sqlite3.Connection: Eine neue Datenbankverbindung.
        """
        from app.config import config
        current_config = config['default']()
        conn = sqlite3.connect(current_config.DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    
    @classmethod
    def get_db(cls):
        """Gibt eine Datenbankverbindung zur Hauptdatenbank (inventory.db) aus dem Flask-Anwendungskontext (g) zurück.

        Erstellt die Verbindung beim ersten Aufruf pro Request und speichert sie in `g.db`.
        Verwendet den Pfad aus `Config.DATABASE`.
        Setzt conn.row_factory = sqlite3.Row.
        Führt beim ersten Verbindungsaufbau Debug-Checks zur Tabellenanzahl durch.

        Returns:
            sqlite3.Connection: Die Datenbankverbindung für den aktuellen Request-Kontext.
        """
        try:
            from flask import g, current_app
            if hasattr(g, 'db'):
                return g.db
                
            # Get database path from config
            db_path = current_app.config.get('DATABASE') or Config.DATABASE
            
            # Create new connection if not in g
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
            
            # Debug: Prüfe Tabelleninhalte beim ersten Verbindungsaufbau
            cursor = g.db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()['count']
                logging.info(f"Tabelle {table_name} enthält {count} Einträge")
                
            return g.db
            
        except RuntimeError:  # Outside of application context
            # Create a new connection if we're not in a request context
            db_path = Config.DATABASE
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    @classmethod
    def show_db_structure(cls):
        """Gibt die Struktur der Hauptdatenbank (inventory.db) zurück.

        Listet alle Tabellen und ihre Spaltennamen auf.

        Returns:
            dict: Ein Dictionary, bei dem Schlüssel Tabellennamen und Werte Listen von Spaltennamen sind.
        """
        conn = cls.get_db_connection()
        cursor = conn.cursor()
        
        # Tabellen auflisten
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        structure = {}
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            structure[table_name] = [column[1] for column in columns]
        
        conn.close()
        return structure
    
    @staticmethod
    def query(sql, params=None, one=False):
        """Führt eine SQL-Abfrage auf der Hauptdatenbank (inventory.db) aus.

        Verwendet die Verbindung aus dem Flask-Anwendungskontext (`get_db`).
        Führt automatisches Commit für INSERT, UPDATE, DELETE aus.
        Loggt die Abfrage, Parameter und Ergebnisse (Beispielrecord).

        Args:
            sql (str): Die auszuführende SQL-Anweisung.
            params (list | tuple, optional): Parameter für die SQL-Anweisung.
            one (bool, optional): Wenn True, wird nur der erste Datensatz zurückgegeben (fetchone),
                                andernfalls alle (fetchall). Standard ist False.

        Returns:
            sqlite3.Row | list[sqlite3.Row] | None: Das Ergebnis der Abfrage.

        Raises:
            sqlite3.Error: Bei Datenbankfehlern.
        """
        logging.info("\n=== DATABASE QUERY ===")
        logging.info(f"SQL: {sql}")
        logging.info(f"Parameters: {params}")
        
        try:
            conn = Database.get_db()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Automatisches Commit für INSERT, UPDATE, DELETE
            if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
                logging.info("Änderungen committed")
                
            if one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
            
            # Konvertiere Datetime-Felder
            if result:
                if one:
                    result = dict(result)
                    for key, value in result.items():
                        if isinstance(value, str) and key.endswith('_at'):
                            try:
                                result[key] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                pass
                else:
                    result = [dict(row) for row in result]
                    for row in result:
                        for key, value in row.items():
                            if isinstance(value, str) and key.endswith('_at'):
                                try:
                                    row[key] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    pass
            
            # Debug-Ausgaben
            if result:
                logging.info(f"Number of results: {len([result] if one else result)}")
                logging.info(f"Example record: {result if one else result[0]}")
            else:
                logging.info("No results returned")
                
            return result
            
        except Exception as e:
            logging.error(f"Datenbankfehler: {str(e)}")
            logging.error(f"Query: {sql}")
            logging.error(f"Parameters: {params}")
            raise
    
    @classmethod
    def get_departments(cls):
        """Gibt alle Abteilungen mit der Anzahl der zugeordneten Mitarbeiter zurück"""
        try:
            departments = cls.query("""
                SELECT 
                    d.name,
                    d.description,
                    COUNT(w.id) as worker_count
                FROM departments d
                LEFT JOIN workers w ON w.department = d.name AND w.deleted = 0
                WHERE d.deleted = 0
                GROUP BY d.name
                ORDER BY d.name
            """)
            
            return [{'name': dept['name'], 'worker_count': dept['worker_count']} for dept in departments]
        except Exception as e:
            logging.error(f"Fehler beim Laden der Abteilungen: {str(e)}")
            return []
    
    @classmethod
    def get_locations(cls):
        """Hole alle Standorte"""
        try:
            with cls.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name,
                           description,
                           (SELECT COUNT(*) FROM tools WHERE location = l.name AND deleted = 0) as tool_count,
                           (SELECT COUNT(*) FROM consumables WHERE location = l.name AND deleted = 0) as consumable_count
                    FROM locations l
                    WHERE deleted = 0
                    ORDER BY name
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Fehler beim Abrufen der Standorte: {e}")
            return []
    
    @classmethod
    def get_categories(cls, usage=None):
        """Gibt alle Kategorien mit der Anzahl der zugeordneten Werkzeuge und Verbrauchsmaterialien zurück"""
        try:
            categories = cls.query("""
                SELECT 
                    c.name,
                    c.description,
                    (SELECT COUNT(*) FROM tools WHERE category = c.name AND deleted = 0) as tools_count,
                    (SELECT COUNT(*) FROM consumables WHERE category = c.name AND deleted = 0) as consumables_count
                FROM categories c
                WHERE c.deleted = 0
                ORDER BY c.name
            """)
            
            return [
                {
                    'name': cat['name'],
                    'usage': cat['description'],
                    'tools_count': cat['tools_count'],
                    'consumables_count': cat['consumables_count']
                }
                for cat in categories
            ]
        except Exception as e:
            logging.error(f"Fehler beim Laden der Kategorien: {str(e)}")
            return []
    
    @classmethod
    def restore_backup(cls, backup_file):
        """Stellt ein Backup wieder her"""
        try:
            # Schließe alle bestehenden Verbindungen
            if hasattr(cls, '_connection'):
                cls._connection.close()
                delattr(cls, '_connection')
            
            backup_path = os.path.join(Config.BACKUP_DIR, backup_file)
            if not os.path.exists(backup_path):
                print(f"Backup {backup_file} nicht gefunden")
                return False

            # Sichere aktuelle Datenbank
            db_path = Config.DATABASE
            if os.path.exists(db_path):
                os.rename(db_path, db_path + '.bak')

            # Kopiere Backup
            shutil.copy2(backup_path, db_path)

            # Teste die wiederhergestellte Datenbank
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Prüfe Tabelleneinträge
                tables = ['tools', 'consumables', 'workers', 'lendings', 'consumable_usages']
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                    count = cursor.fetchone()['count']
                    print(f"Tabelle {table} enthält {count} Einträge")
                
                conn.close()
                
                # Lösche Backup wenn Test erfolgreich
                if os.path.exists(db_path + '.bak'):
                    os.remove(db_path + '.bak')
                    
                print("Backup wurde erfolgreich wiederhergestellt")
                
                # Erstelle Flag für Neustart
                tmp_dir = os.path.join(os.path.dirname(Config.BASE_DIR), 'tmp')
                os.makedirs(tmp_dir, exist_ok=True)
                with open(os.path.join(tmp_dir, 'needs_restart'), 'w') as f:
                    f.write('1')
                    
                return True

            except Exception as e:
                print(f"Fehler beim Testen des Backups: {str(e)}")
                # Stelle Original wieder her
                if os.path.exists(db_path + '.bak'):
                    os.remove(db_path)
                    os.rename(db_path + '.bak', db_path)
                return False

        except Exception as e:
            print(f"Fehler bei der Backup-Wiederherstellung: {str(e)}")
            return False

    @classmethod
    def init_app(cls, app):
        """Initialisiert die Datenbankverbindung für die Flask-App"""
        @app.teardown_appcontext
        def close_db(error):
            if error:
                logger.error(f"Fehler beim Beenden des Request-Kontexts: {str(error)}")
            cls.close_connection()

    @classmethod
    def update_category_usage(cls, name, usage):
        """Aktualisiert die Nutzungsart einer Kategorie"""
        try:
            with cls.get_db() as db:
                db.execute(
                    "UPDATE settings SET description = ? WHERE key = ? AND key LIKE 'category_%'",
                    (usage, f"category_{name}")
                )
                db.commit()
                return True
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Kategorie-Nutzung: {e}")
            return False

    @classmethod
    def update_location_usage(cls, name, usage):
        """Aktualisiert die Nutzungsart eines Standorts"""
        try:
            with cls.get_db() as db:
                db.execute(
                    "UPDATE settings SET description = ? WHERE key = ? AND key LIKE 'location_%'",
                    (usage, f"location_{name}")
                )
                db.commit()
                return True
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Standort-Nutzung: {e}")
            return False

    @classmethod
    def get_consumables_forecast(cls):
        """Berechnet die Bestandsprognose für Verbrauchsmaterialien"""
        try:
            return cls.query("""
                WITH daily_usage AS (
                    SELECT 
                        c.barcode,
                        c.name,
                        c.quantity as current_amount,
                        CAST(SUM(cu.quantity) AS FLOAT) / 30 as avg_daily_usage
                    FROM consumables c
                    LEFT JOIN consumable_usages cu 
                        ON c.barcode = cu.consumable_barcode
                        AND cu.used_at >= date('now', '-30 days')
                    WHERE c.deleted = 0
                    GROUP BY c.barcode, c.name, c.quantity
                )
                SELECT 
                    name,
                    current_amount,
                    ROUND(avg_daily_usage, 2) as avg_daily_usage,
                    CASE 
                        WHEN avg_daily_usage > 0 
                        THEN ROUND(current_amount / avg_daily_usage)
                        ELSE 999
                    END as days_remaining
                FROM daily_usage
                WHERE current_amount > 0
                ORDER BY days_remaining ASC
                LIMIT 10
            """)
        except Exception as e:
            print(f"Fehler beim Abrufen der Bestandsprognose: {e}")
            return []

def init_db():
    """Initialisiert die Hauptdatenbank, falls sie leer ist oder Tabellen fehlen."""
    try:
        conn = sqlite3.connect(Config.DATABASE)
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Prüfe ob Admin-Benutzer existiert
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        logger.info(f"Admin-User-Count: {admin_count}")
        
        if admin_count == 0:
            logger.warning("Kein Admin-Benutzer gefunden.")
        else:
            logger.info("Mindestens ein Admin-Benutzer existiert bereits.")

        conn.commit()
        logger.info("Datenbank erfolgreich initialisiert.")
        
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankinitialisierung: {e}")
        conn.rollback() # Änderungen rückgängig machen bei Fehler
    finally:
        conn.close()