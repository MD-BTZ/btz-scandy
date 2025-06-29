// MongoDB Initialisierung für Scandy production
// Datenbank: scandy_production

// Erstelle MongoDB-Authentifizierungsbenutzer in der admin-Datenbank
db = db.getSiblingDB('admin');

// Erstelle den MongoDB-Authentifizierungsbenutzer
db.createUser({
    user: 'admin',
    pwd: '9jzJdz_AauYF7G4s',
    roles: [
        { role: 'readWrite', db: 'scandy_production' },
        { role: 'dbAdmin', db: 'scandy_production' }
    ]
});

// Wechsle zur Instanz-spezifischen Datenbank
db = db.getSiblingDB('scandy_production');

// Erstelle Collections
db.createCollection('tools');
db.createCollection('consumables');
db.createCollection('workers');
db.createCollection('lendings');
db.createCollection('users');
db.createCollection('tickets');
db.createCollection('settings');
db.createCollection('system_logs');

// Erstelle Indexe
db.tools.createIndex({ "barcode": 1 }, { unique: true });
db.tools.createIndex({ "deleted": 1 });
db.tools.createIndex({ "status": 1 });

db.consumables.createIndex({ "barcode": 1 }, { unique: true });
db.consumables.createIndex({ "deleted": 1 });

db.workers.createIndex({ "barcode": 1 }, { unique: true });
db.workers.createIndex({ "deleted": 1 });

db.lendings.createIndex({ "tool_barcode": 1 });
db.lendings.createIndex({ "worker_barcode": 1 });
db.lendings.createIndex({ "returned_at": 1 });

db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { sparse: true });

db.tickets.createIndex({ "created_at": 1 });
db.tickets.createIndex({ "status": 1 });
db.tickets.createIndex({ "assigned_to": 1 });

// Erstelle Admin-Benutzer
db.users.insertOne({
    username: 'admin',
    email: 'admin@production.local',
    password_hash: '$2b$12$EawTS69lQeWoJoeVRms9BuU6XfePQzgTjZwVjn8dl4xqA3rnxVbHy',
    role: 'admin',
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
});

// Erstelle Standard-Einstellungen
db.settings.insertOne({
    key: 'system_name',
    value: 'Scandy production',
    created_at: new Date(),
    updated_at: new Date()
});

db.settings.insertOne({
    key: 'ticket_system_name',
    value: 'Aufgaben',
    created_at: new Date(),
    updated_at: new Date()
});

db.settings.insertOne({
    key: 'tool_system_name',
    value: 'Werkzeuge',
    created_at: new Date(),
    updated_at: new Date()
});

db.settings.insertOne({
    key: 'consumable_system_name',
    value: 'Verbrauchsgüter',
    created_at: new Date(),
    updated_at: new Date()
});

print('MongoDB für Scandy production initialisiert!');
print('Datenbank: scandy_production');
print('MongoDB-Authentifizierungsbenutzer: admin / 9jzJdz_AauYF7G4s');
print('App-Admin-Benutzer: admin / admin123');
