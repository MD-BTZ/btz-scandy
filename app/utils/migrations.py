def migrate_categories():
    """Migriert die bestehenden Kategorien, um den Typ zu unterstützen."""
    try:
        with Database.get_db() as conn:
            # Prüfe ob die Spalte 'type' bereits existiert
            cursor = conn.execute("PRAGMA table_info(categories)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'type' not in columns:
                # Füge die Spalte 'type' hinzu
                conn.execute('ALTER TABLE categories ADD COLUMN type TEXT NOT NULL DEFAULT "ticket"')
                
                # Aktualisiere bestehende Kategorien
                conn.execute('''
                    UPDATE categories 
                    SET type = "ticket" 
                    WHERE type IS NULL
                ''')
                
                # Erstelle einen Unique-Index für name und type
                conn.execute('''
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_categories_name_type 
                    ON categories(name, type) 
                    WHERE deleted = 0
                ''')
                
                logger.info("Kategorien erfolgreich migriert")
                return True
    except Exception as e:
        logger.error(f"Fehler bei der Kategorie-Migration: {str(e)}")
        return False 