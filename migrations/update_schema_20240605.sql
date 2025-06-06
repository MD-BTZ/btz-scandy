-- Migration script to update database schema for Scandy
-- Created: 2024-06-05

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Add new columns to tools table if they don't exist
BEGIN TRANSACTION;

-- Add sync_status column if it doesn't exist
CREATE TABLE IF NOT EXISTS tools_new (
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
    sync_status TEXT DEFAULT 'pending',
    last_sync TIMESTAMP,
    notes TEXT
);

-- Copy data from old table to new table
INSERT INTO tools_new (
    id, barcode, name, description, status, category, location, 
    created_at, modified_at, deleted, deleted_at, sync_status
) SELECT 
    id, barcode, name, description, status, category, location, 
    created_at, modified_at, deleted, deleted_at, sync_status 
FROM tools;

-- Drop old table and rename new one
DROP TABLE tools;
ALTER TABLE tools_new RENAME TO tools;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_tools_barcode ON tools(barcode);
CREATE INDEX IF NOT EXISTS idx_tools_status ON tools(status);
CREATE INDEX IF NOT EXISTS idx_tools_deleted ON tools(deleted);

-- Update workers table if needed
CREATE TABLE IF NOT EXISTS workers_new (
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
    sync_status TEXT DEFAULT 'pending',
    last_sync TIMESTAMP
);

-- Copy data from old table to new table
INSERT INTO workers_new (
    id, barcode, firstname, lastname, department, email,
    created_at, modified_at, deleted, deleted_at, sync_status
) SELECT 
    id, barcode, firstname, lastname, department, email,
    created_at, modified_at, deleted, deleted_at, COALESCE(sync_status, 'pending')
FROM workers;

-- Drop old table and rename new one
DROP TABLE workers;
ALTER TABLE workers_new RENAME TO workers;

-- Create indexes for workers
CREATE INDEX IF NOT EXISTS idx_workers_barcode ON workers(barcode);
CREATE INDEX IF NOT EXISTS idx_workers_deleted ON workers(deleted);

-- Update lendings table if needed
CREATE TABLE IF NOT EXISTS lendings_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_barcode TEXT NOT NULL,
    worker_barcode TEXT NOT NULL,
    lent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    returned_at TIMESTAMP,
    notes TEXT,
    sync_status TEXT DEFAULT 'pending',
    last_sync TIMESTAMP,
    FOREIGN KEY (tool_barcode) REFERENCES tools(barcode),
    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
);

-- Copy data from old table to new table
INSERT INTO lendings_new (
    id, tool_barcode, worker_barcode, lent_at, returned_at, notes, sync_status
) SELECT 
    id, tool_barcode, worker_barcode, lent_at, returned_at, notes, COALESCE(sync_status, 'pending')
FROM lendings;

-- Drop old table and rename new one
DROP TABLE lendings;
ALTER TABLE lendings_new RENAME TO lendings;

-- Create indexes for lendings
CREATE INDEX IF NOT EXISTS idx_lendings_tool_barcode ON lendings(tool_barcode);
CREATE INDEX IF NOT EXISTS idx_lendings_worker_barcode ON lendings(worker_barcode);
CREATE INDEX IF NOT EXISTS idx_lendings_returned_at ON lendings(returned_at);

-- Commit the transaction
COMMIT;

-- Update database version
PRAGMA user_version = 2;

-- Print success message
SELECT 'Database schema updated successfully!' as message;
