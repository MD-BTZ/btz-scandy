"""
MongoDB-Modelle für Scandy - Vollständige Implementierung
"""
from app.models.mongodb_database import mongodb
from app.config.config import config
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class BaseModel:
    """Basis-Klasse für MongoDB-Modelle"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self):
        """Konvertiert das Objekt in ein Dictionary"""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                data[key] = value
        return data

class MongoDBTool:
    """MongoDB-Modell für Werkzeuge"""
    
    COLLECTION_NAME = 'tools'
    
    @classmethod
    def create(cls, tool_data: Dict[str, Any]) -> str:
        """Erstellt ein neues Werkzeug"""
        return mongodb.insert_one(cls.COLLECTION_NAME, tool_data)
    
    @classmethod
    def get_by_id(cls, tool_id: str) -> Optional[Dict[str, Any]]:
        """Holt ein Werkzeug anhand der ID"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': tool_id})
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Holt ein Werkzeug anhand des Barcodes"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'barcode': barcode})
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Werkzeuge"""
        return mongodb.find(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def get_all_with_status(cls) -> List[Dict[str, Any]]:
        """Holt alle Werkzeuge mit Ausleihstatus"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$lookup': {
                    'from': 'lendings',
                    'let': {'tool_barcode': '$barcode'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$tool_barcode', '$$tool_barcode']},
                                        {'$eq': ['$returned_at', None]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'active_lending'
                }
            },
            {
                '$lookup': {
                    'from': 'workers',
                    'let': {'worker_barcode': {'$arrayElemAt': ['$active_lending.worker_barcode', 0]}},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {'$eq': ['$barcode', '$$worker_barcode']}
                            }
                        }
                    ],
                    'as': 'current_borrower'
                }
            },
            {
                '$addFields': {
                    'current_borrower_name': {
                        '$concat': [
                            {'$arrayElemAt': ['$current_borrower.firstname', 0]},
                            ' ',
                            {'$arrayElemAt': ['$current_borrower.lastname', 0]}
                        ]
                    },
                    'is_lent': {'$gt': [{'$size': '$active_lending'}, 0]}
                }
            },
            {'$sort': {'name': 1}}
        ]
        
        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)
    
    @classmethod
    def update(cls, tool_id: str, update_data: Dict[str, Any]) -> bool:
        """Aktualisiert ein Werkzeug"""
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': tool_id}, update_data)
    
    @classmethod
    def delete(cls, tool_id: str) -> bool:
        """Löscht ein Werkzeug (Soft Delete)"""
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': tool_id}, {'deleted': True})
    
    @classmethod
    def count_active(cls) -> int:
        """Zählt aktive Werkzeuge"""
        return mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def search(cls, search_term: str) -> List[Dict[str, Any]]:
        """Sucht nach Werkzeugen"""
        filter_dict = {
            'deleted': {'$ne': True},
            '$or': [
                {'name': {'$regex': search_term, '$options': 'i'}},
                {'description': {'$regex': search_term, '$options': 'i'}},
                {'barcode': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        return mongodb.find(cls.COLLECTION_NAME, filter_dict)
    
    @classmethod
    def get_lending_history(cls, barcode: str) -> List[Dict[str, Any]]:
        """Holt die Ausleihhistorie für ein Werkzeug"""
        pipeline = [
            {'$match': {'tool_barcode': barcode}},
            {
                '$lookup': {
                    'from': 'workers',
                    'localField': 'worker_barcode',
                    'foreignField': 'barcode',
                    'as': 'worker'
                }
            },
            {
                '$addFields': {
                    'worker_name': {
                        '$concat': [
                            {'$arrayElemAt': ['$worker.firstname', 0]},
                            ' ',
                            {'$arrayElemAt': ['$worker.lastname', 0]}
                        ]
                    },
                    'action': {
                        '$cond': {
                            'if': {'$eq': ['$returned_at', None]},
                            'then': 'Ausgeliehen',
                            'else': 'Zurückgegeben'
                        }
                    },
                    'action_type': 'Ausleihe/Rückgabe',
                    'formatted_lent_at': {
                        '$dateToString': {
                            'format': '%d.%m.%Y %H:%M',
                            'date': '$lent_at'
                        }
                    },
                    'formatted_returned_at': {
                        '$dateToString': {
                            'format': '%d.%m.%Y %H:%M',
                            'date': '$returned_at'
                        }
                    }
                }
            },
            {'$sort': {'_id': -1}}
        ]
        
        return mongodb.aggregate('lendings', pipeline)

class MongoDBWorker:
    """MongoDB-Modell für Mitarbeiter"""
    
    COLLECTION_NAME = 'workers'
    
    @classmethod
    def create(cls, worker_data: Dict[str, Any]) -> str:
        """Erstellt einen neuen Mitarbeiter"""
        return mongodb.insert_one(cls.COLLECTION_NAME, worker_data)
    
    @classmethod
    def get_by_id(cls, worker_id: str) -> Optional[Dict[str, Any]]:
        """Holt einen Mitarbeiter anhand der ID"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': worker_id})
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Holt einen Mitarbeiter anhand des Barcodes"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'barcode': barcode})
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Mitarbeiter"""
        return mongodb.find(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def get_all_with_lendings(cls) -> List[Dict[str, Any]]:
        """Holt alle Mitarbeiter mit aktiven Ausleihen"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$lookup': {
                    'from': 'lendings',
                    'let': {'worker_barcode': '$barcode'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$worker_barcode', '$$worker_barcode']},
                                        {'$eq': ['$returned_at', None]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'active_lendings'
                }
            },
            {
                '$addFields': {
                    'active_lendings_count': {'$size': '$active_lendings'}
                }
            },
            {'$sort': {'lastname': 1, 'firstname': 1}}
        ]
        
        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)
    
    @classmethod
    def update(cls, worker_id: str, update_data: Dict[str, Any]) -> bool:
        """Aktualisiert einen Mitarbeiter"""
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': worker_id}, update_data)
    
    @classmethod
    def delete(cls, worker_id: str) -> bool:
        """Löscht einen Mitarbeiter (Soft Delete)"""
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': worker_id}, {'deleted': True})
    
    @classmethod
    def count_active(cls) -> int:
        """Zählt aktive Mitarbeiter"""
        return mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def search(cls, search_term: str) -> List[Dict[str, Any]]:
        """Sucht nach Mitarbeitern"""
        filter_dict = {
            'deleted': {'$ne': True},
            '$or': [
                {'firstname': {'$regex': search_term, '$options': 'i'}},
                {'lastname': {'$regex': search_term, '$options': 'i'}},
                {'barcode': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        return mongodb.find(cls.COLLECTION_NAME, filter_dict)

class MongoDBConsumable:
    """MongoDB-Modell für Verbrauchsmaterialien"""
    
    COLLECTION_NAME = 'consumables'
    
    @classmethod
    def create(cls, consumable_data: Dict[str, Any]) -> str:
        """Erstellt ein neues Verbrauchsmaterial"""
        return mongodb.insert_one(cls.COLLECTION_NAME, consumable_data)
    
    @classmethod
    def get_by_id(cls, consumable_id: str) -> Optional[Dict[str, Any]]:
        """Holt ein Verbrauchsmaterial anhand der ID"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': consumable_id})
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Holt ein Verbrauchsmaterial anhand des Barcodes"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'barcode': barcode})
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Verbrauchsmaterialien"""
        return mongodb.find(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """Holt alle Verbrauchsmaterialien mit Bestandsstatus"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$addFields': {
                    'stock_status': {
                        '$cond': {
                            'if': {'$lte': ['$quantity', '$min_quantity']},
                            'then': 'Nachbestellen',
                            'else': 'OK'
                        }
                    }
                }
            },
            {'$sort': {'name': 1}}
        ]
        
        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)
    
    @classmethod
    def get_forecast(cls) -> List[Dict[str, Any]]:
        """Berechnet die Bestandsprognose für Verbrauchsmaterialien"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}, 'quantity': {'$gt': 0}}},
            {
                '$lookup': {
                    'from': 'consumable_usages',
                    'let': {'consumable_barcode': '$barcode'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$consumable_barcode', '$$consumable_barcode']},
                                        {'$gte': ['$used_at', {'$dateSubtract': {'startDate': '$$NOW', 'unit': 'day', 'amount': 30}}]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'recent_usage'
                }
            },
            {
                '$addFields': {
                    'avg_daily_usage': {
                        '$divide': [
                            {'$sum': '$recent_usage.quantity'},
                            30
                        ]
                    }
                }
            },
            {
                '$addFields': {
                    'days_remaining': {
                        '$cond': {
                            'if': {'$gt': ['$avg_daily_usage', 0]},
                            'then': {'$divide': ['$quantity', '$avg_daily_usage']},
                            'else': 999
                        }
                    }
                }
            },
            {'$sort': {'days_remaining': 1}},
            {'$limit': 10}
        ]
        
        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)
    
    @classmethod
    def update(cls, consumable_id: str, update_data: Dict[str, Any]) -> bool:
        """Aktualisiert ein Verbrauchsmaterial"""
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': consumable_id}, update_data)
    
    @classmethod
    def delete(cls, consumable_id: str) -> bool:
        """Löscht ein Verbrauchsmaterial (Soft Delete)"""
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': consumable_id}, {'deleted': True})
    
    @classmethod
    def count_active(cls) -> int:
        """Zählt aktive Verbrauchsmaterialien"""
        return mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def search(cls, search_term: str) -> List[Dict[str, Any]]:
        """Sucht nach Verbrauchsmaterialien"""
        filter_dict = {
            'deleted': {'$ne': True},
            '$or': [
                {'name': {'$regex': search_term, '$options': 'i'}},
                {'description': {'$regex': search_term, '$options': 'i'}},
                {'barcode': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        return mongodb.find(cls.COLLECTION_NAME, filter_dict)

class MongoDBLending:
    """MongoDB-Modell für Ausleihen"""
    
    COLLECTION_NAME = 'lendings'
    
    @classmethod
    def create(cls, lending_data: Dict[str, Any]) -> str:
        """Erstellt eine neue Ausleihe"""
        return mongodb.insert_one(cls.COLLECTION_NAME, lending_data)
    
    @classmethod
    def get_by_id(cls, lending_id: str) -> Optional[Dict[str, Any]]:
        """Holt eine Ausleihe anhand der ID"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': lending_id})
    
    @classmethod
    def get_active_by_tool(cls, tool_id: str) -> Optional[Dict[str, Any]]:
        """Holt die aktive Ausleihe für ein Werkzeug"""
        return mongodb.find_one(cls.COLLECTION_NAME, {
            'tool_id': tool_id,
            'returned_at': {'$exists': False}
        })
    
    @classmethod
    def get_active_by_worker(cls, worker_id: str) -> List[Dict[str, Any]]:
        """Holt alle aktiven Ausleihen eines Mitarbeiters"""
        return mongodb.find(cls.COLLECTION_NAME, {
            'worker_id': worker_id,
            'returned_at': {'$exists': False}
        })
    
    @classmethod
    def get_active_lendings(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Ausleihen"""
        return mongodb.find(cls.COLLECTION_NAME, {'returned_at': {'$exists': False}})
    
    @classmethod
    def get_lendings_by_worker(cls, worker_barcode: str) -> List[Dict[str, Any]]:
        """Holt alle Ausleihen eines Mitarbeiters"""
        return mongodb.find(cls.COLLECTION_NAME, {'worker_barcode': worker_barcode})
    
    @classmethod
    def get_lendings_by_tool(cls, tool_barcode: str) -> List[Dict[str, Any]]:
        """Holt alle Ausleihen eines Werkzeugs"""
        return mongodb.find(cls.COLLECTION_NAME, {'tool_barcode': tool_barcode})
    
    @classmethod
    def return_tool(cls, lending_id: str) -> bool:
        """Gibt ein Werkzeug zurück"""
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': lending_id}, {
            'returned_at': datetime.now()
        })
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Ausleihen"""
        return mongodb.find(cls.COLLECTION_NAME, {'returned_at': {'$exists': False}})

class MongoDBConsumableUsage:
    """MongoDB-Modell für Verbrauchsmaterial-Verwendung"""
    
    COLLECTION_NAME = 'consumable_usages'
    
    @classmethod
    def create(cls, usage_data: Dict[str, Any]) -> str:
        """Erstellt einen neuen Verbrauchsmaterial-Verbrauch"""
        return mongodb.insert_one(cls.COLLECTION_NAME, usage_data)
    
    @classmethod
    def get_by_consumable(cls, consumable_id: str) -> List[Dict[str, Any]]:
        """Holt alle Verwendungen eines Verbrauchsmaterials"""
        return mongodb.find(cls.COLLECTION_NAME, {'consumable_id': consumable_id})
    
    @classmethod
    def get_by_worker(cls, worker_id: str) -> List[Dict[str, Any]]:
        """Holt alle Verwendungen eines Mitarbeiters"""
        return mongodb.find(cls.COLLECTION_NAME, {'worker_id': worker_id})
    
    @classmethod
    def get_usage_by_worker(cls, worker_barcode: str, days: int = 30) -> List[Dict[str, Any]]:
        """Holt den Verbrauch eines Mitarbeiters"""
        from datetime import timedelta
        
        start_date = datetime.now() - timedelta(days=days)
        
        return mongodb.find(
            cls.COLLECTION_NAME, 
            {
                'worker_barcode': worker_barcode,
                'used_at': {'$gte': start_date}
            }
        )

class MongoDBUser:
    """MongoDB-Modell für Benutzer"""
    
    COLLECTION_NAME = 'users'
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Holt einen Benutzer anhand der ID"""
        try:
            # Konvertiere String-ID zu ObjectId
            object_id = ObjectId(user_id)
            return mongodb.find_one(cls.COLLECTION_NAME, {'_id': object_id})
        except Exception as e:
            print(f"DEBUG: Fehler beim Laden des Users mit ID {user_id}: {e}")
            return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional[Dict[str, Any]]:
        """Holt einen Benutzer anhand des Benutzernamens"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'username': username})
    
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """Holt alle Benutzer"""
        return mongodb.find(cls.COLLECTION_NAME, {})

class MongoDBTicket:
    """MongoDB-Modell für Tickets"""
    
    COLLECTION_NAME = 'tickets'
    
    @classmethod
    def get_by_status(cls, status: str) -> List[Dict[str, Any]]:
        """Holt Tickets nach Status"""
        return mongodb.find(cls.COLLECTION_NAME, {'status': status, 'deleted': {'$ne': True}})
    
    @classmethod
    def get_by_assignee(cls, assigned_to: str) -> List[Dict[str, Any]]:
        """Holt Tickets nach Zuweisung"""
        return mongodb.find(cls.COLLECTION_NAME, {'assigned_to': assigned_to, 'deleted': {'$ne': True}})

def create_mongodb_indexes():
    """Erstellt alle notwendigen MongoDB-Indizes und initialisiert die Datenbank"""
    try:
        # Werkzeuge-Indizes
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'barcode', unique=True)
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'name')
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'category')
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'location')
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'status')
        
        # Mitarbeiter-Indizes
        mongodb.create_index(MongoDBWorker.COLLECTION_NAME, 'barcode', unique=True)
        mongodb.create_index(MongoDBWorker.COLLECTION_NAME, 'lastname')
        mongodb.create_index(MongoDBWorker.COLLECTION_NAME, 'department')
        
        # Verbrauchsmaterial-Indizes
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, 'barcode', unique=True)
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, 'name')
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, 'category')
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, 'location')
        
        # Ausleihen-Indizes
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, 'tool_barcode')
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, 'worker_barcode')
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, 'lent_at')
        
        # Verbrauchsmaterial-Verwendung-Indizes
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, 'consumable_barcode')
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, 'worker_barcode')
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, 'used_at')
        
        # Benutzer-Indizes
        mongodb.create_index(MongoDBUser.COLLECTION_NAME, 'username', unique=True)
        mongodb.create_index(MongoDBUser.COLLECTION_NAME, 'email')
        
        # Ticket-Indizes
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, 'status')
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, 'assigned_to')
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, 'created_at')
        
        # Settings-Indizes
        mongodb.create_index('settings', 'key', unique=True)
        
        # Timesheets-Indizes
        mongodb.create_index('timesheets', 'user_id')
        mongodb.create_index('timesheets', 'year')
        mongodb.create_index('timesheets', 'kw')
        
        # Homepage-Notices-Indizes
        mongodb.create_index('homepage_notices', 'is_active')
        mongodb.create_index('homepage_notices', 'priority')
        mongodb.create_index('homepage_notices', 'created_at')
        
        logger.info("MongoDB-Indizes erfolgreich erstellt")
        
        # Datenbankinitialisierung
        from app.utils.database_helpers import ensure_default_settings, migrate_old_data_to_settings
        
        # Stelle sicher, dass die settings Collections existieren
        ensure_default_settings()
        
        # Migriere alte Daten (falls vorhanden)
        migrate_old_data_to_settings()
        
        logger.info("Datenbankinitialisierung abgeschlossen")
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der MongoDB-Indizes: {str(e)}")
        raise 