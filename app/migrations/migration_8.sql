-- Füge pdf_path-Feld zur applications-Tabelle hinzu
ALTER TABLE applications ADD COLUMN pdf_path TEXT;

-- Aktualisiere die Schema-Version
UPDATE schema_version SET version = 8; 