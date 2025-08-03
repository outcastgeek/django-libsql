# Django libSQL Backend

A Django database backend for [libSQL](https://libsql.org/) and [Turso](https://turso.tech/).

## Features

- Full Django ORM compatibility
- Support for libSQL local and remote databases
- Turso edge database integration
- Threading support with performance optimizations
- Embedded replica support for low-latency reads

## Installation

```bash
pip install django-libsql
```

## Quick Start

1. Install the package:
   ```bash
   pip install django-libsql
   ```

2. Configure your Django settings:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django_libsql.libsql',
           'NAME': 'your-database-path-or-url',
           'OPTIONS': {
               'auth_token': 'your-auth-token-if-using-turso',
           },
       }
   }
   ```

3. For Turso databases:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django_libsql.libsql',
           'NAME': 'libsql://your-database.turso.io',
           'OPTIONS': {
               'auth_token': 'your-turso-auth-token',
           },
       }
   }
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

## Documentation

For detailed documentation, visit: https://django-libsql.readthedocs.io

## Testing

```bash
# Install development dependencies
pip install -e .[dev]

# Run tests
pytest

# Run with coverage
pytest --cov=django_libsql
```

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

MIT License - see LICENSE file for details.