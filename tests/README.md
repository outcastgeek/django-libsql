# Django libSQL Test Suite

Comprehensive tests for the Django libSQL backend, including threading, embedded replicas, and performance tests.

## Test Structure

### Core Tests
- `test_backend.py` - Core backend functionality tests
- `test_threading.py` - Threading and concurrency tests
- `test_embedded_replica.py` - Embedded replica functionality tests
- `test_gil_comparison.py` - GIL vs no-GIL performance comparison

### Models
The test suite uses the following models in `testapp/models.py`:
- `TestModel` - Basic model for simple tests
- `RelatedModel` - For foreign key relationship tests
- `Book` - Complex model with various field types
- `Review` - Model with unique_together constraint

## Running Tests

### Using Makefile (Recommended - NO MANUAL INTERVENTION!)

```bash
# Run ALL tests in ALL modes automatically
make test-all

# Run specific test suites
make test-basic      # Basic functionality tests
make test-embedded   # Embedded replica tests (requires setup)
make test-examples   # Test all Django example apps

# Quick test
make test           # Run quick basic tests
```

### Test Scenarios Covered

The `make test-all` command automatically runs tests in ALL modes:
1. **Regular Python (single-threaded)**
2. **Python with Threads**
3. **Python with Threads + No-GIL**
4. **Python with Threads + No-GIL + Django ORM**

### Using pytest Directly

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

# Run embedded replica tests
pytest test_embedded_replica.py -v

# Run GIL comparison tests
pytest test_gil_comparison.py -v

# Run with GIL disabled (Python 3.13+)
PYTHON_GIL=0 python -Xgil=0 -m pytest test_threading.py -v
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

### 3. Embedded Replica Tests (`test_embedded_replica.py`)
- Single-threaded writes with sync
- Multi-threaded concurrent operations
- Batch processing with sync intervals
- Complex queries on embedded replicas
- Sync performance metrics

### 4. GIL Comparison Tests (`test_gil_comparison.py`)
- Sequential vs concurrent performance
- GIL vs no-GIL benchmarks
- Django ORM threading performance

## Key Features Tested

1. **libSQL/Turso Compatibility**
   - Remote database connections
   - Authentication token handling
   - Sync interval configuration
   - Embedded replica support (local file + remote sync)

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