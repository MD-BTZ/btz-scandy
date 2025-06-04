import os
import sqlite3
import glob
import logging

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), '../migrations')

# Erwartete Tabellen und (optionale) Spalten
EXPECTED_TABLES = {
    'users': ['id', 'username', 'password_hash', 'role', 'created_at'],
    'settings': ['key', 'value'],
    'categories': ['id', 'name'],
    'locations': ['id', 'name'],
    'departments': ['id', 'name'],
    'tools': ['id', 'barcode', 'name'],
    'workers': ['id', 'barcode', 'firstname', 'lastname'],
    'consumables': ['id', 'barcode', 'name'],
    'lendings': ['id', 'tool_barcode', 'worker_barcode'],
    'consumable_usages': ['id', 'consumable_barcode', 'worker_barcode'],
    'tickets': ['id', 'title', 'created_by'],
    'ticket_notes': ['id', 'ticket_id', 'note'],
    'ticket_messages': ['id', 'ticket_id', 'message'],
    'ticket_history': ['id', 'ticket_id', 'field_name'],
    'bewerbungsvorlagen': ['id', 'name', 'dateiname', 'kategorie', 'erstellt_von'],
    'bewerbungsdokumente': ['id', 'vorlagen_id', 'name', 'dateipfad'],
    'bewerbungen': ['id', 'vorlagen_id', 'bewerber', 'status', 'erstellt_am'],
    'bewerbungsdokumente_uploads': ['id', 'bewerbung_id', 'dokument_id', 'dateipfad'],
    'schema_version': ['version'],
}

# Geschützte Tabellen, die nicht gelöscht werden dürfen
PROTECTED_TABLES = {'sqlite_sequence', 'sqlite_master', 'sqlite_temp_master'}

def apply_pending_migrations(db_path, migrations_dir=MIGRATIONS_DIR):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("SELECT MAX(version) FROM schema_version")
        current_version = cursor.fetchone()[0] or 0

        migration_files = sorted(glob.glob(os.path.join(migrations_dir, "migration_*.sql")))
        for migration_file in migration_files:
            version = int(os.path.basename(migration_file).split("_")[-1].split(".")[0])
            if version > current_version:
                with open(migration_file, "r") as f:
                    sql = f.read()
                    try:
                        cursor.executescript(sql)
                        logger.info(f"Migration {version} angewendet: {migration_file}")
                    except Exception as e:
                        logger.error(f"Fehler bei Migration {version} ({migration_file}): {e}")
                        break
        conn.commit()

def check_schema(db_path):
    missing_tables = []
    missing_columns = {}
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = set(row[0] for row in cursor.fetchall())
        
        # Überflüssige Tabellen löschen (außer geschützte)
        for table in tables:
            if table not in EXPECTED_TABLES and table not in PROTECTED_TABLES:
                logger.warning(f"Lösche überflüssige Tabelle: {table}")
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
        
        # Fehlende Tabellen anlegen
        for table, columns in EXPECTED_TABLES.items():
            if table not in tables:
                logger.warning(f"Lege fehlende Tabelle an: {table}")
                col_defs = ', '.join([f'{col} TEXT' for col in columns])
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({col_defs})")
            else:
                cursor.execute(f"PRAGMA table_info({table})")
                existing_cols = set(row[1] for row in cursor.fetchall())
                for col in columns:
                    if col not in existing_cols:
                        logger.warning(f"Füge fehlende Spalte {col} zu {table} hinzu")
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
        conn.commit()
    logger.info("Schema-Prüfung abgeschlossen: Überflüssige Tabellen entfernt, fehlende Tabellen/Spalten ergänzt.")

def auto_migrate_and_check(db_path):
    logger.info("Starte automatische Migration...")
    apply_pending_migrations(db_path)
    logger.info("Prüfe das Datenbankschema...")
    check_schema(db_path) 