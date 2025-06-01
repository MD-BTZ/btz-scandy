import sqlite3
import logging
from pathlib import Path
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class SchemaValidator:
    def __init__(self, db_path, schema_file):
        self.db_path = db_path
        self.schema_file = schema_file
        self.schema = self._load_schema()
        
    def _load_schema(self):
        """Lädt das Schema aus der Schema-Datei"""
        schema = {}
        current_table = None
        in_columns = False
        
        with open(self.schema_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Neue Tabelle gefunden
                if line.startswith('Tabelle:'):
                    current_table = line.split(':', 1)[1].strip()
                    schema[current_table] = {
                        'columns': [],
                        'indices': [],
                        'foreign_keys': []
                    }
                    in_columns = False
                
                # Spalten-Bereich gefunden
                elif line == 'Spalten:' and current_table:
                    in_columns = True
                    continue
                
                # Spalten gefunden
                elif line.startswith('  - ') and current_table and in_columns:
                    # Extrahiere Spaltenname und Definition
                    col_def = line.strip('- ').strip()
                    if '(' in col_def:
                        name = col_def.split('(')[0].strip()
                        type_info = col_def[col_def.find('(')+1:col_def.rfind(')')].strip()
                        
                        # Extrahiere Typ und Constraints
                        type_parts = type_info.split()
                        col_type = type_parts[0]
                        
                        column = {
                            'name': name,
                            'type': col_type,
                            'primary_key': 'PRIMARY KEY' in type_info,
                            'not_null': 'NOT NULL' in type_info
                        }
                        
                        # Extrahiere DEFAULT-Wert
                        if 'DEFAULT' in type_info:
                            default_start = type_info.find('DEFAULT') + 7
                            column['default'] = type_info[default_start:].strip()
                        
                        schema[current_table]['columns'].append(column)
                
                # Indizes gefunden
                elif line == 'Indizes:' and current_table:
                    in_columns = False
                    continue
                elif line.startswith('  - ') and current_table and not in_columns and 'idx_' in line:
                    schema[current_table]['indices'].append(line.strip('- ').strip())
                
                # Foreign Keys gefunden
                elif line == 'Foreign Keys:' and current_table:
                    in_columns = False
                    continue
                elif line.startswith('  - ') and current_table and not in_columns and '->' in line:
                    schema[current_table]['foreign_keys'].append(line.strip('- ').strip())
        
        return schema
    
    def _generate_migration_sql(self, db_tables, db_columns, db_indices, db_foreign_keys):
        """Generiert SQL für die Migration zur gewünschten Struktur"""
        migration_sql = []
        
        # Prüfe jede Tabelle im Schema
        for table_name, table_schema in self.schema.items():
            # Neue Tabelle erstellen
            if table_name not in db_tables:
                columns = []
                for col in table_schema['columns']:
                    col_def = f"{col['name']} {col['type']}"
                    if col.get('primary_key'):
                        col_def += " PRIMARY KEY"
                    if col.get('not_null'):
                        col_def += " NOT NULL"
                    if col.get('default'):
                        col_def += f" DEFAULT {col['default']}"
                    columns.append(col_def)
                
                # Füge Foreign Keys hinzu
                for fk in table_schema.get('foreign_keys', []):
                    from_col, ref = fk.split(' -> ')
                    ref_table, ref_col = ref.split('.')
                    columns.append(f"FOREIGN KEY ({from_col}) REFERENCES {ref_table}({ref_col})")
                
                if columns:  # Nur erstellen wenn Spalten vorhanden sind
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    " + ",\n    ".join(columns) + "\n)"
                    migration_sql.append(create_table_sql)
                continue
            
            # Spalten hinzufügen oder ändern
            for column in table_schema['columns']:
                if column['name'] not in db_columns:
                    # Neue Spalte hinzufügen
                    col_def = f"{column['name']} {column['type']}"
                    if column.get('not_null'):
                        col_def += " NOT NULL"
                    if column.get('default'):
                        col_def += f" DEFAULT {column['default']}"
                    migration_sql.append(f"ALTER TABLE {table_name} ADD COLUMN {col_def}")
            
            # Indizes hinzufügen
            for index in table_schema.get('indices', []):
                if index not in db_indices:
                    # Extrahiere Spaltennamen aus dem Index
                    index_columns = index.split('_')[1:]  # Entferne 'idx_' Präfix
                    migration_sql.append(f"CREATE INDEX IF NOT EXISTS {index} ON {table_name} ({', '.join(index_columns)})")
            
            # Foreign Keys hinzufügen
            for fk in table_schema.get('foreign_keys', []):
                if fk not in db_foreign_keys:
                    # Extrahiere Spalten und Referenzen
                    from_col, ref = fk.split(' -> ')
                    ref_table, ref_col = ref.split('.')
                    migration_sql.append(
                        f"ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_{from_col} "
                        f"FOREIGN KEY ({from_col}) REFERENCES {ref_table}({ref_col})"
                    )
        
        return migration_sql
    
    def validate_and_migrate(self):
        """Prüft das Schema und führt Migrationen durch, wenn nötig"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Hole alle Tabellen aus der Datenbank
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                db_tables = {row[0] for row in cursor.fetchall()}
                
                # Sammle Informationen über die aktuelle Datenbankstruktur
                db_columns = {}
                db_indices = {}
                db_foreign_keys = {}
                
                for table in db_tables:
                    # Spalten
                    cursor.execute(f"PRAGMA table_info({table})")
                    db_columns[table] = {row[1]: {'type': row[2], 'pk': row[5]} for row in cursor.fetchall()}
                    
                    # Indizes
                    cursor.execute(f"PRAGMA index_list({table})")
                    db_indices[table] = {row[1] for row in cursor.fetchall()}
                    
                    # Foreign Keys
                    cursor.execute(f"PRAGMA foreign_key_list({table})")
                    db_foreign_keys[table] = set()
                    for row in cursor.fetchall():
                        ref_table = row[2]
                        from_col = row[3]
                        to_col = row[4]
                        db_foreign_keys[table].add(f"{from_col} -> {ref_table}.{to_col}")
                
                # Generiere Migrations-SQL
                migration_sql = self._generate_migration_sql(db_tables, db_columns, db_indices, db_foreign_keys)
                
                if migration_sql:
                    logger.info(f"Führe {len(migration_sql)} Migrationen für {self.db_path} durch")
                    
                    # Backup erstellen
                    backup_path = f"{self.db_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
                    with open(self.db_path, 'rb') as src, open(backup_path, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"Backup erstellt: {backup_path}")
                    
                    # Migrationen ausführen
                    for sql in migration_sql:
                        try:
                            cursor.execute(sql)
                            logger.info(f"Migration ausgeführt: {sql}")
                        except Exception as e:
                            logger.error(f"Fehler bei Migration: {sql}\nFehler: {str(e)}")
                            raise
                    
                    conn.commit()
                    logger.info("Migration erfolgreich abgeschlossen")
                    return True
                else:
                    logger.info("Keine Migrationen notwendig")
                    return True
                
        except Exception as e:
            logger.error(f"Fehler bei der Migration: {str(e)}")
            return False

def validate_and_migrate_databases():
    """Validiert und migriert beide Datenbanken beim Programmstart"""
    base_dir = Path(__file__).parent.parent.parent
    
    # Validiere und migriere Tickets-Datenbank
    tickets_db = base_dir / 'app' / 'database' / 'tickets.db'
    tickets_schema = base_dir / 'tickets_schema.txt'
    if tickets_db.exists() and tickets_schema.exists():
        validator = SchemaValidator(str(tickets_db), str(tickets_schema))
        if not validator.validate_and_migrate():
            logger.error("Tickets-Datenbank-Migration fehlgeschlagen")
            return False
    
    # Validiere und migriere Inventory-Datenbank
    inventory_db = base_dir / 'app' / 'database' / 'inventory.db'
    inventory_schema = base_dir / 'inventory_schema.txt'
    if inventory_db.exists() and inventory_schema.exists():
        validator = SchemaValidator(str(inventory_db), str(inventory_schema))
        if not validator.validate_and_migrate():
            logger.error("Inventory-Datenbank-Migration fehlgeschlagen")
            return False
    
    return True 