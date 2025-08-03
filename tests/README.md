# Django libSQL Test Suite

Comprehensive tests for the Django libSQL backend, including threading and performance tests.

## Test Structure

### Core Tests
- `test_backend.py` - Core backend functionality tests
- `test_threading.py` - Threading and concurrency tests
- `test_quick_threading.py` - Quick performance test script
- `run_gil_comparison.py` - GIL vs no-GIL comparison script

### Models
The test suite uses the following models in `testapp/models.py`:
- `TestModel` - Basic model for simple tests
- `RelatedModel` - For foreign key relationship tests
- `Book` - Complex model with various field types
- `Review` - Model with unique_together constraint

## Running Tests

### Using pytest (Recommended)

```bash
# Run all tests
pytest

# Run specific test file
pytest test_backend.py

# Run specific test class or method
pytest test_backend.py::LibSQLBackendTest
pytest test_backend.py::LibSQLBackendTest::test_basic_crud_operations

# Run with coverage
pytest --cov=django_libsql --cov-report=html

# Run in parallel
pytest -n auto

# Run with verbose output
pytest -v

# Show print statements during tests
pytest -s
```

### Using Django Test Runner

From the tests directory:
```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test test_backend

# Run with keepdb for faster subsequent runs
python manage.py test --keepdb

# Run in parallel
python manage.py test --parallel

# Run specific test case
python manage.py test test_backend.LibSQLBackendTest
```

Or from the project root:
```bash
# Run all tests
python -m django test --settings=tests.settings

# Run specific tests
python -m django test tests.test_backend --settings=tests.settings
```

### Threading and Performance Tests

```bash
# Run all threading tests
pytest test_threading.py -v

# Run quick threading test
python test_quick_threading.py

# Compare GIL vs no-GIL performance
python run_gil_comparison.py

# Run with GIL disabled (Python 3.13+)
PYTHON_GIL=0 python -Xgil=0 test_quick_threading.py
```

### Test Database Management

```bash
# Create/update test database schema
python manage.py migrate

# Show migrations
python manage.py showmigrations

# Create migrations for test models
python manage.py makemigrations testapp
```

### Environment Variables
For Turso testing, set these environment variables:
```bash
export TURSO_DATABASE_URL="libsql://your-db.turso.io"
export TURSO_AUTH_TOKEN="your-auth-token"
export TURSO_SYNC_INTERVAL="0.1"  # Optional, in seconds
```

## Performance Results

### Threading Performance (from dj_on_libsql testing)
| Configuration | Performance | Improvement |
|--------------|-------------|-------------|
| Django ORM with GIL | 0.9 CRUD ops/sec | baseline |
| Django ORM without GIL | 2.1 CRUD ops/sec | +133% |
| Raw SQL with GIL | 3.1 ops/sec | baseline |
| Raw SQL without GIL | 16.7 ops/sec | +443% |

### Running No-GIL Tests
Requires Python 3.13+ free-threading build:
```bash
# Run with GIL disabled
PYTHON_GIL=0 python -Xgil=0 tests/test_quick_threading.py
```

## Test Categories

### 1. Backend Tests (`test_backend.py`)
- Basic CRUD operations
- Foreign key relationships
- Complex model operations
- Index and ordering verification
- Unique constraints
- Transaction handling
- Connection settings
- Parameter substitution

### 2. Threading Tests (`test_threading.py`)
- Concurrent model creation
- Concurrent CRUD operations
- Foreign key operations under concurrency
- Connection isolation per thread
- Sync interval effectiveness
- Performance comparisons

### 3. Quick Performance Tests
- `test_quick_threading.py` - Standalone script for quick benchmarks
- `run_gil_comparison.py` - Automated GIL comparison

## Key Features Tested

1. **libSQL/Turso Compatibility**
   - Remote database connections
   - Authentication token handling
   - Sync interval configuration

2. **Django ORM Integration**
   - All field types (CharField, IntegerField, DecimalField, etc.)
   - Auto-generated fields (created_at, updated_at)
   - Model Meta options (ordering, indexes, unique_together)
   - Foreign key relationships and cascades

3. **Thread Safety**
   - Isolated connections per thread
   - No connection sharing
   - Concurrent operations without conflicts

4. **Performance**
   - Significant improvements with no-GIL Python
   - Efficient handling of concurrent operations
   - Proper sync behavior for consistency

## Notes

- All tests clean up after themselves
- Tests work with both local and Turso databases
- Performance results may vary based on network latency
- The backend is fully thread-safe and optimized for concurrent access