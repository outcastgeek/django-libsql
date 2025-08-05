"""
Settings for Embedded Replica Demo App.

This app demonstrates libSQL embedded replicas with Django.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-embedded-replica-demo-key-not-for-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sensors',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'embedded_replica_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Database configuration
# Control whether to use embedded replica mode via environment variable
USE_EMBEDDED_REPLICA = os.environ.get('USE_EMBEDDED_REPLICA', 'True').lower() in ('true', '1', 'yes')

if USE_EMBEDDED_REPLICA:
    # Embedded replica mode - local file with remote sync
    DATABASES = {
        'default': {
            'ENGINE': 'django_libsql.libsql',
            # Local database file
            'NAME': str(BASE_DIR / 'local_replica.db'),
            # Remote Turso database to sync with
            'SYNC_URL': os.environ.get('TURSO_DATABASE_URL'),
            'AUTH_TOKEN': os.environ.get('TURSO_AUTH_TOKEN'),
            # Sync every 1 second in background for demo
            'SYNC_INTERVAL': float(os.environ.get('TURSO_SYNC_INTERVAL', '1.0')),
            # Optional encryption for local replica
            'ENCRYPTION_KEY': os.environ.get('ENCRYPTION_KEY'),
        }
    }
else:
    # Remote-only mode - direct Turso connection
    DATABASES = {
        'default': {
            'ENGINE': 'django_libsql.libsql',
            'NAME': os.environ.get('TURSO_DATABASE_URL'),
            'AUTH_TOKEN': os.environ.get('TURSO_AUTH_TOKEN'),
            'SYNC_INTERVAL': float(os.environ.get('TURSO_SYNC_INTERVAL', '0.1')),
        }
    }

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}