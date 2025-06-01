import sqlite3
import logging
from werkzeug.security import generate_password_hash
import os
import time

logger = logging.getLogger(__name__)

# Die Schema-Version, die die aktuelle Codebasis erwartet
CURRENT_SCHEMA_VERSION = 5

def get_db_connection(db_path, timeout=30):
    """Erstellt eine Datenbankverbindung mit Timeout."""
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_db_schema_version(conn):
    """Liest die Schema-Version aus der settings-Tabelle."""
    try:
        cursor = conn.cursor()
        # Zuerst prüfen wir die schema_version Tabelle
        cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        result = cursor.fetchone()
        if result and str(result[0]).strip().isdigit():
            return int(result[0])
        # Wenn keine schema_version Tabelle existiert, prüfen wir die settings Tabelle
        cursor.execute("SELECT value FROM settings WHERE key = 'schema_version'")
        result = cursor.fetchone()
        if result and str(result[0]).strip().isdigit():
            return int(result[0])
        # Wenn kein Eintrag existiert, prüfen wir, ob die users-Tabelle existiert
        try:
            cursor.execute("SELECT 1 FROM users LIMIT 1")
            logger.warning("Kein Schema-Versionseintrag gefunden, aber 'users'-Tabelle existiert. Nehme Version 2 an.")
            return 2
        except sqlite3.OperationalError:
            logger.warning("Kein Schema-Versionseintrag und keine 'users'-Tabelle gefunden. Nehme Version 1 an.")
            return 1
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Schema-Version: {e}. Nehme Version 1 an.")
        return 1

def set_db_schema_version(conn, version):
    """Schreibt die Schema-Version in beide Tabellen."""
    try:
        cursor = conn.cursor()
        
        # In settings Tabelle
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                       ['schema_version', str(version)])
                      
        # In schema_version Tabelle
        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                      [version])
                      
        logger.info(f"Datenbank Schema-Version auf {version} gesetzt.")
    except Exception as e:
        logger.error(f"Fehler beim Setzen der Schema-Version auf {version}: {e}")
        raise

def _migrate_v1_to_v2(conn):
    """Migration von Schema-Version 1 auf 2. Fügt users und homepage_notices hinzu."""
    logger.info("Führe Migration von Schema v1 auf v2 durch...")
    cursor = conn.cursor()

    try:
        # 1. Users-Tabelle erstellen (IF NOT EXISTS ist sicher)
        logger.info("Erstelle 'users'-Tabelle (falls nicht vorhanden)...")
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'mitarbeiter', 'anwender')),
            is_active INTEGER DEFAULT 1
        )''')

        # 2. Homepage Notices Tabelle erstellen (IF NOT EXISTS ist sicher)
        logger.info("Erstelle 'homepage_notices'-Tabelle (falls nicht vorhanden)...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS homepage_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 4. Initiale Hinweise einfügen (nur wenn Tabelle leer war/ist)
        cursor.execute('SELECT COUNT(*) FROM homepage_notices')
        if cursor.fetchone()[0] == 0:
            logger.info("Füge Standard-Hinweise hinzu...")
            cursor.execute('''
                INSERT INTO homepage_notices (title, content, priority)
                VALUES
                    ('Willkommen', 'Willkommen im Scandy-System. Hier können Sie Werkzeuge und Verbrauchsmaterialien verwalten.', 1),
                    ('Hinweis', 'Bitte melden Sie sich an, um das System zu nutzen.', 2)
            ''')
        else:
            logger.info("'homepage_notices'-Tabelle ist nicht leer, überspringe das Hinzufügen von Standard-Hinweisen.")

        # 5. Schema-Version aktualisieren
        set_db_schema_version(conn, 2)

        logger.info("Migration von v1 auf v2 erfolgreich abgeschlossen.")
        return True

    except Exception as e:
        logger.error(f"Fehler während der Migration von v1 auf v2: {e}", exc_info=True)
        return False

def _migrate_v2_to_v3(conn):
    """Migration von Schema-Version 2 auf 3. Aktualisiert die description für Kategorien und Standorte."""
    logger.info("Führe Migration von Schema v2 auf v3 durch...")
    cursor = conn.cursor()

    try:
        # Aktualisiere die description für bestehende Kategorien
        cursor.execute('''
            UPDATE settings 
            SET description = 'both'
            WHERE key LIKE 'category_%'
            AND key NOT LIKE '%_tools'
            AND key NOT LIKE '%_consumables'
            AND description IS NULL
        ''')

        # Aktualisiere die description für bestehende Standorte
        cursor.execute('''
            UPDATE settings 
            SET description = 'both'
            WHERE key LIKE 'location_%'
            AND key NOT LIKE '%_tools'
            AND key NOT LIKE '%_consumables'
            AND description IS NULL
        ''')

        # Füge die neue Schema-Version hinzu
        cursor.execute('''
            INSERT INTO schema_version (version)
            VALUES (3)
        ''')

        conn.commit()
        logger.info("Migration von Schema v2 auf v3 erfolgreich abgeschlossen.")
    except Exception as e:
        logger.error(f"Fehler bei der Migration von Schema v2 auf v3: {e}")
        conn.rollback()
        raise

def _migrate_v3_to_v4(conn):
    """Migration von Version 3 auf Version 4"""
    try:
        cursor = conn.cursor()
        
        # Prüfe ob die alte Tabelle existiert
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consumable_usage'")
        if cursor.fetchone():
            # Benenne die Tabelle um
            cursor.execute("ALTER TABLE consumable_usage RENAME TO consumable_usages")
            logger.info("Tabelle consumable_usage zu consumable_usages umbenannt")
        
        # Füge modified_at Spalte hinzu, falls sie noch nicht existiert
        try:
            cursor.execute('ALTER TABLE consumable_usages ADD COLUMN modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            cursor.execute('UPDATE consumable_usages SET modified_at = used_at WHERE modified_at IS NULL')
            logger.info("modified_at Spalte zur consumable_usages Tabelle hinzugefügt")
        except Exception as e:
            logger.info(f"modified_at Spalte existiert bereits oder konnte nicht hinzugefügt werden: {e}")
        
        # Aktualisiere die Schema-Version
        set_db_schema_version(conn, 4)
        logger.info("Schema-Version auf 4 aktualisiert")
        
        return True
    except Exception as e:
        logger.error(f"Fehler bei Migration v3->v4: {e}")
        return False

def _migrate_v4_to_v5(conn):
    """Migration von Version 4 auf Version 5 - Fügt Bewerbungstabellen hinzu"""
    try:
        cursor = conn.cursor()
        
        # Erstelle application_templates Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_templates (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                template_content TEXT NOT NULL,
                category TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users(username)
            )
        """)

        # Erstelle application_document_templates Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_document_templates (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                description TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users(username)
            )
        """)

        # Erstelle applications Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY,
                template_id INTEGER NOT NULL,
                company_name TEXT NOT NULL,
                position TEXT NOT NULL,
                contact_person TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                address TEXT,
                generated_content TEXT NOT NULL,
                status TEXT DEFAULT 'erstellt',
                sent_at TIMESTAMP,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (template_id) REFERENCES application_templates(id),
                FOREIGN KEY (created_by) REFERENCES users(username)
            )
        """)

        # Erstelle application_documents Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_documents (
                id INTEGER PRIMARY KEY,
                application_id INTEGER NOT NULL,
                document_template_id INTEGER,
                document_type TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id),
                FOREIGN KEY (document_template_id) REFERENCES application_document_templates(id)
            )
        """)

        # Erstelle application_responses Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_responses (
                id INTEGER PRIMARY KEY,
                application_id INTEGER NOT NULL,
                response_type TEXT NOT NULL,
                response_date TIMESTAMP,
                response_content TEXT,
                next_steps TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES applications(id)
            )
        """)

        # Erstelle application_template_placeholders Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_template_placeholders (
                id INTEGER PRIMARY KEY,
                template_id INTEGER NOT NULL,
                placeholder_name TEXT NOT NULL,
                description TEXT NOT NULL,
                example_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES application_templates(id)
            )
        """)
        
        # Aktualisiere die Schema-Version
        set_db_schema_version(conn, 5)
        logger.info("Schema-Version auf 5 aktualisiert")
        
        return True
    except Exception as e:
        logger.error(f"Fehler bei Migration v4->v5: {e}")
        return False

def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def _migrate_ticket_db(conn):
    """Führt die Migrationen für die Ticket-Datenbank durch."""
    db_path = os.path.join(current_app.root_path, 'database', 'tickets.db')
    logging.info(f"Verwendeter Ticket-Datenbankpfad: {db_path}")
    
    # Korrigiere Berechtigungen
    logging.info(f"Korrigiere Berechtigungen für {db_path}")
    _fix_permissions(db_path)
    logging.info("Berechtigungen erfolgreich korrigiert")
    
    with sqlite3.connect(db_path) as db:
        # Erstelle schema_version Tabelle falls nicht vorhanden
        db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Hole aktuelle Version
        current_version = db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
        
        # Führe Migrationen durch
        if current_version < 1:
            # Erstelle users Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    firstname TEXT,
                    lastname TEXT,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # Erstelle settings Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Erstelle categories Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Erstelle ticket_categories Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
            """)
            
            # Erstelle locations Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Erstelle departments Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP
                )
            """)
            
            # Erstelle tools Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY,
                    barcode TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'verfügbar',
                    category TEXT,
                    location TEXT,
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
            """)
            
            # Erstelle workers Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY,
                    barcode TEXT NOT NULL UNIQUE,
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
            """)
            
            # Erstelle consumables Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS consumables (
                    id INTEGER PRIMARY KEY,
                    barcode TEXT NOT NULL UNIQUE,
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
            """)
            
            # Erstelle lendings Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS lendings (
                    id INTEGER PRIMARY KEY,
                    tool_barcode TEXT NOT NULL,
                    worker_barcode TEXT NOT NULL,
                    lent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    returned_at TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode),
                    FOREIGN KEY (tool_barcode) REFERENCES tools(barcode)
                )
            """)
            
            # Erstelle consumable_usages Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS consumable_usages (
                    id INTEGER PRIMARY KEY,
                    consumable_barcode TEXT NOT NULL,
                    worker_barcode TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_status TEXT DEFAULT 'pending',
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode),
                    FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode)
                )
            """)
            
            # Erstelle tickets Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'offen',
                    priority TEXT DEFAULT 'normal',
                    created_by TEXT NOT NULL,
                    assigned_to TEXT,
                    category TEXT,
                    due_date TIMESTAMP,
                    estimated_time INTEGER,
                    actual_time INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    resolution_notes TEXT,
                    response TEXT,
                    last_modified_by TEXT,
                    last_modified_at TIMESTAMP,
                    FOREIGN KEY (last_modified_by) REFERENCES users(username),
                    FOREIGN KEY (assigned_to) REFERENCES users(username),
                    FOREIGN KEY (created_by) REFERENCES users(username)
                )
            """)
            
            # Erstelle auftrag_details Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS auftrag_details (
                    id INTEGER PRIMARY KEY,
                    ticket_id INTEGER NOT NULL,
                    auftrag_an TEXT,
                    bereich TEXT,
                    auftraggeber_intern BOOLEAN DEFAULT 1,
                    auftraggeber_extern BOOLEAN DEFAULT 0,
                    auftraggeber_name TEXT,
                    kontakt TEXT,
                    auftragsbeschreibung TEXT,
                    ausgefuehrte_arbeiten TEXT,
                    arbeitsstunden REAL,
                    leistungskategorie TEXT,
                    fertigstellungstermin TEXT,
                    gesamtsumme REAL DEFAULT 0,
                    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            """)
            
            # Erstelle auftrag_material Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS auftrag_material (
                    id INTEGER PRIMARY KEY,
                    ticket_id INTEGER NOT NULL,
                    material TEXT,
                    menge REAL,
                    einzelpreis REAL,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            """)
            
            # Erstelle ticket_notes Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_notes (
                    id INTEGER PRIMARY KEY,
                    ticket_id INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    is_private BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(username),
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            """)
            
            # Erstelle ticket_messages Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id INTEGER PRIMARY KEY,
                    ticket_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender) REFERENCES users(username),
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            """)
            
            # Erstelle ticket_history Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS ticket_history (
                    id INTEGER PRIMARY KEY,
                    ticket_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    changed_by TEXT NOT NULL,
                    FOREIGN KEY (changed_by) REFERENCES users(username),
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
                )
            """)
            
            # Erstelle system_logs Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT
                )
            """)
            
            # Erstelle access_settings Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS access_settings (
                    route TEXT PRIMARY KEY,
                    is_public BOOLEAN DEFAULT 0,
                    description TEXT
                )
            """)
            
            # Erstelle timesheets Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS timesheets (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    kw INTEGER NOT NULL,
                    montag_start TEXT,
                    montag_end TEXT,
                    montag_tasks TEXT,
                    dienstag_start TEXT,
                    dienstag_end TEXT,
                    dienstag_tasks TEXT,
                    mittwoch_start TEXT,
                    mittwoch_end TEXT,
                    mittwoch_tasks TEXT,
                    donnerstag_start TEXT,
                    donnerstag_end TEXT,
                    donnerstag_tasks TEXT,
                    freitag_start TEXT,
                    freitag_end TEXT,
                    freitag_tasks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Erstelle application_templates Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS application_templates (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    template_content TEXT NOT NULL,
                    category TEXT,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (created_by) REFERENCES users(username)
                )
            """)

            # Erstelle applications Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY,
                    template_id INTEGER NOT NULL,
                    company_name TEXT NOT NULL,
                    position TEXT NOT NULL,
                    contact_person TEXT,
                    contact_email TEXT,
                    contact_phone TEXT,
                    address TEXT,
                    generated_content TEXT NOT NULL,
                    custom_block TEXT,
                    status TEXT DEFAULT 'erstellt',
                    sent_at TIMESTAMP,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (template_id) REFERENCES application_templates(id),
                    FOREIGN KEY (created_by) REFERENCES users(username)
                )
            """)

            # Erstelle application_documents Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS application_documents (
                    id INTEGER PRIMARY KEY,
                    application_id INTEGER NOT NULL,
                    document_type TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES applications(id)
                )
            """)

            # Erstelle application_responses Tabelle
            db.execute("""
                CREATE TABLE IF NOT EXISTS application_responses (
                    id INTEGER PRIMARY KEY,
                    application_id INTEGER NOT NULL,
                    response_type TEXT NOT NULL,
                    response_date TIMESTAMP,
                    response_content TEXT,
                    next_steps TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (application_id) REFERENCES applications(id)
                )
            """)
            
            # Aktualisiere Version
            db.execute("INSERT INTO schema_version (version) VALUES (1)")
            db.commit()
            logging.info("Schema-Migration für {} abgeschlossen.".format(db_path))

def run_migrations(db_path):
    """Führt alle notwendigen Migrationen für die Ticket-Datenbank durch"""
    try:
        logger.info(f"Starte Migration für {db_path}")
        
        # Prüfe ob die Datenbank existiert
        if not os.path.exists(db_path):
            logger.info("Datenbank existiert nicht, erstelle neue Datenbank")
            _migrate_ticket_db(db_path)
            return
            
        # Hole aktuelle Schema-Version
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(version) FROM schema_version")
            current_version = cursor.fetchone()[0] or 0
            logger.info(f"Aktuelle Schema-Version: {current_version}")
            
        # Führe Migrationen basierend auf Version durch
        if current_version < 1:
            logger.info("Führe Migration von v1 zu v2 durch")
            _migrate_v1_to_v2(db_path)
        if current_version < 2:
            logger.info("Führe Migration von v2 zu v3 durch")
            _migrate_v2_to_v3(db_path)
        if current_version < 3:
            logger.info("Führe Migration von v3 zu v4 durch")
            _migrate_v3_to_v4(db_path)
        if current_version < 4:
            logger.info("Führe Migration von v4 zu v5 durch")
            _migrate_v4_to_v5(db_path)
            
        logger.info("Migration erfolgreich abgeschlossen")
        
    except Exception as e:
        logger.error(f"Fehler bei der Migration: {str(e)}")
        raise

def run_ticket_db_migrations(ticket_db_path):
    """Führt Migrationen für die Ticket-Datenbank durch."""
    logger.info(f"Prüfe Ticket-Datenbank-Migrationen für: {ticket_db_path}")
    if not os.path.exists(ticket_db_path):
        logger.warning(f"Ticket-Datenbankdatei {ticket_db_path} existiert nicht. Migrationen werden übersprungen (wird neu erstellt).")
        return

    conn = None
    max_retries = 3
    retry_delay = 1  # Sekunden

    for attempt in range(max_retries):
        try:
            conn = get_db_connection(ticket_db_path)
            if not _migrate_ticket_db(conn):
                raise Exception("Ticket-Datenbank-Migration fehlgeschlagen!")
            break  # Erfolgreich, keine weiteren Versuche nötig

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"Ticket-Datenbank ist gesperrt. Versuche {attempt + 1} von {max_retries}...")
                    time.sleep(retry_delay)
                    continue
            logger.error(f"Fehler bei der Ticket-Datenbank-Migration: {str(e)}")
            raise
        finally:
            if conn:
                conn.close() 