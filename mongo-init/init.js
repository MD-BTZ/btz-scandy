// MongoDB Initialisierung für Scandy
// Datenbank: scandy

// Hole Benutzer und Passwort aus den offiziellen MongoDB-Umgebungsvariablen
var mongoUser = process.env.MONGO_INITDB_ROOT_USERNAME || 'admin';
var mongoPassword = process.env.MONGO_INITDB_ROOT_PASSWORD || 'scandy123';

// Erstelle MongoDB-Authentifizierungsbenutzer in der admin-Datenbank
db = db.getSiblingDB('admin');

// Erstelle den MongoDB-Authentifizierungsbenutzer
db.createUser({
    user: mongoUser,
    pwd: mongoPassword,
    roles: [
        { role: 'readWrite', db: 'scandy' },
        { role: 'dbAdmin', db: 'scandy' }
    ]
});

// Wechsle zur Instanz-spezifischen Datenbank
db = db.getSiblingDB('scandy');

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
// Email-Index nur erstellen wenn er nicht existiert
try {
    db.users.createIndex({ "email": 1 }, { sparse: true });
} catch (e) {
    // Index existiert bereits, ignoriere Fehler
    print("Email-Index existiert bereits oder konnte nicht erstellt werden: " + e.message);
}

db.tickets.createIndex({ "created_at": 1 });
db.tickets.createIndex({ "status": 1 });
db.tickets.createIndex({ "assigned_to": 1 });

// Erstelle Admin-Benutzer
db.users.insertOne({
    username: 'admin',
    email: 'admin@scandy.local',
    password_hash: '$2b$12$EawTS69lQeWoJoeVRms9BuU6XfePQzgTjZwVjn8dl4xqA3rnxVbHy',
    role: 'admin',
    is_active: true,
    created_at: new Date(),
    updated_at: new Date()
});

// Erstelle Beispiel-Teilnehmer
db.users.insertOne({
    username: 'teilnehmer',
    email: 'teilnehmer@scandy.local',
    password_hash: '$2b$12$EawTS69lQeWoJoeVRms9BuU6XfePQzgTjZwVjn8dl4xqA3rnxVbHy',
    role: 'teilnehmer',
    is_active: true,
    timesheet_enabled: true,
    created_at: new Date(),
    updated_at: new Date()
});

// Erstelle Standard-Einstellungen
db.settings.insertOne({
    key: 'system_name',
    value: 'Scandy',
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

print('MongoDB für Scandy initialisiert!');
print('Datenbank: scandy');
print('MongoDB-Authentifizierungsbenutzer: admin / [aus Umgebungsvariable]');
print('App-Admin-Benutzer: Wird über Setup-Assistent erstellt (keine Standard-Zugangsdaten)');
