import os

DEBUG = True
SECRET_KEY = "test-secret-key"

DATABASES = {
    "default": {
        "ENGINE": "django_libsql.libsql",
        "NAME": os.environ.get("TURSO_DATABASE_URL", ":memory:"),
        "OPTIONS": {
            "auth_token": os.environ.get("TURSO_AUTH_TOKEN"),
        },
        "TEST": {
            "NAME": os.environ.get("TURSO_DATABASE_URL", ":memory:"),
        },
    }
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "tests.testapp",
]

USE_TZ = True