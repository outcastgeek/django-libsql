"""
Database features for libSQL.
"""
from django.db.backends.sqlite3.features import DatabaseFeatures as SQLiteFeatures


class DatabaseFeatures(SQLiteFeatures):
    """
    libSQL database features.
    """
    # libSQL can rollback DDL in transactions
    can_rollback_ddl = True
    
    # libSQL works with autocommit
    uses_autocommit = True
    
    # libSQL supports transactions
    supports_transactions = True
    
    # libSQL supports atomic operations
    supports_atomic_references_rename = True
    
    # Disable savepoints for now - libSQL handles them differently
    uses_savepoints = False
    supports_savepoints = False
    
    # libSQL handles transactions at the connection level
    autocommits_when_autocommit_is_off = False
    
    # Force Django to close connections between requests/threads
    # This is crucial for libSQL which isn't thread-safe
    connection_persists_old_columns = False