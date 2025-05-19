from app.models.database import Database

def init_db():
    """Initialisiert die Datenbank"""
    try:
        # Initialisiere die Datenbank mit dem Pfad
        Database.initialize('data/scandy.db')
        
        # Erstelle die Tabellen
        with Database.get_db() as conn:
            cursor = conn.cursor()
            
            # Settings Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Workers Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    department TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0
                )
            """)
            
            # Tools Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'available',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0
                )
            """)
            
            # Tool Usages Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_usages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_id INTEGER NOT NULL,
                    worker_id INTEGER NOT NULL,
                    borrowed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    returned_at TIMESTAMP,
                    FOREIGN KEY (tool_id) REFERENCES tools (id),
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            """)
            
            # Consumables Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consumables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT,
                    location TEXT,
                    quantity INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0
                )
            """)
            
            # Consumable Usages Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS consumable_usages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    consumable_id INTEGER NOT NULL,
                    worker_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (consumable_id) REFERENCES consumables (id),
                    FOREIGN KEY (worker_id) REFERENCES workers (id)
                )
            """)
            
            conn.commit()
            
        return True, "Datenbank erfolgreich initialisiert"
    except Exception as e:
        return False, f"Fehler bei der Datenbankinitialisierung: {str(e)}"

def create_admin_user():
    """Erstellt einen Admin-Benutzer"""
    try:
        # Prüfe ob Admin bereits existiert
        admin = Database.query(
            "SELECT * FROM workers WHERE name = 'Admin'",
            one=True
        )
        
        if admin:
            return True, "Admin-Benutzer existiert bereits"
            
        # Erstelle Admin-Benutzer
        Database.query(
            "INSERT INTO workers (name, department) VALUES (?, ?)",
            ['Admin', 'Administration']
        )
        
        return True, "Admin-Benutzer erfolgreich erstellt"
    except Exception as e:
        return False, f"Fehler beim Erstellen des Admin-Benutzers: {str(e)}"

def setup():
    """Führt das Setup durch"""
    # Initialisiere Datenbank
    success, message = init_db()
    if not success:
        return False, message
        
    # Erstelle Admin-Benutzer
    success, message = create_admin_user()
    if not success:
        return False, message
        
    return True, "Setup erfolgreich abgeschlossen" 