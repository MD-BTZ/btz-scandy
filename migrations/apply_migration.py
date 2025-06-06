#!/usr/bin/env python3
"""
Script to apply database migrations for Scandy.
"""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

def get_db_path():
    """Get the path to the database file."""
    # Try to get the path from environment variable
    db_path = os.environ.get('SCANDY_DB_PATH')
    if db_path:
        return Path(db_path)
    
    # Default path
    base_dir = Path(__file__).parent.parent
    return base_dir / 'instance' / 'inventory.db'

def backup_database(db_path):
    """Create a backup of the database."""
    backup_dir = Path(db_path).parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f"inventory_backup_{timestamp}.db"
    
    print(f"Creating backup at: {backup_path}")
    with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
        dst.write(src.read())
    
    return backup_path

def get_db_version(conn):
    """Get the current database version."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    return cursor.fetchone()[0]

def apply_migration(conn, migration_file):
    """Apply a migration from a SQL file."""
    print(f"Applying migration: {migration_file}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    conn.executescript(sql_script)
    conn.commit()
    
    new_version = get_db_version(conn)
    print(f"Migration applied successfully. Database version: {new_version}")

def main():
    """Main function to run the migration."""
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        return 1
    
    print(f"Using database: {db_path}")
    
    # Create a backup
    try:
        backup_path = backup_database(db_path)
        print(f"Backup created at: {backup_path}")
    except Exception as e:
        print(f"Error creating backup: {e}")
        return 1
    
    # Apply migrations
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Get current version
        current_version = get_db_version(conn)
        print(f"Current database version: {current_version}")
        
        # Apply migrations based on current version
        if current_version < 2:
            migration_file = Path(__file__).parent / 'update_schema_20240605.sql'
            if migration_file.exists():
                apply_migration(conn, migration_file)
            else:
                print(f"Error: Migration file not found: {migration_file}")
                return 1
        else:
            print("Database is already up to date.")
        
        return 0
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    sys.exit(main())
