"""
Database operations for libSQL backend.
"""

from django.db.backends.sqlite3 import operations as sqlite_operations


class DatabaseOperations(sqlite_operations.DatabaseOperations):
    """
    libSQL-specific database operations.

    Overrides SQLite operations that don't work well with libSQL,
    especially in multi-threaded/no-GIL scenarios.
    """

    def last_executed_query(self, cursor, sql, params):
        """
        Return the last executed query as a string.

        The SQLite backend tries to execute a separate query to format
        parameters, which fails with libSQL when connections are lost
        in no-GIL scenarios. We'll just return the query with placeholders.
        """
        # For libSQL, we don't try to execute additional queries for formatting
        # This avoids "stream not found" errors in multi-threaded scenarios
        if params:
            return f"{sql} -- params: {params}"
        return sql
