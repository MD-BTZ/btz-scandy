"""
MongoDB-Datenbankmodul für Scandy
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from datetime import datetime
import logging
from bson import ObjectId
from app.config.config import config
import json
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

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
        """Stellt die Verbindung zur MongoDB her"""
        try:
            current_config = config['default']()
            
            # MongoDB-Client mit Authentifizierung erstellen
            # Verwende die MONGODB_URI direkt, da sie bereits die Authentifizierung enthält
            self._client = MongoClient(
                current_config.MONGODB_URI,
                serverSelectionTimeoutMS=10000,  # Erhöhe Timeout für Docker
                connectTimeoutMS=10000,
                retryWrites=True,
                w='majority'
            )
            
            # Teste die Verbindung
            self._client.admin.command('ping')
            
            self._db = self._client[current_config.MONGODB_DB]
            logger.info(f"MongoDB-Verbindung erfolgreich mit '{current_config.MONGODB_DB}' hergestellt.")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB-Verbindungsfehler: {str(e)}")
            logger.error(f"Verwendete URI: {current_config.MONGODB_URI}")
            logger.error("Bitte stellen Sie sicher, dass:")
            logger.error("1. MongoDB läuft und erreichbar ist")
            logger.error("2. Die Authentifizierungsdaten korrekt sind")
            logger.error("3. Der Container-Name in der MONGODB_URI korrekt ist")
            raise
    
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
        result = collection.find_one(filter_dict)
        
        if result:
            # ObjectId zu String konvertieren
            result['_id'] = str(result['_id'])
        
        return result
    
    def find(self, collection_name: str, filter_dict: Dict[str, Any] = None, 
             sort: List[tuple] = None, limit: int = None) -> List[Dict[str, Any]]:
        """Findet mehrere Dokumente in einer Collection"""
        collection = self.get_collection(collection_name)
        
        if filter_dict is None:
            filter_dict = {}
        
        cursor = collection.find(filter_dict)
        
        if sort:
            cursor = cursor.sort(sort)
        
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
        
        # updated_at Timestamp hinzufügen
        if '$set' in update_dict:
            update_dict['$set']['updated_at'] = datetime.now()
        else:
            # Erstelle $set Modifier falls nicht vorhanden
            update_dict = {'$set': {**update_dict, 'updated_at': datetime.now()}}
        
        result = collection.update_one(filter_dict, update_dict, upsert=upsert)
        return result.modified_count > 0 or result.upserted_id is not None
    
    def update_many(self, collection_name: str, filter_dict: Dict[str, Any], 
                    update_dict: Dict[str, Any]) -> int:
        """Aktualisiert mehrere Dokumente in einer Collection"""
        collection = self.get_collection(collection_name)
        
        # updated_at Timestamp hinzufügen
        if '$set' in update_dict:
            update_dict['$set']['updated_at'] = datetime.now()
        else:
            # Erstelle $set Modifier falls nicht vorhanden
            update_dict = {'$set': {**update_dict, 'updated_at': datetime.now()}}
        
        result = collection.update_many(filter_dict, update_dict)
        return result.modified_count
    
    def delete_one(self, collection_name: str, filter_dict: Dict[str, Any]) -> bool:
        """Löscht ein Dokument aus einer Collection"""
        collection = self.get_collection(collection_name)
        result = collection.delete_one(filter_dict)
        return result.deleted_count > 0
    
    def delete_many(self, collection_name: str, filter_dict: Dict[str, Any]) -> int:
        """Löscht mehrere Dokumente aus einer Collection"""
        collection = self.get_collection(collection_name)
        result = collection.delete_many(filter_dict)
        return result.deleted_count
    
    def count_documents(self, collection_name: str, filter_dict: Dict[str, Any] = None) -> int:
        """Zählt Dokumente in einer Collection"""
        collection = self.get_collection(collection_name)
        
        if filter_dict is None:
            filter_dict = {}
        
        return collection.count_documents(filter_dict)
    
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
    
    def create_index(self, collection_name: str, field: str, unique: bool = False):
        """Erstellt einen Index für eine Collection"""
        collection = self.get_collection(collection_name)
        collection.create_index(field, unique=unique)
    
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

# Globale Instanz
mongodb = MongoDBDatabase() 