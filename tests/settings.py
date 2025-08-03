import os

DEBUG = True
SECRET_KEY = "test-secret-key"

# ALWAYS use Turso for tests
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
