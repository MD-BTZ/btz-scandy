-- Füge pdf_path-Feld zur applications-Tabelle hinzu
ALTER TABLE applications ADD COLUMN pdf_path TEXT;

-- Migration 8: Füge Indizes für bessere Performance hinzu
-- Prüfe zuerst, ob die Spalte erstellt_von existiert
SELECT CASE 
    WHEN EXISTS (
        SELECT 1 
        FROM pragma_table_info('applications') 
        WHERE name = 'erstellt_von'
    ) THEN 1
    ELSE 0
END;

-- Füge die Spalte hinzu, falls sie nicht existiert
ALTER TABLE applications ADD COLUMN erstellt_von TEXT;

-- Erstelle die Indizes
CREATE INDEX IF NOT EXISTS idx_applications_erstellt_von ON applications(erstellt_von);
CREATE INDEX IF NOT EXISTS idx_applications_erstellt_am ON applications(erstellt_am);
CREATE INDEX IF NOT EXISTS idx_applications_aktualisiert_am ON applications(aktualisiert_am);
CREATE INDEX IF NOT EXISTS idx_application_documents_application_id ON application_documents(application_id);
CREATE INDEX IF NOT EXISTS idx_application_documents_document_type ON application_documents(document_type);

-- Aktualisiere die Schema-Version
INSERT OR IGNORE INTO schema_version (version) VALUES (8); 