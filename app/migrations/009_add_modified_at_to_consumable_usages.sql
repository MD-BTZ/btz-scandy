-- Füge modified_at Spalte zur consumable_usages Tabelle hinzu
ALTER TABLE consumable_usages ADD COLUMN modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Aktualisiere bestehende Einträge
UPDATE consumable_usages SET modified_at = used_at WHERE modified_at IS NULL; 