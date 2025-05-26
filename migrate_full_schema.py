import sqlite3
import os

# Soll-Schema für inventory.db
INVENTORY_SCHEMA = {
    "tools": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("barcode", "TEXT NOT NULL UNIQUE"),
        ("name", "TEXT NOT NULL"),
        ("description", "TEXT"),
        ("status", "TEXT DEFAULT 'verfügbar'"),
        ("category", "TEXT"),
        ("location", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("deleted", "INTEGER DEFAULT 0"),
        ("deleted_at", "TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP")
    ],
    "workers": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("barcode", "TEXT NOT NULL UNIQUE"),
        ("firstname", "TEXT NOT NULL"),
        ("lastname", "TEXT NOT NULL"),
        ("department", "TEXT"),
        ("email", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("deleted", "INTEGER DEFAULT 0"),
        ("deleted_at", "TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP")
    ],
    "consumables": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("barcode", "TEXT NOT NULL UNIQUE"),
        ("name", "TEXT NOT NULL"),
        ("description", "TEXT"),
        ("quantity", "INTEGER DEFAULT 0"),
        ("category", "TEXT"),
        ("location", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("deleted", "INTEGER DEFAULT 0"),
        ("deleted_at", "TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP")
    ],
    "lendings": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("tool_barcode", "TEXT NOT NULL"),
        ("worker_barcode", "TEXT NOT NULL"),
        ("lent_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("returned_at", "TIMESTAMP"),
        ("notes", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "consumable_usages": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("consumable_barcode", "TEXT NOT NULL"),
        ("worker_barcode", "TEXT NOT NULL"),
        ("quantity", "INTEGER NOT NULL"),
        ("used_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "settings": [
        ("key", "TEXT PRIMARY KEY"),
        ("value", "TEXT"),
        ("description", "TEXT")
    ],
    "history": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("action", "TEXT NOT NULL"),
        ("item_type", "TEXT NOT NULL"),
        ("item_id", "TEXT NOT NULL"),
        ("user_id", "INTEGER"),
        ("details", "TEXT"),
        ("timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "tool_status_changes": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("tool_barcode", "TEXT NOT NULL"),
        ("old_status", "TEXT NOT NULL"),
        ("new_status", "TEXT NOT NULL"),
        ("reason", "TEXT"),
        ("changed_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "access_settings": [
        ("route", "TEXT PRIMARY KEY"),
        ("is_public", "BOOLEAN DEFAULT 0"),
        ("description", "TEXT")
    ],
    "consumable_lendings": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("consumable_barcode", "TEXT NOT NULL"),
        ("worker_barcode", "TEXT NOT NULL"),
        ("quantity", "INTEGER NOT NULL"),
        ("lending_time", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("return_time", "TIMESTAMP")
    ],
    "departments": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT UNIQUE NOT NULL"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("deleted", "INTEGER DEFAULT 0"),
        ("deleted_at", "TIMESTAMP")
    ],
    "homepage_notices": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("title", "TEXT NOT NULL"),
        ("content", "TEXT NOT NULL"),
        ("priority", "INTEGER DEFAULT 0"),
        ("is_active", "BOOLEAN DEFAULT 1"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("created_by", "INTEGER")
    ]
}

TICKETS_SCHEMA = {
    "schema_version": [
        ("version", "INTEGER PRIMARY KEY"),
        ("applied_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "users": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("username", "TEXT UNIQUE NOT NULL"),
        ("password_hash", "TEXT NOT NULL"),
        ("email", "TEXT"),
        ("firstname", "TEXT"),
        ("lastname", "TEXT"),
        ("role", "TEXT NOT NULL DEFAULT 'user'"),
        ("is_active", "BOOLEAN DEFAULT 1"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("last_login", "TIMESTAMP")
    ],
    "settings": [
        ("key", "TEXT PRIMARY KEY"),
        ("value", "TEXT NOT NULL"),
        ("description", "TEXT"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "categories": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT UNIQUE NOT NULL"),
        ("description", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "ticket_categories": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT NOT NULL UNIQUE")
    ],
    "locations": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT UNIQUE NOT NULL"),
        ("description", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "departments": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("name", "TEXT UNIQUE NOT NULL"),
        ("description", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("deleted", "INTEGER DEFAULT 0"),
        ("deleted_at", "TIMESTAMP")
    ],
    "tools": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("barcode", "TEXT NOT NULL UNIQUE"),
        ("name", "TEXT NOT NULL"),
        ("description", "TEXT"),
        ("status", "TEXT DEFAULT 'verfügbar'"),
        ("category", "TEXT"),
        ("location", "TEXT"),
        ("last_maintenance", "DATE"),
        ("next_maintenance", "DATE"),
        ("maintenance_interval", "INTEGER"),
        ("last_checked", "TIMESTAMP"),
        ("supplier", "TEXT"),
        ("reorder_point", "INTEGER"),
        ("notes", "TEXT"),
        ("deleted", "BOOLEAN DEFAULT 0"),
        ("deleted_at", "TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "workers": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("barcode", "TEXT NOT NULL UNIQUE"),
        ("firstname", "TEXT NOT NULL"),
        ("lastname", "TEXT NOT NULL"),
        ("department", "TEXT"),
        ("email", "TEXT"),
        ("phone", "TEXT"),
        ("notes", "TEXT"),
        ("deleted", "BOOLEAN DEFAULT 0"),
        ("deleted_at", "TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "consumables": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("barcode", "TEXT NOT NULL UNIQUE"),
        ("name", "TEXT NOT NULL"),
        ("description", "TEXT"),
        ("quantity", "INTEGER DEFAULT 0"),
        ("min_quantity", "INTEGER DEFAULT 0"),
        ("category", "TEXT"),
        ("location", "TEXT"),
        ("unit", "TEXT"),
        ("supplier", "TEXT"),
        ("reorder_point", "INTEGER"),
        ("notes", "TEXT"),
        ("deleted", "BOOLEAN DEFAULT 0"),
        ("deleted_at", "TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "lendings": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("tool_barcode", "TEXT NOT NULL"),
        ("worker_barcode", "TEXT NOT NULL"),
        ("lent_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("returned_at", "TIMESTAMP"),
        ("notes", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "consumable_usages": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("consumable_barcode", "TEXT NOT NULL"),
        ("worker_barcode", "TEXT NOT NULL"),
        ("quantity", "INTEGER NOT NULL"),
        ("used_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("sync_status", "TEXT DEFAULT 'pending'"),
        ("modified_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "tickets": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("title", "TEXT NOT NULL"),
        ("description", "TEXT NOT NULL"),
        ("status", "TEXT DEFAULT 'offen'"),
        ("priority", "TEXT DEFAULT 'normal'"),
        ("created_by", "TEXT NOT NULL"),
        ("assigned_to", "TEXT"),
        ("category", "TEXT"),
        ("due_date", "TIMESTAMP"),
        ("estimated_time", "INTEGER"),
        ("actual_time", "INTEGER"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("resolved_at", "TIMESTAMP"),
        ("resolution_notes", "TEXT"),
        ("response", "TEXT"),
        ("last_modified_by", "TEXT"),
        ("last_modified_at", "TIMESTAMP")
    ],
    "auftrag_details": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("ticket_id", "INTEGER NOT NULL"),
        ("auftrag_an", "TEXT"),
        ("bereich", "TEXT"),
        ("auftraggeber_intern", "BOOLEAN DEFAULT 1"),
        ("auftraggeber_extern", "BOOLEAN DEFAULT 0"),
        ("auftraggeber_name", "TEXT"),
        ("kontakt", "TEXT"),
        ("auftragsbeschreibung", "TEXT"),
        ("ausgefuehrte_arbeiten", "TEXT"),
        ("arbeitsstunden", "REAL"),
        ("leistungskategorie", "TEXT"),
        ("fertigstellungstermin", "TEXT"),
        ("gesamtsumme", "REAL DEFAULT 0"),
        ("erstellt_am", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "auftrag_material": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("ticket_id", "INTEGER NOT NULL"),
        ("material", "TEXT"),
        ("menge", "REAL"),
        ("einzelpreis", "REAL")
    ],
    "ticket_notes": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("ticket_id", "INTEGER NOT NULL"),
        ("note", "TEXT NOT NULL"),
        ("created_by", "TEXT NOT NULL"),
        ("is_private", "BOOLEAN DEFAULT 0"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "ticket_messages": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("ticket_id", "INTEGER NOT NULL"),
        ("message", "TEXT NOT NULL"),
        ("sender", "TEXT NOT NULL"),
        ("is_admin", "BOOLEAN DEFAULT 0"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ],
    "ticket_history": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("ticket_id", "INTEGER NOT NULL"),
        ("field_name", "TEXT NOT NULL"),
        ("old_value", "TEXT"),
        ("new_value", "TEXT"),
        ("changed_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("changed_by", "TEXT NOT NULL")
    ],
    "system_logs": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("level", "TEXT NOT NULL"),
        ("message", "TEXT NOT NULL"),
        ("details", "TEXT")
    ],
    "access_settings": [
        ("route", "TEXT PRIMARY KEY"),
        ("is_public", "BOOLEAN DEFAULT 0"),
        ("description", "TEXT")
    ],
    "timesheets": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("user_id", "INTEGER NOT NULL"),
        ("year", "INTEGER NOT NULL"),
        ("kw", "INTEGER NOT NULL"),
        ("montag_start", "TEXT"),
        ("montag_end", "TEXT"),
        ("montag_tasks", "TEXT"),
        ("dienstag_start", "TEXT"),
        ("dienstag_end", "TEXT"),
        ("dienstag_tasks", "TEXT"),
        ("mittwoch_start", "TEXT"),
        ("mittwoch_end", "TEXT"),
        ("mittwoch_tasks", "TEXT"),
        ("donnerstag_start", "TEXT"),
        ("donnerstag_end", "TEXT"),
        ("donnerstag_tasks", "TEXT"),
        ("freitag_start", "TEXT"),
        ("freitag_end", "TEXT"),
        ("freitag_tasks", "TEXT"),
        ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]
}

def ensure_table(conn, table, columns):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if not cursor.fetchone():
        col_defs = ", ".join([f"{col} {typ}" for col, typ in columns])
        cursor.execute(f"CREATE TABLE {table} ({col_defs})")
        print(f"Tabelle {table} wurde neu angelegt.")
    else:
        cursor.execute(f"PRAGMA table_info({table})")
        existing_cols = {row[1]: row[2] for row in cursor.fetchall()}
        for col, typ in columns:
            if col not in existing_cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
                print(f"Spalte {col} zu {table} hinzugefügt.")
            elif typ.split()[0] not in existing_cols[col]:
                print(f"WARNUNG: Spalte {col} in {table} hat Typ {existing_cols[col]}, erwartet: {typ}")

def migrate_full_schema(db_path, schema):
    if not os.path.exists(db_path):
        print(f"Datei {db_path} nicht gefunden!")
        return
    conn = sqlite3.connect(db_path)
    for table, columns in schema.items():
        ensure_table(conn, table, columns)
    conn.commit()
    conn.close()
    print(f"Schema-Migration für {db_path} abgeschlossen.")

if __name__ == "__main__":
    migrate_full_schema("app/database/inventory.db", INVENTORY_SCHEMA)
    migrate_full_schema("app/database/tickets.db", TICKETS_SCHEMA) 