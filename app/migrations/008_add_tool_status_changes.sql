CREATE TABLE IF NOT EXISTS tool_status_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_barcode TEXT NOT NULL,
    old_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tool_barcode) REFERENCES tools(barcode)
);

-- Index für schnellere Abfragen
CREATE INDEX IF NOT EXISTS idx_tool_status_changes_tool ON tool_status_changes(tool_barcode);
CREATE INDEX IF NOT EXISTS idx_tool_status_changes_date ON tool_status_changes(created_at); 