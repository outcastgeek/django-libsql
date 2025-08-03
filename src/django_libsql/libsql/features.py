"""
Database features for libSQL.
"""
from django.db.backends.sqlite3.features import DatabaseFeatures as SQLiteFeatures


class DatabaseFeatures(SQLiteFeatures):
    """
    libSQL database features.
    """
    # libSQL requires explicit commits for DDL operations
    can_rollback_ddl = False
    
    # libSQL works best with autocommit
    uses_autocommit = True
    
    # libSQL supports transactions but handles them differently
    supports_transactions = True
    
    # Disable savepoints for Turso remote connections
    uses_savepoints = False
    
    # libSQL/Turso doesn't support nested transactions the same way
    supports_savepoints = False