# Database Migrations

This directory contains database migration scripts for the Scandy application.

## Available Migrations

### update_schema_20240605.sql
- Updates the database schema to version 2
- Adds new columns for sync status and timestamps
- Creates necessary indexes for better performance
- Ensures foreign key constraints are properly set

## How to Run Migrations

1. **Backup your database** (recommended):
   ```bash
   cp instance/inventory.db instance/backups/inventory_backup_$(date +%Y%m%d_%H%M%S).db
   ```

2. **Run the migration script**:
   ```bash
   python migrations/apply_migration.py
   ```

   You can also specify a custom database path:
   ```bash
   SCANDY_DB_PATH=/path/to/your/database.db python migrations/apply_migration.py
   ```

3. **Verify the migration**:
   - The script will print the current database version before and after applying migrations
   - Check the logs for any errors

## Database Versioning

The database version is stored in the `user_version` PRAGMA. You can check it with:

```sql
PRAGMA user_version;
```

## Rollback

If you need to rollback a migration:

1. Restore from the backup created by the migration script
2. The backup is stored in `instance/backups/` with a timestamp

## Adding New Migrations

1. Create a new SQL file with a descriptive name and date (e.g., `update_schema_YYYYMMDD.sql`)
2. Update the version number in the SQL file using `PRAGMA user_version = X`
3. Update the `apply_migration.py` script to handle the new version
4. Test the migration on a backup of your production database
5. Document the changes in this README
