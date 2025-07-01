#!/usr/bin/env python3
"""
Script um alle Collections in der Datenbank zu prüfen
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb

def check_collections():
    print("=== ALLE COLLECTIONS IN DER DATENBANK ===\n")
    
    # Hole alle Collections
    collections = mongodb.db.list_collection_names()
    
    print(f"Anzahl Collections: {len(collections)}\n")
    
    for collection in sorted(collections):
        # Zähle Dokumente
        count = mongodb.db[collection].count_documents({})
        print(f"Collection: {collection}")
        print(f"  - Dokumente: {count}")
        
        # Zeige ein Beispiel-Dokument (falls vorhanden)
        if count > 0:
            example = mongodb.db[collection].find_one()
            if example:
                # Zeige nur die ersten 3 Felder
                fields = list(example.keys())[:3]
                print(f"  - Beispiel-Felder: {fields}")
        print()

if __name__ == "__main__":
    check_collections() 