"""
MongoDB-Datenbankmodul für Scandy
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
from datetime import datetime
import logging
from bson import ObjectId
from app.config.config import config
import json
from typing import Dict, List, Any, Optional, Union
import os
import time

# Logger deaktiviert für Gunicorn-Kompatibilität
# logger = logging.getLogger(__name__)

class MongoDBDatabase:
    """MongoDB-Datenbankklasse für Scandy"""
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBDatabase, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._connect()
    
    def _connect(self):
        """Stellt die Verbindung zur MongoDB her (robust mit Retry)"""
        uri = os.environ.get("MONGODB_URI")
        db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
        if uri and 'authSource' not in uri:
            # Füge authSource=admin hinzu, falls nicht vorhanden
            if '?' in uri:
                uri += '&authSource=admin'
            else:
                uri += '?authSource=admin'
        for attempt in range(10):
            try:
                password = os.environ.get("MONGO_INITDB_ROOT_PASSWORD", "")
                safe_uri = uri.replace(password, "***") if password and uri else uri
                print(f"[MongoDB] Verbindungsversuch {attempt+1}/10 zu {safe_uri}")
                self._client = MongoClient(uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000, retryWrites=True, w='majority')
                self._client.admin.command('ping')
                self._db = self._client[db_name]
                print(f"[MongoDB] Verbindung erfolgreich zu {safe_uri}")
                return
            except (ServerSelectionTimeoutError, OperationFailure) as e:
                print(f"[MongoDB] Nicht erreichbar (Versuch {attempt+1}/10): {e}")
                time.sleep(3)
        raise Exception("MongoDB-Verbindung nach 10 Versuchen fehlgeschlagen!")
    
    @property
    def db(self):
        """Gibt die Datenbank zurück"""
        if self._db is None:
            self._connect()
        return self._db
    
    def get_collection(self, collection_name: str):
        """Gibt eine MongoDB-Collection zurück"""
        if self._db is None:
            self._connect()
        return self._db[collection_name]
    
    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> str:
        """Fügt ein Dokument in eine Collection ein"""
        collection = self.get_collection(collection_name)
        
        # Timestamps hinzufügen
        document['created_at'] = datetime.now()
        document['updated_at'] = datetime.now()
        
        result = collection.insert_one(document)
        return str(result.inserted_id)
    
    def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]) -> List[str]:
        """Fügt mehrere Dokumente in eine Collection ein"""
        collection = self.get_collection(collection_name)
        
        # Timestamps hinzufügen
        for doc in documents:
            doc['created_at'] = datetime.now()
            doc['updated_at'] = datetime.now()
        
        result = collection.insert_many(documents)
        return [str(id) for id in result.inserted_ids]
    
    def find_one(self, collection_name: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Findet ein Dokument in einer Collection"""
        collection = self.get_collection(collection_name)
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        result = collection.find_one(processed_filter)
        
        if result:
            # ObjectId zu String konvertieren
            result['_id'] = str(result['_id'])
        
        return result
    
    def find(self, collection_name: str, filter_dict: Dict[str, Any] = None, 
             sort: List[tuple] = None, limit: int = None, skip: int = None) -> List[Dict[str, Any]]:
        """Findet mehrere Dokumente in einer Collection"""
        collection = self.get_collection(collection_name)
        
        if filter_dict is None:
            filter_dict = {}
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        cursor = collection.find(processed_filter)
        
        if sort:
            cursor = cursor.sort(sort)
        
        if skip:
            cursor = cursor.skip(skip)
        
        if limit:
            cursor = cursor.limit(limit)
        
        results = []
        for doc in cursor:
            # ObjectId zu String konvertieren
            doc['_id'] = str(doc['_id'])
            results.append(doc)
        
        return results
    
    def update_one(self, collection_name: str, filter_dict: Dict[str, Any], 
                   update_dict: Dict[str, Any], upsert: bool = False) -> bool:
        """Aktualisiert ein Dokument in einer Collection"""
        collection = self.get_collection(collection_name)
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        # Prüfe ob update_dict bereits MongoDB-Operatoren enthält
        has_operators = any(key.startswith('$') for key in update_dict.keys())
        
        if has_operators:
            # Wenn bereits Operatoren vorhanden sind, füge nur updated_at hinzu, falls $set vorhanden ist
            if '$set' in update_dict:
                update_dict['$set']['updated_at'] = datetime.now()
            # Wenn kein $set vorhanden ist, füge es hinzu nur für updated_at
            else:
                update_dict['$set'] = {'updated_at': datetime.now()}
        else:
            # Erstelle $set Modifier falls nicht vorhanden
            update_dict = {'$set': {**update_dict, 'updated_at': datetime.now()}}
        
        try:
            result = collection.update_one(processed_filter, update_dict, upsert=upsert)
            
            # Debug-Logs für bessere Fehlerdiagnose
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"DEBUG: update_one Ergebnis - matched_count: {result.matched_count}, modified_count: {result.modified_count}, upserted_id: {result.upserted_id}")
            logger.info(f"DEBUG: update_one Filter: {processed_filter}")
            
            # Betrachte die Operation als erfolgreich, wenn:
            # 1. Ein Dokument modifiziert wurde, ODER
            # 2. Ein neues Dokument erstellt wurde (upsert), ODER
            # 3. Ein Dokument gefunden wurde (matched_count > 0) - auch wenn sich nichts geändert hat
            success = (result.modified_count > 0 or 
                      result.upserted_id is not None or 
                      result.matched_count > 0)
            
            logger.info(f"DEBUG: update_one Erfolg: {success}")
            return success
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Fehler bei update_one: {e}")
            return False
    
    def _process_filter_ids(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Konvertiert String-IDs zu ObjectIds in Filter-Dictionaries"""
        processed_filter = {}
        
        for key, value in filter_dict.items():
            if key == '_id' and isinstance(value, str):
                try:
                    from bson import ObjectId
                    processed_filter[key] = ObjectId(value)
                except Exception:
                    # Falls Konvertierung fehlschlägt, verwende Original-Wert
                    processed_filter[key] = value
            else:
                processed_filter[key] = value
        
        return processed_filter
    
    def update_one_array(self, collection_name: str, filter_dict: Dict[str, Any], 
                        update_dict: Dict[str, Any], upsert: bool = False) -> bool:
        """Aktualisiert ein Dokument in einer Collection mit Array-Operationen ($push, $pull, etc.)
        Diese Methode fügt keine automatischen Timestamps hinzu, um Konflikte zu vermeiden."""
        collection = self.get_collection(collection_name)
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        result = collection.update_one(processed_filter, update_dict, upsert=upsert)
        return result.modified_count > 0 or result.upserted_id is not None
    
    def update_many(self, collection_name: str, filter_dict: Dict[str, Any], 
                    update_dict: Dict[str, Any]) -> int:
        """Aktualisiert mehrere Dokumente in einer Collection"""
        collection = self.get_collection(collection_name)
        
        # Prüfe ob update_dict bereits MongoDB-Operatoren enthält
        has_operators = any(key.startswith('$') for key in update_dict.keys())
        
        if has_operators:
            # Wenn bereits Operatoren vorhanden sind, füge nur updated_at hinzu, falls $set vorhanden ist
            if '$set' in update_dict:
                update_dict['$set']['updated_at'] = datetime.now()
            # Wenn kein $set vorhanden ist, füge es hinzu nur für updated_at
            else:
                update_dict['$set'] = {'updated_at': datetime.now()}
        else:
            # Erstelle $set Modifier falls nicht vorhanden
            update_dict = {'$set': {**update_dict, 'updated_at': datetime.now()}}
        
        result = collection.update_many(filter_dict, update_dict)
        return result.modified_count
    
    def delete_one(self, collection_name: str, filter_dict: Dict[str, Any]) -> bool:
        """Löscht ein Dokument aus einer Collection"""
        collection = self.get_collection(collection_name)
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        result = collection.delete_one(processed_filter)
        return result.deleted_count > 0
    
    def delete_many(self, collection_name: str, filter_dict: Dict[str, Any]) -> int:
        """Löscht mehrere Dokumente aus einer Collection"""
        collection = self.get_collection(collection_name)
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        result = collection.delete_many(processed_filter)
        return result.deleted_count
    
    def count_documents(self, collection_name: str, filter_dict: Dict[str, Any] = None) -> int:
        """Zählt Dokumente in einer Collection"""
        collection = self.get_collection(collection_name)
        
        if filter_dict is None:
            filter_dict = {}
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        return collection.count_documents(processed_filter)
    
    def aggregate(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Führt eine Aggregation-Pipeline aus"""
        collection = self.get_collection(collection_name)
        cursor = collection.aggregate(pipeline)
        
        results = []
        for doc in cursor:
            # ObjectId zu String konvertieren
            doc['_id'] = str(doc['_id'])
            results.append(doc)
        
        return results
    
    def distinct(self, collection_name: str, field: str, filter_dict: Dict[str, Any] = None) -> List[Any]:
        """Gibt eindeutige Werte eines Feldes zurück"""
        collection = self.get_collection(collection_name)
        
        if filter_dict is None:
            filter_dict = {}
        
        # Konvertiere String-IDs zu ObjectIds in filter_dict
        processed_filter = self._process_filter_ids(filter_dict)
        
        return list(collection.distinct(field, processed_filter))
    
    def create_index(self, collection_name: str, field: str, unique: bool = False, sparse: bool = False):
        """Erstellt einen Index für eine Collection"""
        collection = self.get_collection(collection_name)
        try:
            # Prüfe ob Index bereits existiert
            existing_indexes = collection.list_indexes()
            index_name = f"{field}_1"
            
            for index in existing_indexes:
                if index['name'] == index_name:
                    # Index existiert bereits, überspringe
                    return
            
            # Erstelle Index nur wenn er nicht existiert
            collection.create_index(field, unique=unique, sparse=sparse)
        except Exception as e:
            # Ignoriere Fehler wenn Index bereits existiert
            if "already exists" not in str(e) and "IndexKeySpecsConflict" not in str(e):
                raise e
    
    def drop_collection(self, collection_name: str):
        """Löscht eine Collection"""
        collection = self.get_collection(collection_name)
        collection.drop()
    
    def close(self):
        """Schließt die MongoDB-Verbindung"""
        if self._client:
            self._client.close()
            logger.info("MongoDB-Verbindung geschlossen")
    
    def backup_collection(self, collection_name: str, backup_path: str):
        """Erstellt ein Backup einer Collection"""
        collection = self.get_collection(collection_name)
        documents = list(collection.find({}))
        
        # ObjectIds zu Strings konvertieren
        for doc in documents:
            doc['_id'] = str(doc['_id'])
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(documents, f, default=str, indent=2, ensure_ascii=False)
        
        logger.info(f"Backup erstellt: {backup_path}")
    
    def restore_collection(self, collection_name: str, backup_path: str):
        """Stellt eine Collection aus einem Backup wieder her"""
        with open(backup_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        
        # Collection leeren
        self.drop_collection(collection_name)
        
        # Dokumente wiederherstellen
        if documents:
            self.insert_many(collection_name, documents)
        
        logger.info(f"Collection wiederhergestellt: {collection_name}")

# Alias für einfacheren Import
MongoDB = MongoDBDatabase

# Globale Instanz (lazy initialization)
_mongodb_instance = None

def get_mongodb():
    """Lazy initialization der MongoDB-Instanz"""
    global _mongodb_instance
    if _mongodb_instance is None:
        _mongodb_instance = MongoDBDatabase()
    return _mongodb_instance

# Alias für Rückwärtskompatibilität - wird erst bei Verwendung initialisiert
class LazyMongoDB:
    def __getattr__(self, name):
        return getattr(get_mongodb(), name)

mongodb = LazyMongoDB() 

def get_feature_settings():
    """Holt alle Feature-Einstellungen"""
    try:
        # Fallback: Standard-Einstellungen wenn MongoDB nicht verfügbar
        default_settings = {
            'tools': True,
            'consumables': True,
            'workers': True,
            'lending_system': True,
            'ticket_system': True,
            'timesheet': True,
            'media_management': True,
            'software_management': False,
            'job_board': False,
            'weekly_reports': False
        }
        
        # Versuche MongoDB zu verwenden
        try:
            settings = {}
            rows = mongodb.find('settings', {'key': {'$regex': '^feature_'}})
            
            for row in rows:
                feature_name = row['key'].replace('feature_', '')
                settings[feature_name] = row.get('value', False)
            
            # Kombiniere mit Standard-Einstellungen
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            
            return settings
        except:
            # Fallback zu Standard-Einstellungen
            return default_settings
            
    except Exception as e:
        print(f"Fehler beim Laden der Feature-Einstellungen: {e}")
        return {
            'tools': True,
            'consumables': True,
            'workers': True,
            'lending_system': True,
            'ticket_system': True,
            'timesheet': True,
            'media_management': True,
            'software_management': False,
            'job_board': False,
            'weekly_reports': False
        }

def set_feature_setting(feature_name, enabled):
    """Setzt eine Feature-Einstellung"""
    try:
        mongodb.update_one('settings', 
                         {'key': f'feature_{feature_name}'}, 
                         {'$set': {'value': enabled}}, 
                         upsert=True)
        return True
    except Exception as e:
        print(f"Fehler beim Setzen der Feature-Einstellung: {e}")
        return False

def is_feature_enabled(feature_name):
    """Prüft ob ein Feature aktiviert ist"""
    try:
        # Standard-Einstellungen
        default_settings = {
            'tools': True,
            'consumables': True,
            'workers': True,
            'lending_system': True,
            'ticket_system': True,
            'timesheet': True,
            'media_management': True,
            'software_management': False,
            'job_board': False,
            'weekly_reports': False
        }
        
        # Versuche aus MongoDB zu lesen
        try:
            setting = mongodb.find_one('settings', {'key': f'feature_{feature_name}'})
            return setting.get('value', default_settings.get(feature_name, False)) if setting else default_settings.get(feature_name, False)
        except:
            # Fallback zu Standard-Einstellungen
            return default_settings.get(feature_name, False)
            
    except Exception as e:
        print(f"Fehler beim Prüfen der Feature-Einstellung: {e}")
        return True  # Standardmäßig aktiviert für Sicherheit 