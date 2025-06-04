-- Migration 6: Erstelle application_templates Tabelle
CREATE TABLE IF NOT EXISTS application_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Aktualisiere die Schema-Version
INSERT OR IGNORE INTO schema_version (version) VALUES (6); 