"""
Database features for libSQL.
"""

from django.db.backends.sqlite3.features import DatabaseFeatures as SQLiteFeatures
from django.utils.functional import cached_property


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
    
    @cached_property
    def can_return_columns_from_insert(self):
        """
        Override parent's RETURNING support only for embedded replica mode.
        
        In embedded replica mode, writes go to REMOTE but reads come from LOCAL.
        RETURNING clauses try to read immediately after write, which fails
        because LOCAL hasn't synced yet, so we must disable it.
        
        For non-embedded mode, we inherit Django's SQLite implementation which
        checks for SQLite >= 3.35 (when RETURNING was introduced).
        """
        # Check if we're in embedded replica mode
        is_embedded = self.connection.settings_dict.get('SYNC_URL') is not None
        if is_embedded:
            # Disable RETURNING for embedded replicas due to write/read split
            return False
        
        # For non-embedded mode, use parent's implementation
        # Django's SQLite backend checks: Database.sqlite_version_info >= (3, 35)
        return super().can_return_columns_from_insert
    
    @cached_property
    def can_return_rows_from_bulk_insert(self):
        """
        Disable bulk insert RETURNING for embedded replica mode.
        
        Same reason as can_return_columns_from_insert.
        """
        # Just return the same value as can_return_columns_from_insert
        # This matches what SQLite does with its property
        return self.can_return_columns_from_insert
