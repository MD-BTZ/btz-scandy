#!/usr/bin/env python3
"""
Debug-Skript für MongoDB-Verbindung und Statistiken
"""
import sys
import os

# Füge das app-Verzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.models.mongodb_database import mongodb
    from app.models.mongodb_models import MongoDBTool
    from app.config.config import config
    
    print("=== MONGODB DEBUG ===")
    
    # 1. Test der Konfiguration
    print("\n1. Konfiguration:")
    current_config = config['default']()
    print(f"MONGODB_URI: {current_config.MONGODB_URI}")
    print(f"MONGODB_DB: {current_config.MONGODB_DB}")
    
    # 2. Test der MongoDB-Verbindung
    print("\n2. MongoDB-Verbindung:")
    try:
        if mongodb._client is not None:
            print("✓ mongodb._client ist verfügbar")
            mongodb._client.admin.command('ping')
            print("✓ Ping erfolgreich")
        else:
            print("✗ mongodb._client ist None")
    except Exception as e:
        print(f"✗ MongoDB-Verbindungsfehler: {e}")
    
    # 3. Test der Collections
    print("\n3. Collections:")
    try:
        if mongodb.db is not None:
            collections = mongodb.db.list_collection_names()
            print(f"Verfügbare Collections: {collections}")
            
            # Teste spezifische Collections
            for collection_name in ['tools', 'consumables', 'workers', 'lendings', 'tickets']:
                if collection_name in collections:
                    count = mongodb.db[collection_name].count_documents({})
                    print(f"  {collection_name}: {count} Dokumente")
                else:
                    print(f"  {collection_name}: Collection nicht gefunden")
    except Exception as e:
        print(f"✗ Fehler beim Testen der Collections: {e}")
    
    # 4. Test der get_statistics Methode
    print("\n4. get_statistics Methode:")
    try:
        # Teste einzelne count_documents Aufrufe
        print("Teste einzelne Datenbankabfragen:")
        
        # Tools
        total_tools = mongodb.count_documents('tools', {'deleted': {'$ne': True}})
        print(f"  Tools total: {total_tools}")
        
        available_tools = mongodb.count_documents('tools', {
            'deleted': {'$ne': True},
            '$or': [
                {'status': 'available'},
                {'status': 'verfügbar'},
                {'status': 'Available'},
                {'status': {'$exists': False}}
            ]
        })
        print(f"  Tools available: {available_tools}")
        
        # Consumables
        total_consumables = mongodb.count_documents('consumables', {'deleted': {'$ne': True}})
        print(f"  Consumables total: {total_consumables}")
        
        # Workers
        total_workers = mongodb.count_documents('workers', {'deleted': {'$ne': True}})
        print(f"  Workers total: {total_workers}")
        
        # Lendings
        current_lendings = mongodb.count_documents('lendings', {'returned_at': {'$exists': False}})
        print(f"  Current lendings: {current_lendings}")
        
        # Vollständige get_statistics
        stats = MongoDBTool.get_statistics()
        print("\n✓ get_statistics erfolgreich")
        print(f"Tool-Statistiken: {stats['tool_stats']}")
        print(f"Consumable-Statistiken: {stats['consumable_stats']}")
        print(f"Worker-Statistiken: {stats['worker_stats']}")
        print(f"Aktuelle Ausleihen: {stats['current_lendings']}")
    except Exception as e:
        print(f"✗ Fehler in get_statistics: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    # 5. Test der doppelten Barcodes
    print("\n5. Doppelte Barcodes:")
    try:
        duplicates = MongoDBTool.get_duplicate_barcodes()
        print(f"✓ get_duplicate_barcodes erfolgreich: {len(duplicates)} Duplikate gefunden")
        for dup in duplicates:
            print(f"  Barcode {dup['barcode']}: {dup['count']} mal verwendet")
            for entry in dup['entries']:
                print(f"    - {entry['type']}: {entry['name']}")
    except Exception as e:
        print(f"✗ Fehler bei doppelten Barcodes: {e}")
    
    print("\n=== DEBUG ABGESCHLOSSEN ===")
    
except ImportError as e:
    print(f"Import-Fehler: {e}")
    print("Stelle sicher, dass alle Abhängigkeiten installiert sind.")
except Exception as e:
    print(f"Unerwarteter Fehler: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}") 