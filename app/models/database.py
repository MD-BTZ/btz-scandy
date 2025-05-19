from flask import g, current_app
import sqlite3
from datetime import datetime
import os
import logging
from app.config import Config
import json
from pathlib import Path
import shutil
from contextlib import contextmanager
import threading
import time

# Optional requests importieren
try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

class Database:
    _instance = None
    _lock = threading.Lock()
    _connection = None
    _last_used = None
    _timeout = 300  # 5 Minuten Timeout für Verbindungen
    _max_retries = 3  # Maximale Anzahl von Wiederholungsversuchen
    _retry_delay = 1  # Verzögerung zwischen Wiederholungsversuchen in Sekunden

    @classmethod
    def get_instance(cls):
        """Singleton-Pattern für die Datenbankverbindung"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialisiert die Datenbankverbindung"""
        self.current_config = Config.config['default']()
        self.db_path = os.path.join(self.current_config.BASE_DIR, 'app', 'database', 'inventory.db')
        self._ensure_connection()

    def _ensure_connection(self):
        """Stellt sicher, dass eine gültige Verbindung existiert"""
        current_time = datetime.now()
        
        # Prüfe ob die Verbindung abgelaufen ist
        if (self._last_used and 
            (current_time - self._last_used).total_seconds() > self._timeout):
            self.close_connection()
        
        # Erstelle neue Verbindung wenn nötig
        if not self._connection:
            for attempt in range(self._max_retries):
                try:
                    self._connection = sqlite3.connect(
                        self.db_path,
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
        """Kontext-Manager für Datenbankverbindungen"""
        try:
            self._ensure_connection()
            self._last_used = datetime.now()
            yield self._connection
        except Exception as e:
            logger.error(f"Fehler bei der Datenbankoperation: {str(e)}")
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception as rollback_error:
                    logger.error(f"Fehler beim Rollback: {str(rollback_error)}")
            raise
        finally:
            self._last_used = datetime.now()

    def close_connection(self):
        """Schließt die aktuelle Datenbankverbindung"""
        if self._connection:
            try:
                # Führe WAL-Checkpoint durch
                self._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                self._connection.close()
                logger.info("Datenbankverbindung geschlossen")
            except Exception as e:
                logger.error(f"Fehler beim Schließen der Datenbankverbindung: {str(e)}")
            finally:
                self._connection = None

    def execute_query(self, query, params=None):
        """Führt eine SQL-Abfrage aus"""
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
                    logger.warning(f"Datenbank gesperrt, Versuch {attempt + 1} von {self._max_retries}")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"Fehler bei der Ausführung der Abfrage: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Fehler bei der Ausführung der Abfrage: {str(e)}")
                raise

    def execute_many(self, query, params_list):
        """Führt mehrere SQL-Abfragen aus"""
        for attempt in range(self._max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < self._max_retries - 1:
                    logger.warning(f"Datenbank gesperrt, Versuch {attempt + 1} von {self._max_retries}")
                    time.sleep(self._retry_delay)
                else:
                    logger.error(f"Fehler bei der Ausführung mehrerer Abfragen: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Fehler bei der Ausführung mehrerer Abfragen: {str(e)}")
                raise

    def backup_database(self):
        """Erstellt ein Backup der Datenbank"""
        backup_path = f"{self.db_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            with self.get_connection() as conn:
                # WAL-Datei synchronisieren
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                
                # Backup erstellen
                with sqlite3.connect(backup_path) as backup_conn:
                    conn.backup(backup_conn)
                
                logger.info(f"Datenbank-Backup erstellt: {backup_path}")
                return backup_path
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
            raise

    def vacuum(self):
        """Führt VACUUM auf der Datenbank aus"""
        with self.get_connection() as conn:
            try:
                # Führe WAL-Checkpoint durch
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                
                # Führe VACUUM aus
                conn.execute("VACUUM")
                logger.info("Datenbank-VACUUM durchgeführt")
            except Exception as e:
                logger.error(f"Fehler beim VACUUM: {str(e)}")
                raise

    def check_integrity(self):
        """Überprüft die Datenbankintegrität"""
        with self.get_connection() as conn:
            try:
                # Führe WAL-Checkpoint durch
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                
                # Prüfe Integrität
                result = conn.execute("PRAGMA integrity_check").fetchone()
                if result[0] == "ok":
                    logger.info("Datenbankintegrität OK")
                    return True
                else:
                    logger.error(f"Datenbankintegritätsprüfung fehlgeschlagen: {result[0]}")
                    return False
            except Exception as e:
                logger.error(f"Fehler bei der Integritätsprüfung: {str(e)}")
                raise

    @classmethod
    def print_database_contents(cls):
        """Gibt den Inhalt aller Tabellen der Hauptdatenbank (inventory.db) zu Debugging-Zwecken aus.

        Listet Tabellen, Spalten und die ersten paar Zeilen jeder Tabelle auf.
        Passwörter werden aus Sicherheitsgründen zensiert.
        """
        logger.info("\n=== DATENBANK INHALTE ===")
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
                logger.info(f"\nTabelle: {table_name}")
                
                try:
                    # Hole alle Einträge
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    if not rows:
                        logger.info("  [LEER]")
                        continue
                    
                    # Hole Spaltennamen
                    columns = [description[0] for description in cursor.description]
                    logger.info(f"  Spalten: {', '.join(columns)}")
                    logger.info(f"  Anzahl Einträge: {len(rows)}")
                    
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
        if 'db' not in g:
            g.db = sqlite3.connect(Config.DATABASE)
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
                    s.value as name,
                    COUNT(w.id) as worker_count
                FROM settings s
                LEFT JOIN workers w ON w.department = s.value AND w.deleted = 0
                WHERE s.key LIKE 'department_%'
                AND s.value IS NOT NULL 
                AND s.value != ''
                GROUP BY s.value
                ORDER BY s.value
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
                    SELECT s.value as name,
                           COUNT(DISTINCT t.id) as tool_count,
                           COUNT(DISTINCT c.id) as consumable_count
                    FROM settings s
                    LEFT JOIN tools t ON t.location = s.value
                    LEFT JOIN consumables c ON c.location = s.value
                    WHERE s.key LIKE 'location_%'
                    AND s.value IS NOT NULL
                    AND s.value != ''
                    GROUP BY s.value
                    ORDER BY s.value
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Fehler beim Abrufen der Standorte: {e}")
            return []
    
    @classmethod
    def get_categories(cls, usage=None):
        """Gibt alle Kategorien mit der Anzahl der zugeordneten Werkzeuge und Verbrauchsmaterialien zurück"""
        try:
            # Basis-Query
            query = """
                SELECT 
                    s.value as name,
                    s.description as usage,
                    (SELECT COUNT(*) FROM tools WHERE category = s.value AND deleted = 0) as tools_count,
                    (SELECT COUNT(*) FROM consumables WHERE category = s.value AND deleted = 0) as consumables_count
                FROM settings s
                WHERE s.key LIKE 'category_%'
                AND s.key NOT LIKE '%_tools'
                AND s.key NOT LIKE '%_consumables'
                AND s.value IS NOT NULL 
                AND s.value != ''
            """
            
            query += " ORDER BY s.value"
            
            categories = cls.query(query)
            return [
                {
                    'name': cat['name'],
                    'usage': cat['usage'],
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

class BaseModel:
    """Basisklasse für alle Datenbankmodelle"""
    TABLE_NAME = None
    
    @classmethod
    def get_all_active(cls):
        """Gibt alle aktiven (nicht gelöschten) Einträge zurück"""
        return Database.query(f"SELECT * FROM {cls.TABLE_NAME} WHERE deleted = 0")
    
    @classmethod
    def get_by_id(cls, id):
        """Gibt einen Eintrag anhand seiner ID zurück"""
        return Database.query(
            f"SELECT * FROM {cls.TABLE_NAME} WHERE id = ? AND deleted = 0", 
            [id], 
            one=True
        )
    
    @classmethod
    def get_by_barcode(cls, barcode):
        """Gibt einen Eintrag anhand seines Barcodes zurück"""
        return Database.query(
            f"SELECT * FROM {cls.TABLE_NAME} WHERE barcode = ? AND deleted = 0", 
            [barcode], 
            one=True
        )

def init_db():
    """Initialisiert die Hauptdatenbank, falls sie leer ist oder Tabellen fehlen."""
    try:
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