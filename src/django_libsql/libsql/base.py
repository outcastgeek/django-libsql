from __future__ import annotations

import re
import time
import threading
from django.db.backends.sqlite3 import base as sqlite_base
from .creation import DatabaseCreation
from .schema import DatabaseSchemaEditor
from .features import DatabaseFeatures
from .operations import DatabaseOperations

# Regex to find %s placeholders
FORMAT_QMARK_REGEX = re.compile(r"(?<!%)%s")

# No-GIL connection handling
CONNECTION_RETRY_COUNT = 3
CONNECTION_RETRY_DELAY = 0.1


class LibSQLCursorWrapper:
    """
    A wrapper for libSQL cursors to make them compatible with Django's expectations.
    """

    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        from django.db import IntegrityError, OperationalError

        try:
            if params is None:
                return self.cursor.execute(query)

            # Convert Django's %s placeholders to ? for SQLite/libSQL
            if isinstance(params, (list, tuple)):
                # Convert from "format" style (%s) to "qmark" style (?)
                query = FORMAT_QMARK_REGEX.sub("?", query).replace("%%", "%")
                return self.cursor.execute(query, params)
            elif isinstance(params, dict):
                # Convert from "pyformat" style (%(name)s) to "named" style (:name)
                query = query % {name: f":{name}" for name in params}
                return self.cursor.execute(query, params)
            else:
                return self.cursor.execute(query, params)
        except ValueError as e:
            error_str = str(e)
            # Convert libSQL constraint errors to Django IntegrityError
            if "SQLITE_CONSTRAINT" in error_str:
                raise IntegrityError(error_str)
            # Handle connection stream errors (common with no-GIL and high concurrency)
            elif "stream not found" in error_str or "Hrana:" in error_str:
                raise OperationalError(f"Database connection lost: {error_str}")
            raise

    def executemany(self, query, param_list):
        # Convert query format for executemany as well
        if param_list:
            # Check if first item is dict (named params) or list/tuple (positional)
            first_param = next(iter(param_list), None)
            if first_param:
                if isinstance(first_param, dict):
                    # Named parameters
                    query = query % {name: f":{name}" for name in first_param}
                else:
                    # Positional parameters
                    query = FORMAT_QMARK_REGEX.sub("?", query).replace("%%", "%")
        return self.cursor.executemany(query, param_list)

    def fetchone(self):
        from django.db import IntegrityError

        try:
            return self.cursor.fetchone()
        except ValueError as e:
            # Convert libSQL constraint errors to Django IntegrityError
            if "SQLITE_CONSTRAINT" in str(e):
                raise IntegrityError(str(e))
            raise

    def fetchmany(self, size=None):
        if size is None:
            return self.cursor.fetchmany()
        return self.cursor.fetchmany(size)

    def fetchall(self):
        return self.cursor.fetchall()

    def close(self):
        return self.cursor.close()

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def description(self):
        return self.cursor.description

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __iter__(self):
        return iter(self.fetchall())


class DatabaseWrapper(sqlite_base.DatabaseWrapper):
    """
    A minimal Django backend that reuses Django's SQLite backend
    but connects via the official libSQL Python driver.

    Supports Embedded Replicas via:
      NAME = path to local replica file (e.g. BASE_DIR / "local.db")
      SYNC_URL = Turso/libSQL URL (e.g. libsql://<db>.turso.io)
      AUTH_TOKEN = JWT for the database
      SYNC_INTERVAL = optional auto-sync seconds
      ENCRYPTION_KEY = optional key for encrypted local replica
    """

    vendor = "libsql"
    display_name = "libSQL (Turso)"
    creation_class = DatabaseCreation
    SchemaEditorClass = DatabaseSchemaEditor
    features_class = DatabaseFeatures
    ops_class = DatabaseOperations

    def get_new_connection(self, conn_params):
        import os
        import libsql

        # For embedded replicas, NAME is your local file (e.g. local.db).
        # For local-only, set NAME to a file and omit SYNC_URL/AUTH_TOKEN.
        # For remote-only, you can set NAME to the remote URL and omit SYNC_URL.
        name = conn_params.get("NAME") or ":memory:"

        # CRITICAL FIX: During tests, Django passes ":memory:" but we want to use TEST['NAME']
        # if it's configured to point to a Turso database
        if name == ":memory:":
            test_name = self.settings_dict.get("TEST", {}).get("NAME")
            if test_name and (
                test_name.startswith("libsql://")
                or test_name.startswith("wss://")
                or test_name.startswith("https://")
            ):
                name = test_name
                print(
                    f"🔧 Overriding test :memory: with configured TEST['NAME']: {name}"
                )

        # Check if this is an in-memory database (NOT including Turso URLs)
        is_memory_db = (
            name == ":memory:"
            or name.startswith("file:memory")
            or name.startswith("file::memory:")
            or "mode=memory" in str(name)
        )

        # Pull libSQL/Turso options either from settings or env vars.
        sync_url = self.settings_dict.get("SYNC_URL") or os.getenv("TURSO_DATABASE_URL")
        auth_token = self.settings_dict.get("AUTH_TOKEN") or os.getenv(
            "TURSO_AUTH_TOKEN"
        )
        sync_interval = self.settings_dict.get("SYNC_INTERVAL")
        encryption_key = self.settings_dict.get("ENCRYPTION_KEY")

        kwargs = {}

        # For in-memory databases (but NOT Turso URLs)
        if is_memory_db:
            # Create a pure in-memory database without sync
            conn = libsql.connect(":memory:")
        # If NAME looks like a remote DSN (libsql://, wss://, https://), call connect(name, ...).
        # Otherwise, treat NAME as the local replica path and pass sync_* options.
        elif isinstance(name, str) and name.startswith(
            ("libsql://", "wss://", "ws://", "https://", "http://")
        ):
            if auth_token:
                kwargs["auth_token"] = auth_token
            # IMPORTANT: For remote Turso connections, we should also support sync_interval
            # This helps ensure changes are visible across connections in threading scenarios
            if sync_interval is not None:
                kwargs["sync_interval"] = float(sync_interval)
            conn = libsql.connect(str(name), **kwargs)
        else:
            # This is the embedded replica case - local file with sync_url
            if sync_url:
                kwargs["sync_url"] = sync_url
            if auth_token:
                kwargs["auth_token"] = auth_token
            if sync_interval is not None:
                kwargs["sync_interval"] = float(sync_interval)
            if encryption_key:
                kwargs["encryption_key"] = encryption_key
            
            conn = libsql.connect(str(name), **kwargs)

        # Force autocommit mode for libSQL
        conn.autocommit = True

        return conn

    def _set_autocommit(self, autocommit):
        """Override to handle libSQL's connection object differences"""
        # libSQL uses autocommit attribute directly
        if self.connection is not None:
            self.connection.autocommit = autocommit
            if autocommit:
                # Ensure any pending transaction is committed
                try:
                    self.connection.commit()
                except Exception:
                    pass

    def create_cursor(self, name=None):
        """Override to handle libSQL's cursor creation"""
        # Note: For embedded replicas with SYNC_INTERVAL, libSQL handles
        # automatic syncing internally. We don't need to manually sync here.
        cursor = self.connection.cursor()

        # Use our custom wrapper for libSQL cursors
        return LibSQLCursorWrapper(cursor)

    def disable_constraint_checking(self):
        """
        Disable foreign key constraint checking.
        libSQL/Turso handles this differently than SQLite.
        """
        with self.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF")
        self.needs_rollback = False
        return True

    def enable_constraint_checking(self):
        """
        Enable foreign key constraint checking.
        """
        with self.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = ON")

    def _start_transaction_under_autocommit(self):
        """
        Override transaction handling for libSQL.
        libSQL handles transactions differently than standard SQLite.
        """
        # Start a transaction explicitly
        with self.cursor() as cursor:
            cursor.execute("BEGIN")

    def is_in_memory_db(self):
        """
        Check if this is an in-memory database.
        With libSQL embedded replicas, we have a local file that syncs.
        """
        return self.settings_dict["NAME"] == ":memory:"

    def _commit(self):
        """Override commit to ensure it works with libSQL."""
        if self.connection is not None:
            with self.wrap_database_errors:
                try:
                    return self.connection.commit()
                except ValueError as e:
                    if "stream not found" in str(e):
                        # Connection lost, can't commit
                        self.close()
                        raise
                    else:
                        raise

    def ensure_connection(self):
        """Ensure connection is established."""
        if self.connection is None:
            with self.wrap_database_errors:
                self.connect()

    def sync(self):
        """
        Manually sync the embedded replica with the remote database.
        This is only available for embedded replica connections.
        
        Returns:
            bool: True if sync succeeded, False otherwise
        
        Raises:
            OperationalError: If sync is not available (e.g., for pure remote connections)
        """
        from django.db import OperationalError
        
        self.ensure_connection()
        
        if self.connection is None:
            raise OperationalError("No database connection available")
            
        if not hasattr(self.connection, "sync"):
            raise OperationalError(
                "Manual sync is only available for embedded replica connections. "
                "Ensure you have configured both NAME (local file) and SYNC_URL."
            )
        
        try:
            self.connection.sync()
            return True
        except Exception as e:
            error_msg = str(e)
            if "not supported in databases opened in Remote mode" in error_msg:
                raise OperationalError(
                    "Manual sync is only available for embedded replica connections. "
                    "Ensure you have configured both NAME (local file) and SYNC_URL."
                )
            elif "not supported in databases opened in Memory mode" in error_msg:
                raise OperationalError(
                    "Manual sync is not available for in-memory databases. "
                    "Ensure NAME points to a file path, not ':memory:'."
                )
            raise OperationalError(f"Failed to sync database: {error_msg}")
