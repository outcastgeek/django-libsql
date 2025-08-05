"""Settings for GIL benchmark."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "benchmark-secret-key-not-for-production"
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
    'benchmark_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'gil_benchmark.urls'

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

# Database configuration
# Control whether to use embedded replica mode via environment variable
USE_EMBEDDED_REPLICA = os.environ.get('USE_EMBEDDED_REPLICA', 'False').lower() in ('true', '1', 'yes')

if USE_EMBEDDED_REPLICA:
    # Embedded replica mode - local file with remote sync
    DATABASES = {
        'default': {
            'ENGINE': 'django_libsql.libsql',
            'NAME': str(BASE_DIR / 'benchmark_replica.db'),
            'SYNC_URL': os.environ.get('TURSO_DATABASE_URL'),
            'AUTH_TOKEN': os.environ.get('TURSO_AUTH_TOKEN'),
            'SYNC_INTERVAL': float(os.environ.get('TURSO_SYNC_INTERVAL', '0.5')),  # Sync every 0.5 seconds
        }
    }
else:
    # Remote-only mode (default for benchmarks)
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

# Static files
STATIC_URL = '/static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
