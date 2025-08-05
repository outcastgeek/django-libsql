# Django-libSQL Examples

This directory contains **full Django applications** demonstrating the capabilities of the django-libsql backend with Turso. All examples are proper Django apps with manage.py, URLs, views, templates, and management commands that run in ALL modes automatically.

**NO ONE-OFF SCRIPTS! ALL EXAMPLES ARE FULL DJANGO APPS!**

## Example Applications

### 1. Basic App (`basic_app/`)
A simple todo list application demonstrating:
- Basic CRUD operations
- Model relationships (Category, Todo, TodoAttachment)
- Django admin integration
- Sample data generation

### 2. Blog App (`blog_app/`)
A feature-rich blog application showcasing:
- Complex queries with multiple relationships
- Prefetch optimization and select_related
- Aggregation queries (Count, Avg, Sum)
- Full-text search simulation
- Hierarchical categories
- Comment threading
- View tracking and analytics

### 3. Data Processor (`data_processor/`)
Concurrent data processing demonstration:
- **Thread-safe database operations**
- Connection isolation with `connections.close_all()`
- Concurrent processing with ThreadPoolExecutor
- Real-time progress tracking
- Performance metrics collection
- Batch operations

### 4. GIL Benchmark (`gil_benchmark/`)
Performance testing for Python 3.13+ no-GIL mode:
- Sequential vs concurrent operation comparison
- Various workload types (reads, writes, mixed)
- Transaction-heavy operations
- Batch insert performance
- Complex query benchmarks
- Automatic GIL detection

### 5. Real-time Analytics (`realtime_analytics/`)
Real-time data analytics dashboard:
- Background event processing
- Concurrent aggregation updates
- Session tracking
- Real-time metrics calculation
- Turso sync interval optimization

### 6. Embedded Replica Sensors (`embedded_replica_app/`)
IoT sensor simulation demonstrating embedded replicas:
- **Full Django app with web dashboard**
- Management command: `simulate_sensors` - runs in all modes
- Management command: `test_all_modes` - automatic testing
- Real-time sensor data visualization
- Manual and automatic sync demonstration
- Performance comparison across modes
- Web UI at `/` with live updates

### 7. GIL Benchmark App (`gil_benchmark/`)
Comprehensive performance benchmarking Django app:
- **Full Django app with results dashboard**
- Management command: `run_benchmark` - customizable tests
- Management command: `benchmark_all_modes` - automatic all-mode testing
- Web UI showing benchmark results and comparisons
- Admin interface for historical results
- API endpoints for running benchmarks
- Tests CRUD, read, write, and mixed operations

## Project Structure

This project uses **UV's workspace feature** to manage the examples as a separate package that depends on the main library but is not distributed with it.

### Workspace Configuration

The project is structured as a UV workspace:

```
django-libsql/
├── pyproject.toml          # Main library configuration
├── src/django_libsql/      # Core library code (distributed)
└── examples/               # Examples workspace member (not distributed)
    ├── pyproject.toml      # Examples package configuration
    ├── basic_app/          # Todo list example
    ├── blog_app/           # Blog with complex queries
    ├── data_processor/     # Concurrent processing
    ├── gil_benchmark/      # Performance testing
    └── realtime_analytics/ # Real-time dashboard
```

**Key Configuration in `pyproject.toml`:**
- `[tool.uv.workspace] members = ["examples"]` - Defines the workspace
- `[tool.hatch.build.targets.wheel] exclude = ["examples/"]` - Excludes examples from distribution
- `examples = ["lorem>=0.1.1"]` in optional dependencies - Only needed for example apps

**Examples Package (`examples/pyproject.toml`):**
- `[tool.uv.sources] django-libsql = { workspace = true }` - References main library
- `[project.scripts]` - Defines all UV commands for running examples

This means:
- ✅ **Developers** get full examples with `uv sync` and `uv run` commands
- ✅ **End users** get clean library installs without example bloat
- ✅ **Examples** can depend on and test the latest library code
- ✅ **CI/CD** can test examples against the main library automatically

## Running the Examples

### Quick Start - Run ALL Apps in ALL Modes Automatically

```bash
# First, sync the workspace to install all dependencies
uv sync

# Run ALL Django apps in ALL modes (NO MANUAL INTERVENTION!)
make test-examples

# This runs all apps in ALL REQUIRED MODES automatically:
# - Remote + GIL
# - Remote + No-GIL
# - Embedded Replica + GIL
# - Embedded Replica + No-GIL
```

### Running Individual Django Apps

```bash
# Using Makefile commands
make run-basic-app      # Todo app on port 8000
make run-blog-app       # Blog app on port 8001
make run-data-processor # Data processor on port 8002
make run-analytics      # Analytics on port 8003
make run-sensors        # Embedded replica sensors
make run-benchmark      # Performance benchmark

# Or manually with Django manage.py
cd examples/embedded_replica_app
uv run python manage.py migrate
uv run python manage.py simulate_sensors --duration 30
uv run python manage.py test_all_modes  # Tests ALL modes automatically!

cd examples/gil_benchmark
uv run python manage.py migrate
uv run python manage.py run_benchmark --test crud
uv run python manage.py benchmark_all_modes  # Tests ALL modes automatically!
```

### Testing Specific Modes

```bash
# Test with No-GIL
make test-django-app-nogil APP=embedded_replica_app CMD='simulate_sensors --threads 8'

# Test with Embedded Replica
make test-django-app-embedded APP=gil_benchmark CMD='run_benchmark --test mixed'

# Manual No-GIL execution
PYTHON_GIL=0 uv run python -X gil=0 examples/gil_benchmark/manage.py run_benchmark

# Manual Embedded Replica execution (defaults to embedded replica mode)
uv run python examples/embedded_replica_app/manage.py simulate_sensors

# To use remote-only mode instead
USE_EMBEDDED_REPLICA=false uv run python examples/embedded_replica_app/manage.py simulate_sensors
```

### Manual Execution

```bash
# Navigate to the example app
cd examples/basic_app

# Run any Django command
python manage.py migrate
python manage.py runserver
python manage.py create_sample_data
```

## Environment Variables

All examples support the following environment variables:

- `TURSO_DATABASE_URL`: Your Turso database URL (required)
- `TURSO_AUTH_TOKEN`: Your Turso auth token (required)
- `TURSO_SYNC_INTERVAL`: Sync interval in seconds (default: 0.1)
- `PYTHON_GIL`: Set to "0" to disable GIL (Python 3.13+ only)

Example:
```bash
export TURSO_DATABASE_URL="libsql://your-database.turso.io"
export TURSO_AUTH_TOKEN="your-auth-token"
export TURSO_SYNC_INTERVAL="0.1"

./run_examples.sh blog_app runserver
```

### Manual Setup

#### Basic Todo App
```bash
cd basic_app
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# Visit http://localhost:8000
```

#### Blog App
```bash
cd blog_app
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# Visit http://localhost:8000
# Admin at http://localhost:8000/admin
```

#### Data Processor
```bash
cd data_processor
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# Create some data sources in admin
# Visit http://localhost:8000 to create and monitor processing jobs
```

#### GIL Benchmark
```bash
cd gil_benchmark

# Run with GIL enabled (default)
python benchmark.py

# Run without GIL (Python 3.13+ required)
PYTHON_GIL=0 python -X gil=0 benchmark.py

# Compare the results to see performance improvements
```

#### Real-time Analytics
```bash
cd realtime_analytics
python manage.py migrate
python manage.py createsuperuser

# Create a website in admin first
python manage.py runserver

# Visit http://localhost:8000 for the dashboard
# Use the tracking endpoints to send data
```

## Threading and No-GIL Demonstrations

### Key Threading Patterns

1. **Connection Isolation**
   ```python
   def worker_function():
       # Ensure each thread has its own connection
       from django.db import connections
       connections.close_all()
       
       # Perform database operations
       Model.objects.create(...)
   ```

2. **Thread Pool Usage**
   ```python
   with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
       futures = [executor.submit(task, arg) for arg in args]
       results = [f.result() for f in futures]
   ```

3. **No-GIL Detection**
   ```python
   def is_gil_disabled():
       try:
           import _thread
           return not _thread._is_gil_enabled()
       except (ImportError, AttributeError):
           return os.environ.get("PYTHON_GIL", "1") == "0"
   ```

### Performance Benefits with No-GIL

When running with Python 3.13+ and no-GIL:
- Multi-threaded operations see 2-4x speedup
- CPU-bound operations scale linearly with threads
- Database operations benefit from true parallelism
- Reduced contention in high-concurrency scenarios

### Testing with No-GIL

1. **Check Python version:**
   ```bash
   python --version  # Should be 3.13+
   ```

2. **Run with no-GIL:**
   ```bash
   PYTHON_GIL=0 python -X gil=0 manage.py runserver
   ```

3. **Verify GIL status in code:**
   ```python
   import sys
   print(f"GIL disabled: {sys._is_gil_enabled() == False}")
   ```

## Turso Configuration

All examples can use either local SQLite or remote Turso databases:

### Local Database (Default)
```python
DATABASES = {
    "default": {
        "ENGINE": "django_libsql.libsql",
        "NAME": "file:local.db",
    }
}
```

### Remote Turso Database
```python
DATABASES = {
    "default": {
        "ENGINE": "django_libsql.libsql",
        "NAME": os.environ.get("TURSO_DATABASE_URL"),
        "AUTH_TOKEN": os.environ.get("TURSO_AUTH_TOKEN"),
        "SYNC_INTERVAL": 0.1,  # Fast sync for real-time apps
    }
}
```

## Common Patterns

### Batch Operations
```python
# Efficient bulk inserts
records = [Model(field=value) for value in values]
Model.objects.bulk_create(records, batch_size=100)
```

### Transaction Management
```python
from django.db import transaction

with transaction.atomic():
    # All operations succeed or fail together
    parent = Parent.objects.create(...)
    Child.objects.bulk_create([...])
```

### Query Optimization
```python
# Reduce database queries
queryset = Model.objects.select_related('foreign_key').prefetch_related('many_to_many')
```

## Troubleshooting

### Connection Issues
If you see "stream not found" errors:
- Ensure `connections.close_all()` is called in threads
- Check that django-libsql is properly installed
- Verify Turso credentials are correct

### Performance Issues
- Use connection pooling for high-concurrency apps
- Batch operations when possible
- Monitor sync_interval for real-time requirements

### No-GIL Issues
- Requires Python 3.13+ with free-threading support
- Some C extensions may not be compatible
- Test thoroughly before production use

## Available UV Commands

Here's a complete list of UV commands for the examples:

### Todo App
- `uv run todo-migrate` - Run migrations
- `uv run todo-sample` - Create sample data
- `uv run todo-server` - Start server on port 8000
- `uv run todo-admin` - Create superuser

### Blog App  
- `uv run blog-migrate` - Run migrations
- `uv run blog-sample` - Create sample blog data
- `uv run blog-server` - Start server on port 8001
- `uv run blog-admin` - Create superuser

### Data Processor
- `uv run processor-migrate` - Run migrations
- `uv run processor-sample` - Create data sources
- `uv run processor-server` - Start server on port 8002
- `uv run processor-admin` - Create superuser

### Real-time Analytics
- `uv run analytics-migrate` - Run migrations
- `uv run analytics-sample` - Create websites
- `uv run analytics-server` - Start server on port 8003
- `uv run analytics-admin` - Create superuser

### Benchmarks
- `uv run benchmark` - Run benchmark with GIL
- `uv run benchmark-no-gil` - Run without GIL

### Batch Commands
- `uv run migrate-all` - Migrate all databases
- `uv run sample-all` - Create all sample data
- `uv run setup-all` - Complete setup for all apps

## Additional Resources

- [Django-libSQL Documentation](https://github.com/your-repo/django-libsql)
- [Turso Documentation](https://docs.turso.tech)
- [Python No-GIL Information](https://docs.python.org/3.13/whatsnew/3.13.html)
- [Django ORM Documentation](https://docs.djangoproject.com/en/5.2/topics/db/)