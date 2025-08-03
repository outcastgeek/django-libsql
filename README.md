# Django LibSQL Backend

A Django database backend for [LibSQL](https://libsql.org/) and [Turso](https://turso.tech/).

## Features

- Full Django ORM compatibility
- Support for LibSQL local and remote databases
- Turso edge database integration
- Threading support with performance optimizations
- Embedded replica support for low-latency reads with background sync
- No-GIL Python support for improved performance
- Comprehensive test suite with automatic execution in all modes

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

   **For local SQLite databases:**
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django_libsql.libsql',
           'NAME': '/path/to/your/database.db',
       }
   }
   ```

   **For Turso remote databases:**
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django_libsql.libsql',
           'NAME': os.environ.get('TURSO_DATABASE_URL'),  # libsql://your-database.turso.io
           'AUTH_TOKEN': os.environ.get('TURSO_AUTH_TOKEN'),
           'SYNC_INTERVAL': 0.1,  # Optional: auto-sync interval in seconds
       }
   }
   ```

   **For embedded replicas (local file + remote sync):**
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django_libsql.libsql',
           'NAME': '/path/to/local/replica.db',  # Local file path
           'SYNC_URL': os.environ.get('TURSO_DATABASE_URL'),  # Remote database URL
           'AUTH_TOKEN': os.environ.get('TURSO_AUTH_TOKEN'),
           'SYNC_INTERVAL': 1.0,  # Sync every second
           'ENCRYPTION_KEY': os.environ.get('ENCRYPTION_KEY'),  # Optional
       }
   }
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

## Embedded Replicas

Embedded replicas provide local SQLite performance with automatic background synchronization to your remote Turso database.

### How It Works

1. **Local SQLite file** for fast reads and writes
2. **Background sync** to remote Turso database
3. **Automatic sync** based on `SYNC_INTERVAL`
4. **Manual sync** available via `connection.sync()`

### Manual Sync

```python
from django.db import connection

# Manually sync the embedded replica
connection.sync()
```

**Note:** Manual sync is only available for embedded replica connections (not remote-only connections).

## Development & Testing

This project uses `uv` package manager and includes a comprehensive Makefile for all operations.

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd django-libsql

# Set up environment variables
export TURSO_DATABASE_URL="libsql://your-database.turso.io"
export TURSO_AUTH_TOKEN="your-turso-auth-token"

# Install dependencies
make install

# Run ALL tests in ALL modes (NO MANUAL INTERVENTION!)
make test-all

# Run specific test suites
make test-basic      # Basic functionality tests
make test-embedded   # Embedded replica tests
make test-examples   # Run all Django example apps
```

### Test Scenarios

The test suite automatically runs in ALL required modes:
1. **Regular Python (single-threaded)**
2. **Python with Threads**
3. **Python with Threads + No-GIL**
4. **Python with Threads + No-GIL + Django ORM**

## Examples

This project includes comprehensive example applications demonstrating django-libsql capabilities.

### Quick Start with Examples

```bash
# Setup all example apps (migrations + sample data)
make setup-examples

# Run individual examples
make run-basic-app      # Todo app on port 8000
make run-blog-app       # Blog app on port 8001
make run-data-processor # Data processor on port 8002
make run-analytics      # Analytics dashboard on port 8003
make run-sensors        # Embedded replica sensors
make run-benchmark      # GIL benchmark
```

### Example Applications

- **Basic App**: Todo list demonstrating CRUD operations
- **Blog App**: Complex queries, relationships, and search
- **Data Processor**: Concurrent processing with threading
- **Real-time Analytics**: Dashboard with Turso sync
- **Embedded Replica App**: Sensor simulation with local replica + remote sync
- **GIL Benchmark**: Performance testing for Python 3.13+ no-GIL

See [`examples/README.md`](examples/README.md) for detailed documentation.

### Workspace Architecture

The project uses **UV's workspace feature** for clean separation:

```
django-libsql/
├── pyproject.toml          # Main library (distributed)
├── src/django_libsql/      # Core library code
└── examples/               # Examples workspace (not distributed)
    ├── pyproject.toml      # Examples package with UV scripts
    └── [example apps...]   # Individual Django applications
```

**Benefits:**
- ✅ Developers get full examples with `uv sync`
- ✅ End users get clean library installs without example bloat
- ✅ Examples always test against the latest library code
- ✅ CI/CD can test examples automatically

## Documentation

For detailed documentation, visit: https://django-libsql.readthedocs.io

## Testing

### Important Note on Threading Tests

libSQL connections have different thread-safety characteristics than SQLite. While the backend works correctly for Django's normal usage patterns, some threading tests that attempt to share connections across threads may fail with Rust panics. This is a known limitation of the underlying libSQL library.

### Setup with direnv (Recommended)

The project includes a `.envrc` file for easy environment configuration:

```bash
# Install direnv (if not already installed)
brew install direnv  # macOS
# or: apt-get install direnv  # Ubuntu/Debian

# Allow direnv for this project
direnv allow

# The following environment variables will be automatically loaded:
# - TURSO_DATABASE_URL
# - TURSO_AUTH_TOKEN  
# - TURSO_SYNC_INTERVAL
```

### Manual Setup

If not using direnv, set the environment variables manually:

```bash
export TURSO_DATABASE_URL="libsql://your-database.turso.io"
export TURSO_AUTH_TOKEN="your-turso-auth-token"
export TURSO_SYNC_INTERVAL="0.1"
```

### Installing Dependencies

The project has optional dependency groups defined in `pyproject.toml`:

```bash
# Install the package in editable mode with development dependencies
uv pip install -e ".[dev]"

# Or using pip
pip install -e ".[dev]"

# Install only testing dependencies
uv pip install -e ".[testing]"

# Install just the base package
uv pip install -e .
```

The `dev` group includes:
- pytest (testing framework)
- pytest-django (Django integration)
- pytest-cov (coverage reporting)
- black (code formatter)
- ruff (linter)
- mypy (type checker)

The `testing` group includes
- pytest
- pytest-django
- pytest-cov
- pytest-xdist (parallel test execution)

### Troubleshooting Installation

If you encounter `error: Failed to spawn: pytest`, ensure you've installed the development dependencies:

```bash
# With uv (make sure to sync first)
uv sync
uv pip install -e ".[dev]"

# Then run tests with
uv run pytest

# Or install globally and run directly
pip install -e ".[dev]"
pytest
```

If you see `ImportError: No module named 'tests'`, this is because pytest-django needs to find your Django project. The project includes a `pytest.ini` file that configures the necessary paths.

### Running Tests

The test suite runs automatically without any manual setup. Migrations are created and applied automatically when tests start.

#### Using pytest (Recommended)

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_backend.py

# Run specific test class
pytest tests/test_backend.py::LibSQLBackendTest

# Run specific test method
pytest tests/test_backend.py::LibSQLBackendTest::test_basic_crud_operations

# Run with coverage
pytest --cov=django_libsql --cov-report=html

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run only threading tests
pytest tests/test_threading.py -v

# Run with specific markers (if defined)
pytest -m "not slow"
```

#### Using Django's Test Runner

```bash
# Run all tests using Django's test command
python -m django test --settings=tests.settings

# Run specific test module
python -m django test tests.test_backend --settings=tests.settings

# Run with verbosity
python -m django test --settings=tests.settings --verbosity=2

# Keep test database between runs (faster for multiple test runs)
python -m django test --settings=tests.settings --keepdb

# Run tests in parallel (Django 3.0+)
python -m django test --settings=tests.settings --parallel

# Run specific test case
python -m django test tests.test_backend.LibSQLBackendTest --settings=tests.settings
```

#### Performance and Threading Tests

##### Automatic GIL Testing

**How pytest ensures proper GIL testing:**

1. **Automatic Detection**: Tests use `is_gil_disabled()` to detect current GIL status
2. **Adaptive Assertions**: Tests adjust expectations based on GIL state
3. **Test Runner**: `test_runner_gil.py` runs entire test suite with both GIL modes
4. **Pytest Markers**: Tests can be marked to run only with specific GIL states
5. **CI Integration**: GitHub Actions automatically tests both GIL modes

```bash
# Run all tests with automatic GIL detection
pytest

# Run tests with both GIL modes automatically (Python 3.13+)
python tests/test_runner_gil.py

# Run specific test file with both modes
python tests/test_runner_gil.py tests/test_threading.py

# Force specific GIL mode
PYTHON_GIL=0 python -X gil=0 -m pytest  # GIL disabled
python -m pytest  # GIL enabled (default)

# Run only GIL comparison tests
pytest tests/test_gil_comparison.py -v
```

**Test Markers for GIL Control:**
```python
@pytest.mark.gil_disabled  # Test runs only with GIL disabled
@pytest.mark.gil_enabled   # Test runs only with GIL enabled
@pytest.mark.test_both_gil_modes  # Test handles both modes internally
```

##### Key Threading Test Files:
- **`tests/test_threading.py`** - Threading tests that detect and adapt to GIL status
  - Tests concurrent CRUD operations
  - Measures performance improvements with no-GIL
  - Validates connection isolation
- **`tests/test_gil_comparison.py`** - Automated GIL performance comparison
  - Runs tests with both GIL modes
  - Compares single vs multi-threaded performance
  - Validates no-GIL benefits
- **`tests/test_quick_threading.py`** - Quick threading benchmark

##### Manual Performance Testing:
```bash
# Run quick threading performance test
python tests/test_quick_threading.py

# Compare GIL vs no-GIL performance (manual script)
python tests/test_gil_comparison_manual.py

# Run with GIL disabled manually
PYTHON_GIL=0 python -X gil=0 tests/test_quick_threading.py
```

#### Test Database Management

```bash
# Create test database schema
python -m django migrate --settings=tests.settings

# Run tests keeping the test database
python -m django test --settings=tests.settings --keepdb

# Explicitly destroy test database
python -m django test --settings=tests.settings --no-keepdb
```

#### Troubleshooting Tests

```bash
# Run with maximum verbosity
pytest -vvv

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Run last failed tests
pytest --lf

# Run tests and stop on first failure
pytest -x

# Show slowest tests
pytest --durations=10
```

### Test Status

As of the latest version:
- **Backend Tests**: All 12 tests pass (1 skipped for savepoints)
- **Threading Tests**: All 9 tests pass with proper connection isolation
- **Transaction Tests**: All pass
- **Connection Tests**: All pass
- **GIL Comparison Tests**: All pass, showing 2.4x speedup with no-GIL

#### No-GIL Performance Results:
- **GIL Enabled**: ~1.2x speedup with 4 threads
- **GIL Disabled**: ~2.4x speedup with 4 threads
- Tests automatically detect GIL status and adjust expectations

All tests run automatically without manual intervention, using the actual Turso database.

## Contributing

Contributions are welcome! Please read our contributing guidelines and submit pull requests.

## License

MIT License - see LICENSE file for details.