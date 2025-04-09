-- Neue Datenbank erstellen
ATTACH DATABASE 'instance/inventory_new.db' AS new;

-- Bestehende Tabellen löschen
DROP TABLE IF EXISTS new.users;
DROP TABLE IF EXISTS new.tools;
DROP TABLE IF EXISTS new.workers;
DROP TABLE IF EXISTS new.consumables;
DROP TABLE IF EXISTS new.lendings;
DROP TABLE IF EXISTS new.consumable_usages;
DROP TABLE IF EXISTS new.settings;
DROP TABLE IF EXISTS new.tickets;
DROP TABLE IF EXISTS new.ticket_notes;
DROP TABLE IF EXISTS new.tool_status_changes;

-- Tabellen in der neuen Datenbank erstellen
CREATE TABLE new.users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    is_tech INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE new.tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'verfügbar',
    category TEXT,
    location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER DEFAULT 0,
    deleted_at TIMESTAMP,
    sync_status TEXT DEFAULT 'pending'
);

CREATE TABLE new.workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT NOT NULL UNIQUE,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    department TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER DEFAULT 0,
    deleted_at TIMESTAMP,
    sync_status TEXT DEFAULT 'pending'
);

CREATE TABLE new.consumables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    quantity INTEGER DEFAULT 0,
    min_quantity INTEGER DEFAULT 0,
    category TEXT,
    location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted INTEGER DEFAULT 0,
    deleted_at TIMESTAMP,
    sync_status TEXT DEFAULT 'pending'
);

CREATE TABLE new.lendings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_barcode TEXT NOT NULL,
    worker_barcode TEXT NOT NULL,
    lent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    returned_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending',
    FOREIGN KEY (tool_barcode) REFERENCES tools(barcode),
    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
);

CREATE TABLE new.consumable_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumable_barcode TEXT NOT NULL,
    worker_barcode TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'pending',
    FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
);

CREATE TABLE new.settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

CREATE TABLE new.tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'offen',
    priority TEXT DEFAULT 'normal',
    created_by TEXT NOT NULL,
    assigned_to TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT
);

CREATE TABLE new.ticket_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    note TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

CREATE TABLE new.tool_status_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_barcode TEXT NOT NULL,
    old_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (tool_barcode) REFERENCES tools(barcode)
);

-- Indizes erstellen
CREATE INDEX new.idx_tools_barcode ON tools(barcode);
CREATE INDEX new.idx_workers_barcode ON workers(barcode);
CREATE INDEX new.idx_consumables_barcode ON consumables(barcode);
CREATE INDEX new.idx_lendings_tool ON lendings(tool_barcode);
CREATE INDEX new.idx_lendings_worker ON lendings(worker_barcode);
CREATE INDEX new.idx_consumable_usages_consumable ON consumable_usages(consumable_barcode);
CREATE INDEX new.idx_consumable_usages_worker ON consumable_usages(worker_barcode);
CREATE INDEX new.idx_tool_status_changes_tool ON tool_status_changes(tool_barcode);
CREATE INDEX new.idx_tickets_status ON tickets(status);
CREATE INDEX new.idx_tickets_priority ON tickets(priority);
CREATE INDEX new.idx_ticket_notes_ticket ON ticket_notes(ticket_id);

-- Daten migrieren
-- Users
INSERT INTO new.users SELECT * FROM users;

-- Tools
INSERT INTO new.tools SELECT * FROM tools;

-- Workers
INSERT INTO new.workers SELECT * FROM workers;

-- Consumables
INSERT INTO new.consumables SELECT * FROM consumables;

-- Lendings
INSERT INTO new.lendings SELECT * FROM lendings;

-- Consumable Usages
INSERT INTO new.consumable_usages SELECT * FROM consumable_usages;

-- Settings
INSERT INTO new.settings SELECT * FROM settings;

-- Tickets
INSERT INTO new.tickets SELECT * FROM tickets;

-- Ticket Notes
INSERT INTO new.ticket_notes SELECT * FROM ticket_notes;

-- Tool Status Changes
INSERT INTO new.tool_status_changes SELECT * FROM tool_status_changes;

-- Datenbank-Verbindung trennen
DETACH DATABASE new; 