-- Initiales Schema für die Datenbank

-- Schema Version Tabelle
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users Tabelle
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    firstname TEXT,
    lastname TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Settings Tabelle
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories Tabelle
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Locations Tabelle
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Departments Tabelle
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tools Tabelle
CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    location TEXT,
    status TEXT DEFAULT 'verfügbar',
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Workers Tabelle
CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE NOT NULL,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    department TEXT,
    role TEXT,
    email TEXT,
    phone TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Consumables Tabelle
CREATE TABLE IF NOT EXISTS consumables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    location TEXT,
    quantity INTEGER DEFAULT 0,
    unit TEXT,
    supplier TEXT,
    reorder_point INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lendings Tabelle
CREATE TABLE IF NOT EXISTS lendings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_barcode TEXT NOT NULL,
    worker_barcode TEXT NOT NULL,
    lent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    returned_at TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (tool_barcode) REFERENCES tools(barcode),
    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
);

-- Consumable Usages Tabelle
CREATE TABLE IF NOT EXISTS consumable_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumable_barcode TEXT NOT NULL,
    worker_barcode TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
);

-- Tickets Tabelle
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'offen',
    priority TEXT DEFAULT 'normal',
    category TEXT,
    assigned_to TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(username),
    FOREIGN KEY (assigned_to) REFERENCES users(username)
);

-- Ticket Messages Tabelle
CREATE TABLE IF NOT EXISTS ticket_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    sender TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (sender) REFERENCES users(username)
);

-- Bewerbungsvorlagen Tabelle
CREATE TABLE IF NOT EXISTS bewerbungsvorlagen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    dateiname TEXT NOT NULL,
    file_path TEXT NOT NULL,
    kategorie TEXT,
    erstellt_von TEXT NOT NULL,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ist_aktiv BOOLEAN DEFAULT 1,
    FOREIGN KEY (erstellt_von) REFERENCES users(username)
);

-- Bewerbungsdokumente Tabelle
CREATE TABLE IF NOT EXISTS bewerbungsdokumente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vorlagen_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    beschreibung TEXT,
    dateipfad TEXT NOT NULL,
    ist_erforderlich BOOLEAN DEFAULT 1,
    erstellt_von TEXT NOT NULL,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vorlagen_id) REFERENCES bewerbungsvorlagen(id) ON DELETE CASCADE,
    FOREIGN KEY (erstellt_von) REFERENCES users(username)
);

-- Bewerbungen Tabelle
CREATE TABLE IF NOT EXISTS bewerbungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vorlagen_id INTEGER NOT NULL,
    bewerber TEXT NOT NULL,
    firmenname TEXT NOT NULL,
    position TEXT NOT NULL,
    ansprechpartner TEXT,
    anrede TEXT,
    email TEXT,
    telefon TEXT,
    adresse TEXT,
    eigener_text TEXT,
    status TEXT DEFAULT 'in_bearbeitung',
    erstellt_von TEXT NOT NULL,
    erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vorlagen_id) REFERENCES bewerbungsvorlagen(id),
    FOREIGN KEY (bewerber) REFERENCES users(username),
    FOREIGN KEY (erstellt_von) REFERENCES users(username)
);

-- Bewerbungsdokumente Uploads Tabelle
CREATE TABLE IF NOT EXISTS bewerbungsdokumente_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bewerbung_id INTEGER NOT NULL,
    dokument_id INTEGER NOT NULL,
    dateipfad TEXT NOT NULL,
    hochgeladen_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bewerbung_id) REFERENCES bewerbungen(id) ON DELETE CASCADE,
    FOREIGN KEY (dokument_id) REFERENCES bewerbungsdokumente(id)
);

-- Persönliche Dokumente eines Benutzers
CREATE TABLE IF NOT EXISTS benutzerdokumente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benutzername TEXT NOT NULL,
    dokumenttyp TEXT,
    dateiname TEXT NOT NULL,
    dateipfad TEXT NOT NULL,
    hochgeladen_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (benutzername) REFERENCES users(username)
);

-- Zuordnungstabelle: Welche Dokumente gehören zu welcher Bewerbung?
CREATE TABLE IF NOT EXISTS bewerbung_dokumente_zuordnung (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bewerbung_id INTEGER NOT NULL,
    dokument_id INTEGER NOT NULL,
    FOREIGN KEY (bewerbung_id) REFERENCES bewerbungen(id) ON DELETE CASCADE,
    FOREIGN KEY (dokument_id) REFERENCES benutzerdokumente(id) ON DELETE CASCADE
);

-- Indizes
CREATE INDEX IF NOT EXISTS idx_tools_barcode ON tools(barcode);
CREATE INDEX IF NOT EXISTS idx_workers_barcode ON workers(barcode);
CREATE INDEX IF NOT EXISTS idx_consumables_barcode ON consumables(barcode);
CREATE INDEX IF NOT EXISTS idx_bewerbungsvorlagen_erstellt_von ON bewerbungsvorlagen(erstellt_von);

-- Setze Schema-Version
INSERT INTO schema_version (version) VALUES (10); 