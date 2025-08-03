"""
Custom schema editor for libSQL to ensure migrations commit properly.
"""
from django.db.backends.sqlite3.schema import DatabaseSchemaEditor as SQLiteSchemaEditor


class DatabaseSchemaEditor(SQLiteSchemaEditor):
    """
    Custom schema editor that ensures changes are committed to Turso.
    """
    
    def __enter__(self):
        """Ensure we're in autocommit mode for schema changes."""
        super().__enter__()
        # Don't change autocommit if we're in an atomic block
        if not self.connection.in_atomic_block:
            self.connection.set_autocommit(True)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Override to ensure migrations are committed."""
        # Call parent's __exit__
        super().__exit__(exc_type, exc_value, traceback)
        
        # If no exception, force a commit to ensure changes persist in Turso
        if exc_type is None:
            self.connection.commit()