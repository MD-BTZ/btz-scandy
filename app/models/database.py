from flask import g, current_app
import sqlite3
from datetime import datetime
import os
import logging
from app.config import Config
import json
from pathlib import Path
import shutil
import stat
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Union

# Optional requests importieren
try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class DatabaseError(Exception):
    """Basis-Exception für Datenbankfehler"""
    pass

class ConnectionError(DatabaseError):
    """Exception für Verbindungsfehler"""
    pass

class QueryError(DatabaseError):
    """Exception für Abfragefehler"""
    pass

class Database:
    """Zentrale Datenbankklasse für alle Datenbankoperationen"""
    
    _instance = None
    _db_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls, db_path: str):
        """Initialisiert die Datenbank mit dem angegebenen Pfad"""
        cls._db_path = db_path
        cls._ensure_db_dir()
        cls._check_and_fix_permissions()
    
    @classmethod
    def _ensure_db_dir(cls):
        """Stellt sicher, dass das Datenbankverzeichnis existiert"""
        if cls._db_path:
            db_dir = os.path.dirname(cls._db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir)
    
    @classmethod
    def _check_and_fix_permissions(cls):
        """Überprüft und korrigiert die Berechtigungen der Datenbankdatei"""
        if cls._db_path and os.path.exists(cls._db_path):
            try:
                # Setze Berechtigungen auf 644 (rw-r--r--)
                os.chmod(cls._db_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
            except Exception as e:
                logger.error(f"Fehler beim Setzen der Berechtigungen: {e}")
    
    @classmethod
    @contextmanager
    def get_db(cls):
        """Kontext-Manager für Datenbankverbindungen"""
        if not cls._db_path:
            raise ConnectionError("Datenbank nicht initialisiert")
            
        conn = None
        try:
            conn = sqlite3.connect(cls._db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            raise ConnectionError(f"Datenbankverbindungsfehler: {e}")
        finally:
            if conn:
                conn.close()
    
    @classmethod
    def query(cls, query: str, params: Optional[List] = None, one: bool = False) -> Union[List[Dict], Dict, None]:
        """Führt eine SQL-Abfrage aus und gibt die Ergebnisse zurück"""
        logger.debug(f"SQL QUERY: {query} - PARAMS: {params}")
        try:
            with current_app.app_context():
                with cls.get_db() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                        
                    if one:
                        result = cursor.fetchone()
                        logger.debug(f"QUERY RESULT: {result}")
                        return dict(result) if result else None
                    else:
                        result = [dict(row) for row in cursor.fetchall()]
                        logger.debug(f"QUERY RESULT: {result}")
                        return result
        except sqlite3.Error as e:
            logger.error(f"QUERY ERROR: {e}")
            raise QueryError(f"Abfragefehler: {e}")
    
    @classmethod
    def execute(cls, query: str, params: Optional[List] = None) -> int:
        """Führt eine SQL-Anweisung aus und gibt die Anzahl der betroffenen Zeilen zurück"""
        try:
            with current_app.app_context():
                with cls.get_db() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    conn.commit()
                    return cursor.rowcount
        except sqlite3.Error as e:
            raise QueryError(f"Ausführungsfehler: {e}")
    
    @classmethod
    def transaction(cls, queries: List[tuple]) -> bool:
        """Führt mehrere Abfragen in einer Transaktion aus"""
        try:
            with current_app.app_context():
                with cls.get_db() as conn:
                    cursor = conn.cursor()
                    for query, params in queries:
                        if params:
                            cursor.execute(query, params)
                        else:
                            cursor.execute(query)
                    conn.commit()
                    return True
        except sqlite3.Error as e:
            logger.error(f"Transaktionsfehler: {e}")
            return False
    
    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        """Holt einen Einstellungswert"""
        try:
            result = cls.query(
                "SELECT value FROM settings WHERE key = ?",
                [key],
                one=True
            )
            return result['value'] if result else default
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Einstellung {key}: {e}")
            return default
    
    @classmethod
    def set_setting(cls, key: str, value: Any, description: Optional[str] = None) -> bool:
        """Setzt einen Einstellungswert"""
        try:
            if description:
                cls.query(
                    """
                    INSERT OR REPLACE INTO settings (key, value, description, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                    """,
                    [key, str(value), description]
                )
            else:
                cls.query(
                    """
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, datetime('now'))
                    """,
                    [key, str(value)]
                )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Einstellung {key}: {e}")
            return False
    
    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """Holt alle Einstellungen"""
        try:
            settings = cls.query("SELECT key, value FROM settings")
            return {row['key']: row['value'] for row in settings}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen aller Einstellungen: {e}")
            return {}
    
    @classmethod
    def get_departments(cls) -> List[str]:
        """Holt alle Abteilungen"""
        try:
            departments = cls.query(
                """
                SELECT value 
                FROM settings 
                WHERE key LIKE 'department_%'
                AND value IS NOT NULL 
                AND value != ''
                ORDER BY value
                """
            )
            return [dept['value'] for dept in departments]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Abteilungen: {e}")
            return []
    
    @classmethod
    def add_department(cls, name: str) -> bool:
        """Fügt eine neue Abteilung hinzu"""
        try:
            # Nächste freie ID finden
            result = cls.query(
                """
                SELECT MAX(CAST(SUBSTR(key, 12) AS INTEGER)) as max_id 
                FROM settings 
                WHERE key LIKE 'department_%'
                """,
                one=True
            )
            next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
            
            # Neue Abteilung einfügen
            return cls.set_setting(f'department_{next_id}', name)
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Abteilung {name}: {e}")
            return False
    
    @classmethod
    def delete_department(cls, name: str) -> bool:
        """Löscht eine Abteilung"""
        try:
            cls.query(
                "DELETE FROM settings WHERE key LIKE 'department_%' AND value = ?",
                [name]
            )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Abteilung {name}: {e}")
            return False
    
    @classmethod
    def get_locations(cls) -> List[Dict[str, str]]:
        """Holt alle Standorte mit ihrer Verwendung"""
        try:
            locations = cls.query(
                """
                SELECT value as name, description as usage
                FROM settings
                WHERE key LIKE 'location_%'
                AND value IS NOT NULL
                AND value != ''
                ORDER BY value
                """
            )
            return [dict(loc) for loc in locations]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Standorte: {e}")
            return []
    
    @classmethod
    def add_location(cls, name: str, usage: str = 'both') -> bool:
        """Fügt einen neuen Standort hinzu"""
        try:
            # Nächste freie ID finden
            result = cls.query(
                """
                SELECT MAX(CAST(SUBSTR(key, 10) AS INTEGER)) as max_id 
                FROM settings 
                WHERE key LIKE 'location_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                """,
                one=True
            )
            next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
            
            # Neuen Standort einfügen
            return cls.set_setting(f'location_{next_id}', name, description=usage)
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Standorts {name}: {e}")
            return False
    
    @classmethod
    def delete_location(cls, name: str) -> bool:
        """Löscht einen Standort"""
        try:
            cls.query(
                "DELETE FROM settings WHERE key LIKE 'location_%' AND value = ?",
                [name]
            )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Standorts {name}: {e}")
            return False
    
    @classmethod
    def get_categories(cls) -> List[Dict[str, str]]:
        """Holt alle Kategorien mit ihrer Verwendung"""
        try:
            categories = cls.query(
                """
                SELECT value as name, description as usage
                FROM settings
                WHERE key LIKE 'category_%'
                AND value IS NOT NULL
                AND value != ''
                ORDER BY value
                """
            )
            return [dict(cat) for cat in categories]
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Kategorien: {e}")
            return []
    
    @classmethod
    def add_category(cls, name: str, usage: str = 'both') -> bool:
        """Fügt eine neue Kategorie hinzu"""
        try:
            # Nächste freie ID finden
            result = cls.query(
                """
                SELECT MAX(CAST(SUBSTR(key, 10) AS INTEGER)) as max_id 
                FROM settings 
                WHERE key LIKE 'category_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                """,
                one=True
            )
            next_id = 1 if not result or result['max_id'] is None else result['max_id'] + 1
            
            # Neue Kategorie einfügen
            return cls.set_setting(f'category_{next_id}', name, description=usage)
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Kategorie {name}: {e}")
            return False
    
    @classmethod
    def delete_category(cls, name: str) -> bool:
        """Löscht eine Kategorie"""
        try:
            cls.query(
                "DELETE FROM settings WHERE key LIKE 'category_%' AND value = ?",
                [name]
            )
            return True
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Kategorie {name}: {e}")
            return False
    
    @classmethod
    def update_category_usage(cls, name: str, usage: str) -> bool:
        """Aktualisiert die Verwendung einer Kategorie"""
        try:
            category_key = cls.query(
                """
                SELECT key FROM settings 
                WHERE key LIKE 'category_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                AND value = ?
                """,
                [name],
                one=True
            )
            
            if not category_key:
                return False
                
            base_key = category_key['key']
            
            # Aktualisiere die Kategorie und ihre Eigenschaften
            cls.query(
                """
                UPDATE settings 
                SET description = ?,
                    updated_at = datetime('now')
                WHERE key = ?
                """,
                [usage, base_key]
            )
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Kategorie {name}: {e}")
            return False
    
    @classmethod
    def update_location_usage(cls, name: str, usage: str) -> bool:
        """Aktualisiert die Verwendung eines Standorts"""
        try:
            location_key = cls.query(
                """
                SELECT key FROM settings 
                WHERE key LIKE 'location_%'
                AND key NOT LIKE '%_tools'
                AND key NOT LIKE '%_consumables'
                AND value = ?
                """,
                [name],
                one=True
            )
            
            if not location_key:
                return False
                
            base_key = location_key['key']
            
            # Aktualisiere den Standort und seine Eigenschaften
            cls.query(
                """
                UPDATE settings 
                SET description = ?,
                    updated_at = datetime('now')
                WHERE key = ?
                """,
                [usage, base_key]
            )
            
            return True
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Standorts {name}: {e}")
            return False
    
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
        logger.debug(f"SQL QUERY: {sql} - PARAMS: {params}")
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
                logger.info("Änderungen committed")
                
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
                logger.debug(f"QUERY RESULT: {result}")
                logger.debug(f"Number of results: {len([result] if one else result)}")
                logger.debug(f"Example record: {result if one else result[0]}")
            else:
                logger.debug("No results returned")
                
            return result
            
        except Exception as e:
            logger.error(f"QUERY ERROR: {e}")
            logger.error(f"Query: {sql}")
            logger.error(f"Parameters: {params}")
            raise
    
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
    
    @classmethod
    def close_connection(cls):
        """Schließt die aktuelle Datenbankverbindung"""
        if hasattr(g, 'db'):
            try:
                g.db.close()
                delattr(g, 'db')
            except Exception as e:
                logger.error(f"Fehler beim Schließen der Datenbankverbindung: {str(e)}")
    
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

    @staticmethod
    def set_setting(key, value):
        """Setzt einen Einstellungswert in der Datenbank"""
        try:
            with Database.get_db() as db:
                db.execute(
                    '''
                    INSERT OR REPLACE INTO settings (key, value) 
                    VALUES (?, ?)
                    ''',
                    [key, value]
                )
                db.commit()
                return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Einstellung {key}: {e}")
            return False

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