def handle_consumable(barcode, quantity, worker_barcode):
    # Bestand prüfen und aktualisieren
    consumable = Database.query('''
        SELECT * FROM consumables 
        WHERE barcode = ? AND deleted = 0
    ''', [barcode], one=True)
    
    if not consumable:
        return False, "Verbrauchsmaterial nicht gefunden"
        
    if consumable['quantity'] < quantity:
        return False, "Nicht genügend Bestand verfügbar"
    
    # Bestand reduzieren
    Database.execute('''
        UPDATE consumables 
        SET quantity = quantity - ? 
        WHERE barcode = ?
    ''', [quantity, barcode])
    
    # Verbrauch protokollieren
    Database.execute('''
        INSERT INTO consumable_usage 
        (consumable_barcode, worker_barcode, quantity) 
        VALUES (?, ?, ?)
    ''', [barcode, worker_barcode, quantity])
    
    return True, "Materialentnahme erfolgreich" 