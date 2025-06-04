-- Migration 6
CREATE TABLE IF NOT EXISTS application_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    category TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Migration 7
CREATE TABLE IF NOT EXISTS application_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    document_type TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Migration 8
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER,
    company_name TEXT NOT NULL,
    position TEXT NOT NULL,
    contact_person TEXT,
    salutation TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    address TEXT,
    generated_content TEXT,
    custom_text TEXT,
    status TEXT DEFAULT 'neu',
    notes TEXT,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cv_path TEXT,
    certificates_path TEXT,
    output_path TEXT,
    pdf_path TEXT,
    FOREIGN KEY (template_id) REFERENCES application_templates(id)
);

-- Migration 9
-- Überprüfe, ob die Spalte erstellt_von bereits existiert
SELECT CASE 
    WHEN EXISTS (
        SELECT 1 
        FROM pragma_table_info('applications') 
        WHERE name = 'erstellt_von'
    ) THEN 1
    ELSE 0
END as column_exists;

-- Füge die fehlenden Spalten hinzu, falls sie noch nicht existieren
ALTER TABLE applications ADD COLUMN erstellt_am TIMESTAMP;
ALTER TABLE applications ADD COLUMN aktualisiert_am TIMESTAMP;
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

-- Migriere die Daten von den alten Spalten zu den neuen
UPDATE applications 
SET erstellt_am = created_at,
    aktualisiert_am = created_at,  -- Verwende created_at als Fallback
    firmenname = company_name,
    ansprechpartner = contact_person,
    anrede = salutation,
    email = contact_email,
    telefon = contact_phone,
    adresse = address,
    generierter_inhalt = generated_content,
    eigener_text = custom_text,
    notizen = notes,
    lebenslauf_pfad = cv_path,
    zeugnisse_pfad = certificates_path,
    ausgabe_pfad = output_path,
    pdf_pfad = pdf_path
WHERE erstellt_am IS NULL;

-- Setze Standardwerte für die Timestamp-Spalten
UPDATE applications SET erstellt_am = CURRENT_TIMESTAMP WHERE erstellt_am IS NULL;
UPDATE applications SET aktualisiert_am = CURRENT_TIMESTAMP WHERE aktualisiert_am IS NULL;

-- Aktualisiere die Schema-Version
INSERT OR IGNORE INTO schema_version (version) VALUES (9); 