"""
Data processor settings with Embedded Replica support.

This configuration enables high-performance local processing with background sync.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Add parent paths to Python path
import sys
sys.path.insert(0, str(BASE_DIR.parent.parent))

SECRET_KEY = "django-insecure-data-processor-embedded-replica-key"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "processor",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Database - Embedded Replica Configuration
# This gives us the best of both worlds:
# - Ultra-fast local reads/writes
# - Automatic background sync to Turso
# - Perfect for high-throughput data processing

DATABASES = {
    "default": {
        "ENGINE": "django_libsql.libsql",
        # Local SQLite file for embedded replica
        "NAME": str(BASE_DIR / "data" / "processor_replica.db"),
        # Remote Turso database to sync with
        "SYNC_URL": os.environ.get("TURSO_DATABASE_URL"),
        "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN"),
        # Sync interval in seconds (adjust based on your needs)
        # Shorter = more consistent, Longer = better performance
        "SYNC_INTERVAL": float(os.environ.get("SYNC_INTERVAL", "2.0")),
        # Optional: Encrypt the local replica
        "ENCRYPTION_KEY": os.environ.get("ENCRYPTION_KEY"),
    }
}

# Alternative: Remote-only configuration (uncomment to compare)
# DATABASES = {
#     "default": {
#         "ENGINE": "django_libsql.libsql",
#         "NAME": os.environ.get("TURSO_DATABASE_URL"),
#         "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN"),
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Data processor settings optimized for embedded replicas
DATA_PROCESSOR_SETTINGS = {
    # More workers possible due to local database performance
    "MAX_WORKERS": int(os.environ.get("MAX_WORKERS", "8")),
    # Larger batches work well with local writes
    "BATCH_SIZE": int(os.environ.get("BATCH_SIZE", "500")),
    # Enable no-GIL for maximum performance
    "ENABLE_NO_GIL": os.environ.get("PYTHON_GIL", "1") == "0",
    # Sync strategy
    "SYNC_AFTER_BATCH": True,  # Sync after each batch completes
    "SYNC_THRESHOLD": 10000,   # Force sync after N records
}

# Logging to track sync operations
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'processor': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django_libsql': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}