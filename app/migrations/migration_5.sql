-- Migration 5: Füge neue Spalten zur applications Tabelle hinzu
ALTER TABLE applications ADD COLUMN erstellt_von TEXT;
ALTER TABLE applications ADD COLUMN erstellt_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE applications ADD COLUMN aktualisiert_am TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE applications ADD COLUMN firmenname TEXT;
ALTER TABLE applications ADD COLUMN ansprechpartner TEXT;
ALTER TABLE applications ADD COLUMN anrede TEXT;
ALTER TABLE applications ADD COLUMN email TEXT;
ALTER TABLE applications ADD COLUMN telefon TEXT;
ALTER TABLE applications ADD COLUMN adresse TEXT;
ALTER TABLE applications ADD COLUMN generierter_inhalt TEXT;
ALTER TABLE applications ADD COLUMN eigener_text TEXT;
ALTER TABLE applications ADD COLUMN notizen TEXT;
ALTER TABLE applications ADD COLUMN lebenslauf_pfad TEXT;
ALTER TABLE applications ADD COLUMN zeugnisse_pfad TEXT;
ALTER TABLE applications ADD COLUMN ausgabe_pfad TEXT;
ALTER TABLE applications ADD COLUMN pdf_pfad TEXT;

-- Aktualisiere die Schema-Version
INSERT OR IGNORE INTO schema_version (version) VALUES (5); 