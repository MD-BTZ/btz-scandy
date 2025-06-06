"""
Base model class that provides common database operations.

This module defines the BaseModel class which serves as the foundation for all
application models, providing common CRUD operations and database utilities.
"""
import sqlite3
import logging
import json
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, Tuple, Callable, Iterator, ContextManager
from pathlib import Path
import os
from datetime import datetime
from contextlib import contextmanager
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for type hints
T = TypeVar('T', bound='BaseModel')

# Database operation types for type hints
QueryResult = Union[List[Dict[str, Any]], Dict[str, Any], int, bool, None]

class QueryType(Enum):
    """Enum for query result types."""
    ALL = "all"
    ONE = "one"
    EXECUTE = "execute"
    SCALAR = "scalar"

class BaseModel:
    """
    Base class for all database models.
    
    This class provides common database operations (CRUD) and utilities
    for interacting with SQLite databases. It uses the active record pattern
    and provides both class and instance methods for database operations.
    
    Attributes:
        TABLE_NAME (str): The name of the database table. Must be overridden by subclasses.
    """
    
    # This must be overridden by subclasses
    TABLE_NAME: str = None
    
    def __init__(self, **kwargs):
        """Initialize model with data from a database row.
        
        Args:
            **kwargs: Column names and values from the database row
        """
        for key, value in kwargs.items():
            # Convert string timestamps to datetime objects
            if key.endswith('_at') and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
            setattr(self, key, value)
    
    def __repr__(self) -> str:
        """Return a string representation of the model."""
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.to_dict().items())
        return f"<{self.__class__.__name__}({attrs})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary."""
        return {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in self.__dict__.items()
            if not key.startswith('_')
        }
    
    @classmethod
    def get_connection(cls, db_path: str = None) -> sqlite3.Connection:
        """Get a database connection.
        
        Args:
            db_path: Optional path to the database file. If not provided,
                   uses the default from config.
                   
        Returns:
            sqlite3.Connection: A connection to the database
        """
        if db_path is None:
            from app.config import Config
            db_path = os.path.join(Config.BASE_DIR, 'app', 'database', 'inventory.db')
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON;")
        
        return conn
    
    @classmethod
    @contextmanager
    def get_cursor(
        cls, 
        db_path: str = None,
        isolation_level: str = None
    ) -> ContextManager[sqlite3.Cursor]:
        """Context manager for database operations.
        
        Args:
            db_path: Optional path to the database file
            isolation_level: SQLite isolation level (None, 'DEFERRED', 'IMMEDIATE', 'EXCLUSIVE')
            
        Yields:
            sqlite3.Cursor: A database cursor
        """
        conn = cls.get_connection(db_path)
        if isolation_level:
            conn.isolation_level = isolation_level
            
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    @classmethod
    def query_all(
        cls, 
        query: str, 
        params: tuple = (), 
        db_path: str = None
    ) -> List[Dict[str, Any]]:
        """Execute a query and return all results as dictionaries.
        
        Args:
            query: SQL query string
            params: Parameters for the query
            db_path: Optional path to the database file
            
        Returns:
            List[Dict[str, Any]]: List of rows as dictionaries
        """
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    @classmethod
    def query_one(
        cls, 
        query: str, 
        params: tuple = (), 
        db_path: str = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a query and return the first result as a dictionary.
        
        Args:
            query: SQL query string
            params: Parameters for the query
            db_path: Optional path to the database file
            
        Returns:
            Optional[Dict[str, Any]]: The first row as a dictionary, or None if no results
        """
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            if result is None:
                return None
            columns = [column[0] for column in cursor.description]
            return dict(zip(columns, result))
    
    @classmethod
    def execute(
        cls, 
        query: str, 
        params: tuple = (), 
        db_path: str = None,
        return_lastrowid: bool = False
    ) -> Union[int, None]:
        """Execute a write operation (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query string
            params: Parameters for the query
            db_path: Optional path to the database file
            return_lastrowid: If True, return the last inserted row ID
            
        Returns:
            Union[int, None]: The last inserted row ID if return_lastrowid is True,
                            otherwise None
        """
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(query, params)
            if return_lastrowid and "INSERT" in query.upper():
                return cursor.lastrowid
            return None
    
    # CRUD Operations
    
    @classmethod
    def get_all(cls: Type[T], where: str = None, params: tuple = (), db_path: str = None) -> List[T]:
        """Get all records from the table, optionally filtered by a WHERE clause."""
        query = f"SELECT * FROM {cls.TABLE_NAME}"
        if where:
            query += f" WHERE {where}"
        
        results = cls.query_all(query, params, db_path)
        return [cls(**row) for row in results]
    
    @classmethod
    def get_by_id(cls: Type[T], id: int, db_path: str = None) -> Optional[T]:
        """Get a record by its ID."""
        result = cls.query_one(f"SELECT * FROM {cls.TABLE_NAME} WHERE id = ?", (id,), db_path)
        return cls(**result) if result else None
    
    @classmethod
    def get_by_field(cls: Type[T], field: str, value: Any, db_path: str = None) -> Optional[T]:
        """Get a record by a specific field."""
        result = cls.query_one(f"SELECT * FROM {cls.TABLE_NAME} WHERE {field} = ?", (value,), db_path)
        return cls(**result) if result else None
    
    @classmethod
    def create(
        cls, 
        data: Dict[str, Any], 
        db_path: str = None,
        ignore_conflicts: bool = False
    ) -> Optional[int]:
        """Create a new record in the database.
        
        Args:
            data: Dictionary of column names and values
            db_path: Optional path to the database file
            ignore_conflicts: If True, silently ignore duplicate key errors
            
        Returns:
            Optional[int]: The ID of the created record, or None if failed
        """
        if not cls.TABLE_NAME:
            raise ValueError("TABLE_NAME must be set in the model class")
        
        if not data:
            raise ValueError("No data provided for creation")
            
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        
        # Handle ON CONFLICT for INSERT
        on_conflict = ""
        if ignore_conflicts:
            on_conflict = " ON CONFLICT DO NOTHING"
            
        query = f"""
            INSERT INTO {cls.TABLE_NAME} ({columns}) 
            VALUES ({placeholders})
            {on_conflict}
        """.strip()
        
        try:
            with cls.get_cursor(db_path) as cursor:
                cursor.execute(query, tuple(data.values()))
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e) and ignore_conflicts:
                return None
            logger.error(f"Error creating record: {e}")
            raise
    
    @classmethod
    def update(
        cls, 
        id: int, 
        data: Dict[str, Any], 
        db_path: str = None,
        where: str = None,
        where_params: tuple = None
    ) -> bool:
        """Update an existing record in the database.
        
        Args:
            id: The ID of the record to update
            data: Dictionary of column names and new values
            db_path: Optional path to the database file
            where: Optional WHERE clause (without the WHERE keyword)
            where_params: Parameters for the WHERE clause
            
        Returns:
            bool: True if the record was updated, False otherwise
        """
        if not cls.TABLE_NAME:
            raise ValueError("TABLE_NAME must be set in the model class")
            
        if not data:
            raise ValueError("No data provided for update")
            
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        
        # Build the WHERE clause
        where_clause = "WHERE id = ?"
        params = list(data.values())
        
        if where:
            where_clause = f"WHERE {where} AND id = ?"
            if where_params:
                params.extend(where_params)
        
        params.append(id)
        
        query = f"""
            UPDATE {cls.TABLE_NAME} 
            SET {set_clause} 
            {where_clause}
        """.strip()
        
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(query, tuple(params))
            return cursor.rowcount > 0
    
    @classmethod
    def delete(
        cls, 
        id: int, 
        db_path: str = None,
        soft_delete: bool = True,
        where: str = None,
        where_params: tuple = None
    ) -> bool:
        """Delete a record from the database.
        
        Args:
            id: The ID of the record to delete
            db_path: Optional path to the database file
            soft_delete: If True, mark as deleted instead of hard delete
            where: Optional additional WHERE conditions (without the WHERE keyword)
            where_params: Parameters for the WHERE clause
            
        Returns:
            bool: True if the record was deleted, False otherwise
        """
        if not cls.TABLE_NAME:
            raise ValueError("TABLE_NAME must be set in the model class")
        
        # Build the WHERE clause
        where_clause = "WHERE id = ?"
        params = []
        
        if where:
            where_clause = f"WHERE {where} AND id = ?"
            if where_params:
                params.extend(where_params)
        
        params.append(id)
            
        if soft_delete and cls.column_exists('deleted'):
            query = f"""
                UPDATE {cls.TABLE_NAME} 
                SET deleted = 1, deleted_at = CURRENT_TIMESTAMP 
                {where_clause}
            """.strip()
        else:
            query = f"DELETE FROM {cls.TABLE_NAME} {where_clause}"
        
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(query, tuple(params))
            return cursor.rowcount > 0
    
    @classmethod
    def get_by_id(
        cls, 
        id: int, 
        db_path: str = None,
        include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a record by its ID.
        
        Args:
            id: The ID of the record to retrieve
            db_path: Optional path to the database file
            include_deleted: If True, include soft-deleted records
            
        Returns:
            Optional[Dict[str, Any]]: The record as a dictionary, or None if not found
        """
        if not cls.TABLE_NAME:
            raise ValueError("TABLE_NAME must be set in the model class")
            
        where_clause = "WHERE id = ?"
        if not include_deleted and cls.column_exists('deleted'):
            where_clause += " AND (deleted = 0 OR deleted IS NULL)"
            
        query = f"SELECT * FROM {cls.TABLE_NAME} {where_clause}"
        return cls.query_one(query, (id,), db_path)
    
    @classmethod
    def get_all(
        cls, 
        db_path: str = None, 
        include_deleted: bool = False,
        order_by: str = None,
        limit: int = None,
        offset: int = None
    ) -> List[Dict[str, Any]]:
        """Get all records from the table.
        
        Args:
            db_path: Optional path to the database file
            include_deleted: If True, include soft-deleted records
            order_by: Optional ORDER BY clause (without the ORDER BY keyword)
            limit: Optional maximum number of records to return
            offset: Optional number of records to skip
            
        Returns:
            List[Dict[str, Any]]: List of records as dictionaries
        """
        if not cls.TABLE_NAME:
            raise ValueError("TABLE_NAME must be set in the model class")
            
        where_clause = ""
        if not include_deleted and cls.column_exists('deleted'):
            where_clause = "WHERE deleted = 0 OR deleted IS NULL"
            
        order_by_clause = f"ORDER BY {order_by}" if order_by else ""
        limit_clause = f"LIMIT {limit}" if limit is not None else ""
        offset_clause = f"OFFSET {offset}" if offset is not None else ""
        
        query = f"""
            SELECT * FROM {cls.TABLE_NAME}
            {where_clause}
            {order_by_clause}
            {limit_clause}
            {offset_clause}
        """.strip()
        
        return cls.query_all(query, db_path=db_path)
    
    # Utility Methods
    
    @classmethod
    def count(
        cls, 
        where: str = None, 
        params: tuple = None,
        db_path: str = None,
        include_deleted: bool = False
    ) -> int:
        """Count records matching the given conditions.
        
        Args:
            where: Optional WHERE clause (without the WHERE keyword)
            params: Parameters for the WHERE clause
            db_path: Optional path to the database file
            include_deleted: If True, include soft-deleted records
            
        Returns:
            int: The number of matching records
        """
        where_clause = ""
        query_params = []
        
        if not include_deleted and cls.column_exists('deleted'):
            where_clause = "WHERE deleted = 0 OR deleted IS NULL"
            
        if where:
            if where_clause:
                where_clause += f" AND ({where})"
            else:
                where_clause = f"WHERE {where}"
            
            if params:
                query_params.extend(params)
        
        query = f"SELECT COUNT(*) as count FROM {cls.TABLE_NAME} {where_clause}"
        
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(query, tuple(query_params))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    @classmethod
    def exists(
        cls, 
        column: str, 
        value: Any, 
        exclude_id: int = None,
        db_path: str = None
    ) -> bool:
        """Check if a record exists with the given column value.
        
        Args:
            column: The column to check
            value: The value to look for
            exclude_id: Optional ID to exclude from the check
            db_path: Optional path to the database file
            
        Returns:
            bool: True if a matching record exists, False otherwise
        """
        query = f"SELECT 1 FROM {cls.TABLE_NAME} WHERE {column} = ?"
        params = [value]
        
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)
        
        if cls.column_exists('deleted'):
            query += " AND (deleted = 0 OR deleted IS NULL)"
            
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(query, tuple(params))
            return cursor.fetchone() is not None
    
    @classmethod
    def column_exists(cls, column_name: str, db_path: str = None) -> bool:
        """Check if a column exists in the table.
        
        Args:
            column_name: The name of the column to check
            db_path: Optional path to the database file
            
        Returns:
            bool: True if the column exists, False otherwise
        """
        with cls.get_cursor(db_path) as cursor:
            try:
                # Try to select the column with a LIMIT 0 query
                cursor.execute(f"SELECT {column_name} FROM {cls.TABLE_NAME} LIMIT 0")
                return True
            except sqlite3.OperationalError:
                return False
    
    @classmethod
    def table_exists(cls, db_path: str = None) -> bool:
        """Check if the table exists in the database.
        
        Args:
            db_path: Optional path to the database file
            
        Returns:
            bool: True if the table exists, False otherwise
        """
        with cls.get_cursor(db_path) as cursor:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (cls.TABLE_NAME,)
            )
            return cursor.fetchone() is not None
    
    def update(self, data: Dict[str, Any], db_path: str = None) -> None:
        """Update the current record."""
        if not hasattr(self, 'id'):
            raise ValueError("Cannot update a record without an ID")
            
        set_clause = ', '.join(f"{key} = ?" for key in data.keys())
        query = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE id = ?"
        
        params = list(data.values()) + [self.id]
        self.execute(query, tuple(params), db_path)
        
        # Update the instance with new values
        for key, value in data.items():
            setattr(self, key, value)
    
    def delete(self, db_path: str = None) -> None:
        """Delete the current record."""
        if not hasattr(self, 'id'):
            raise ValueError("Cannot delete a record without an ID")
            
        query = f"DELETE FROM {self.TABLE_NAME} WHERE id = ?"
        self.execute(query, (self.id,), db_path)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the model
        """
        return {
            key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in self.__dict__.items()
            if not key.startswith('_')
        }

    @classmethod
    def exists(
        cls,
        field: str,
        value: Any,
        db_path: str = None,
        **kwargs
    ) -> bool:
        """Check if a record exists with the given field value.
        
        This is a convenience method that wraps the more feature-rich exists() method.
        For more complex existence checks, use the class method directly.
        
        Args:
            field: The field to check
            value: The value to look for
            db_path: Optional path to the database file
            **kwargs: Additional arguments to pass to the exists() method
            
        Returns:
            bool: True if a matching record exists, False otherwise
        """
        return cls.exists(column=field, value=value, db_path=db_path, **kwargs)
