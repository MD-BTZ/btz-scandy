import sqlite3

# Dateinamen anpassen!
OLD_DB = "app/database/inventory.db.bak_20250508_155331"
NEW_DB = "app/database/inventory.db"

def get_table_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]

def get_tables(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return [row[0] for row in cursor.fetchall()]

def migrate_table(old_cur, new_cur, table):
    old_cols = get_table_columns(old_cur, table)
    new_cols = get_table_columns(new_cur, table)
    common_cols = [col for col in old_cols if col in new_cols and col != 'id']  # id wird neu vergeben

    if not common_cols:
        print(f"Überspringe Tabelle {table} (keine gemeinsamen Spalten)")
        return

    print(f"Migriere Tabelle {table}: gemeinsame Spalten: {common_cols}")

    old_cur.execute(f"SELECT {', '.join(common_cols)} FROM {table}")
    rows = old_cur.fetchall()
    if not rows:
        print(f"Keine Daten in {table}")
        return

    placeholders = ','.join(['?'] * len(common_cols))
    insert_sql = f"INSERT OR IGNORE INTO {table} ({', '.join(common_cols)}) VALUES ({placeholders})"
    new_cur.executemany(insert_sql, rows)
    print(f"{len(rows)} Zeilen in {table} importiert.")

def main():
    old_conn = sqlite3.connect(OLD_DB)
    new_conn = sqlite3.connect(NEW_DB)
    old_cur = old_conn.cursor()
    new_cur = new_conn.cursor()

    old_tables = set(get_tables(old_cur))
    new_tables = set(get_tables(new_cur))
    tables_to_migrate = old_tables & new_tables

    for table in tables_to_migrate:
        if table in ["sqlite_sequence", "schema_version", "sync_status"]:
            continue  # Diese Tabellen nicht migrieren
        migrate_table(old_cur, new_cur, table)
        new_conn.commit()

    old_conn.close()
    new_conn.close()
    print("Migration abgeschlossen!")

if __name__ == "__main__":
    main() 