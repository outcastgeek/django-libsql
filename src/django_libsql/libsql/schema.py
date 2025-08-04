"""
Custom schema editor for libSQL to ensure migrations commit properly.
"""

from django.db.backends.sqlite3.schema import DatabaseSchemaEditor as SQLiteSchemaEditor


class DatabaseSchemaEditor(SQLiteSchemaEditor):
    """
    Custom schema editor that ensures changes are committed to Turso.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override atomic_migration to False for Turso
        # Turso doesn't support nested transactions well, and we need
        # to ensure DDL statements are committed immediately.
        self._atomic_migration = False
    
    @property
    def atomic_migration(self):
        """Disable atomic migrations for Turso."""
        return self._atomic_migration
    
    @atomic_migration.setter
    def atomic_migration(self, value):
        """Always keep atomic_migration False for Turso."""
        self._atomic_migration = False

