import os
from pathlib import Path

DEBUG = True
SECRET_KEY = "test-secret-key"

# Base directory for test database files
BASE_DIR = Path(__file__).resolve().parent

# Control whether to use embedded replica mode via environment variable
USE_EMBEDDED_REPLICA = os.environ.get('USE_EMBEDDED_REPLICA', 'False').lower() in ('true', '1', 'yes')

if USE_EMBEDDED_REPLICA:
    # Embedded replica mode - local file with remote sync
    DATABASES = {
        "default": {
            "ENGINE": "django_libsql.libsql",
            "NAME": str(BASE_DIR / "test_replica.db"),  # Local file
            "SYNC_URL": os.environ.get("TURSO_DATABASE_URL"),
            "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN"),
            "SYNC_INTERVAL": float(os.environ.get("TURSO_SYNC_INTERVAL", "0.1")),
            "OPTIONS": {
                "init_command": ("PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;"),
            },
            "TEST": {
                "NAME": str(BASE_DIR / "test_replica.db"),
                "MIGRATE": True,
            },
        }
    }
else:
    # Remote-only mode - direct Turso connection
    DATABASES = {
        "default": {
            "ENGINE": "django_libsql.libsql",
            "NAME": os.environ.get("TURSO_DATABASE_URL"),
            "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN"),
            "SYNC_INTERVAL": float(os.environ.get("TURSO_SYNC_INTERVAL", "0.1")),
            "OPTIONS": {
                "init_command": ("PRAGMA foreign_keys=ON; PRAGMA busy_timeout=5000;"),
            },
            "TEST": {
                "NAME": os.environ.get("TURSO_DATABASE_URL"),
                "MIGRATE": True,
            },
        }
    }

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "tests.testapp",
    "tests",  # For management commands
]

USE_TZ = True
