# Datenbankstruktur Dokumentation

## Vergleich: Erwartete vs. Tatsächliche Struktur

### Übereinstimmungen
- Alle Tabellen werden korrekt erstellt
- Alle Primärschlüssel sind korrekt definiert
- Alle Fremdschlüssel sind korrekt definiert
- Alle Standardwerte sind korrekt gesetzt
- Die Schema-Versionierung funktioniert wie erwartet

### Unterschiede
1. `users` Tabelle:
   - Erwartet: `password` (TEXT)
   - Tatsächlich: `password_hash` (TEXT)
   - Hinweis: Dies ist ein Implementierungsdetail, da das Passwort gehasht gespeichert wird

2. `settings` Tabelle:
   - Erwartet: Basis-Struktur
   - Tatsächlich: Zusätzliche Einträge für:
     - `department_*`: Abteilungen
     - `location_*`: Standorte
     - `category_*`: Kategorien
     - `label_*`: Benutzerdefinierte Labels
   - Hinweis: Diese zusätzlichen Einträge sind dynamisch und werden zur Laufzeit verwaltet

3. `homepage_notices` Tabelle:
   - Erwartet: Nicht in der Dokumentation
   - Tatsächlich: Wird in der App verwendet
   - Spalten:
     - `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
     - `title` (TEXT)
     - `content` (TEXT)
     - `priority` (INTEGER)
     - `is_active` (BOOLEAN)
     - `created_at` (TIMESTAMP)
     - `updated_at` (TIMESTAMP)

4. `sync_status` Tabelle:
   - Erwartet: Nicht in der Dokumentation
   - Tatsächlich: Wird für die Synchronisation verwendet
   - Spalten:
     - `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
     - `last_sync` (TIMESTAMP)
     - `status` (TEXT)
     - `error` (TEXT)

## Empfehlungen
1. Die Dokumentation sollte um die fehlenden Tabellen `homepage_notices` und `sync_status` ergänzt werden
2. Die dynamischen Einträge in der `settings` Tabelle sollten dokumentiert werden
3. Die Verwendung von `password_hash` statt `password` sollte in der Dokumentation klarer hervorgehoben werden

## Erwartete Datenbankstruktur

Die App erwartet folgende Tabellen und Spalten:

### access_settings
- `route` (TEXT, PRIMARY KEY): Der Routenpfad
- `is_public` (BOOLEAN, DEFAULT 0): Ob die Route öffentlich zugänglich ist
- `description` (TEXT): Beschreibung der Route

### tools
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT, NOT NULL)
- `barcode` (TEXT, UNIQUE NOT NULL)
- `category` (TEXT)
- `location` (TEXT)
- `status` (TEXT, DEFAULT 'verfügbar')
- `last_maintenance` (DATE)
- `next_maintenance` (DATE)
- `maintenance_interval` (INTEGER)
- `last_checked` (TIMESTAMP)
- `supplier` (TEXT)
- `reorder_point` (INTEGER)
- `notes` (TEXT)
- `deleted` (BOOLEAN, DEFAULT 0)
- `deleted_at` (TIMESTAMP)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `sync_status` (TEXT, DEFAULT 'pending')
- `modified_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### consumables
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `name` (TEXT, NOT NULL)
- `barcode` (TEXT, UNIQUE NOT NULL)
- `category` (TEXT)
- `location` (TEXT)
- `quantity` (INTEGER, DEFAULT 0)
- `min_quantity` (INTEGER, DEFAULT 0)
- `unit` (TEXT)
- `supplier` (TEXT)
- `reorder_point` (INTEGER)
- `notes` (TEXT)
- `deleted` (BOOLEAN, DEFAULT 0)
- `deleted_at` (TIMESTAMP)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `sync_status` (TEXT, DEFAULT 'pending')
- `modified_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### workers
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `firstname` (TEXT, NOT NULL)
- `lastname` (TEXT, NOT NULL)
- `barcode` (TEXT, UNIQUE NOT NULL)
- `department` (TEXT)
- `email` (TEXT)
- `phone` (TEXT)
- `notes` (TEXT)
- `deleted` (BOOLEAN, DEFAULT 0)
- `deleted_at` (TIMESTAMP)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `sync_status` (TEXT, DEFAULT 'pending')
- `modified_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### lendings
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `tool_barcode` (TEXT, NOT NULL)
- `worker_barcode` (TEXT, NOT NULL)
- `lent_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `returned_at` (TIMESTAMP)
- `notes` (TEXT)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `sync_status` (TEXT, DEFAULT 'pending')
- `modified_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- FOREIGN KEY (`tool_barcode`) REFERENCES `tools`(`barcode`)
- FOREIGN KEY (`worker_barcode`) REFERENCES `workers`(`barcode`)

### consumable_usage
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `consumable_barcode` (TEXT, NOT NULL)
- `worker_barcode` (TEXT, NOT NULL)
- `quantity` (INTEGER, NOT NULL)
- `used_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `sync_status` (TEXT, DEFAULT 'pending')
- `modified_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- FOREIGN KEY (`consumable_barcode`) REFERENCES `consumables`(`barcode`)
- FOREIGN KEY (`worker_barcode`) REFERENCES `workers`

### tickets
- `id` (INTEGER, PRIMARY KEY AUTOINCREMENT)
- `title` (TEXT, NOT NULL)
- `description` (TEXT, NOT NULL)
- `status` (TEXT, DEFAULT 'offen')
- `priority` (TEXT, DEFAULT 'normal')
- `created_by` (TEXT, NOT NULL)
- `assigned_to` (TEXT)
- `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
- `resolved_at` (TIMESTAMP)
- `resolution_notes` (TEXT)
- `response` (TEXT)  -- Öffentliche Antwort an den Benutzer
- FOREIGN KEY (`created_by`) REFERENCES `users`(`username`)
- FOREIGN KEY (`assigned_to`) REFERENCES `users`(`username`)