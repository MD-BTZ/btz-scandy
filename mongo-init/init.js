// MongoDB Initialisierung
db = db.getSiblingDB('scandy');

// Erstelle Collections
db.createCollection('users');
db.createCollection('tools');
db.createCollection('consumables');
db.createCollection('workers');
db.createCollection('settings');
db.createCollection('tickets');
db.createCollection('lendings');

// Erstelle Indizes
db.users.createIndex({ "username": 1 }, { unique: true });
db.tools.createIndex({ "barcode": 1 }, { unique: true });
db.consumables.createIndex({ "barcode": 1 }, { unique: true });
db.workers.createIndex({ "barcode": 1 }, { unique: true });
db.tickets.createIndex({ "ticket_id": 1 }, { unique: true });

print('MongoDB Initialisierung abgeschlossen');
