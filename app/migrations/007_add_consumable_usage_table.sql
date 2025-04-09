CREATE TABLE IF NOT EXISTS consumable_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consumable_barcode TEXT NOT NULL,
    worker_barcode TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consumable_barcode) REFERENCES consumables(barcode),
    FOREIGN KEY (worker_barcode) REFERENCES workers(barcode)
);

-- Index für schnellere Abfragen
CREATE INDEX IF NOT EXISTS idx_consumable_usage_consumable ON consumable_usages(consumable_barcode);
CREATE INDEX IF NOT EXISTS idx_consumable_usage_worker ON consumable_usages(worker_barcode);
CREATE INDEX IF NOT EXISTS idx_consumable_usage_date ON consumable_usages(used_at); 