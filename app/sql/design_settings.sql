-- Erstelle settings Tabelle falls sie nicht existiert
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Lösche existierende Design-Einträge falls vorhanden
DELETE FROM settings WHERE key IN ('logo_path', 'primary_color', 'secondary_color', 'accent_color');

-- Füge Standard-Design-Einstellungen ein
INSERT INTO settings (key, value) VALUES 
    ('logo_path', 'Logo-BTZ-WEISS.svg'),
    ('primary_color', '#5b69a7'),
    ('secondary_color', '#4c5789'),
    ('accent_color', '#3d4675'); 