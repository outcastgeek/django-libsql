"""
Real-time analytics Django settings demonstrating Turso sync with django-libsql.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Add parent paths to Python path
import sys

sys.path.insert(0, str(BASE_DIR.parent.parent))

SECRET_KEY = "django-insecure-realtime-analytics-example"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "analytics",
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

# Database - Using django-libsql with Turso for real-time sync
DATABASES = {
    "default": {
        "ENGINE": "django_libsql.libsql",
        "NAME": os.environ.get("TURSO_DATABASE_URL"),
        "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN"),
        # Fast sync interval for real-time analytics
        "SYNC_INTERVAL": float(os.environ.get("TURSO_SYNC_INTERVAL", "0.05")),
    }
}

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

# Analytics settings
ANALYTICS_SETTINGS = {
    "RETENTION_DAYS": 30,  # Keep analytics data for 30 days
    "AGGREGATION_INTERVAL": 60,  # Aggregate data every 60 seconds
    "ENABLE_REAL_TIME": True,
    "MAX_EVENTS_PER_BATCH": 100,
}
