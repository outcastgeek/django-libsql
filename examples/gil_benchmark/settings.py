"""Settings for GIL benchmark."""

import os

# Database
DATABASES = {
    "default": {
        "ENGINE": "django_libsql.libsql",
        "NAME": os.environ.get("TURSO_DATABASE_URL", "file:benchmark.db"),
        "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN", ""),
        "SYNC_INTERVAL": float(os.environ.get("TURSO_SYNC_INTERVAL", "0.1")),
    }
}

SECRET_KEY = "benchmark-secret-key"
INSTALLED_APPS = ["gil_benchmark"]
USE_TZ = True
