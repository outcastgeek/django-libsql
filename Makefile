# Makefile for django-libsql using UV
# NO MANUAL INTERVENTION REQUIRED - Everything runs automatically!

.PHONY: test test-all test-basic test-embedded test-examples clean install sync

# Install/sync dependencies with uv
install:
	@echo "📦 Installing dependencies with uv..."
	@uv sync

sync:
	@echo "🔄 Syncing dependencies with uv..."
	@uv sync

# Setup all example apps (migrations + sample data) - NO PYTHON SCRIPT NEEDED!
setup-examples: sync
	@echo "🚀 Setting up all example Django apps..."
	@cd examples/basic_app && uv run python manage.py migrate --noinput && \
		(uv run python manage.py create_sample_data 2>/dev/null || true)
	@cd examples/blog_app && uv run python manage.py migrate --noinput && \
		(uv run python manage.py create_blog_data 2>/dev/null || true)
	@cd examples/data_processor && uv run python manage.py migrate --noinput && \
		(uv run python manage.py create_processor_data 2>/dev/null || true)
	@cd examples/realtime_analytics && uv run python manage.py migrate --noinput && \
		(uv run python manage.py create_analytics_data 2>/dev/null || true)
	@cd examples/embedded_replica_app && uv run python manage.py migrate --noinput
	@cd examples/gil_benchmark && uv run python manage.py migrate --noinput
	@echo "✅ All Django apps setup complete!"

# Run ALL tests in ALL modes automatically - NO MANUAL INTERVENTION!
test-all: sync
	@echo "🚀 Running ALL tests in ALL modes..."
	@echo "\n====== SCENARIO 1: Regular Python (Single-threaded) ======"
	@uv run pytest tests/test_backend.py -v
	@uv run pytest tests/test_embedded_replica.py::TestEmbeddedReplicaAllModes::test_all_scenarios_single_process -v
	@echo "\n====== SCENARIO 2: Python with Threads ======"
	@uv run pytest tests/test_threading.py -v
	@uv run pytest tests/test_embedded_replica.py::TestEmbeddedReplicaAllModes::test_all_scenarios_with_threads -v
	@echo "\n====== SCENARIO 3: Python with Threads + No-GIL ======"
	@PYTHON_GIL=0 uv run python -X gil=0 -m pytest tests/test_threading.py -v || echo "No-GIL not available"
	@PYTHON_GIL=0 uv run python -X gil=0 -m pytest tests/test_embedded_replica.py::TestEmbeddedReplicaAllModes::test_all_scenarios_with_threads -v || echo "No-GIL not available"
	@echo "\n====== SCENARIO 4: Python with Threads + No-GIL + Django ORM ======"
	@uv run pytest tests/test_gil_comparison.py -v
	@PYTHON_GIL=0 uv run python -X gil=0 -m pytest tests/test_gil_comparison.py -v || echo "No-GIL not available"
	@echo "\n✅ ALL SCENARIOS TESTED AUTOMATICALLY!"

# Run basic tests only (pytest auto-discovers!)
test-basic: sync
	@echo "Running basic tests..."
	@uv run pytest tests/test_backend.py tests/test_threading.py -v

# Run embedded replica tests (REQUIRES LOCAL FILE SETUP!)
test-embedded: sync
	@echo "Running embedded replica tests..."
	@echo "NOTE: These tests require embedded replica setup (local file + sync URL)"
	@USE_EMBEDDED_REPLICA=true uv run pytest tests/test_embedded_replica.py -v

# Run all Django example apps in ALL REQUIRED MODES - NO MANUAL INTERVENTION!
test-examples: sync setup-examples
	@echo "🚀 Running all Django example apps in ALL REQUIRED MODES..."
	@echo "\n====== MODE 1: Remote + GIL ======"
	@cd examples/embedded_replica_app && uv run python manage.py test_all_modes
	@cd examples/gil_benchmark && uv run python manage.py benchmark_all_modes
	@echo "\n====== MODE 2: Remote + No-GIL ======"
	@cd examples/embedded_replica_app && PYTHON_GIL=0 uv run python -X gil=0 manage.py test_all_modes || echo "No-GIL not available"
	@cd examples/gil_benchmark && PYTHON_GIL=0 uv run python -X gil=0 manage.py benchmark_all_modes || echo "No-GIL not available"
	@echo "\n====== MODE 3: Embedded Replica + GIL ======"
	@cd examples/embedded_replica_app && USE_EMBEDDED_REPLICA=1 uv run python manage.py test_all_modes
	@cd examples/gil_benchmark && USE_EMBEDDED_REPLICA=1 uv run python manage.py benchmark_all_modes
	@echo "\n====== MODE 4: Embedded Replica + No-GIL ======"
	@cd examples/embedded_replica_app && USE_EMBEDDED_REPLICA=1 PYTHON_GIL=0 uv run python -X gil=0 manage.py test_all_modes || echo "No-GIL not available"
	@cd examples/gil_benchmark && USE_EMBEDDED_REPLICA=1 PYTHON_GIL=0 uv run python -X gil=0 manage.py benchmark_all_modes || echo "No-GIL not available"
	@echo "\n✅ ALL DJANGO APPS TESTED IN ALL MODES!"

# Quick test (pytest with specific tests)
test: sync
	@echo "Running quick tests..."
	@uv run pytest tests/test_backend.py::LibSQLBackendTest::test_backend_vendor tests/test_backend.py::LibSQLBackendTest::test_basic_crud -v

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .pytest_cache
	@rm -rf test_report.json
	@rm -rf examples/embedded_replica_app/local_replica.db
	@rm -rf examples/data_processor/data/processor_replica.db
	@rm -rf .venv

# Install for development with uv
install-dev:
	@echo "📦 Installing for development with uv..."
	@uv sync --all-extras

# Run specific scenario tests
test-scenario-single: sync
	@echo "Testing single-threaded scenario..."
	@uv run pytest tests/test_embedded_replica_comprehensive.py -k "single_threaded" -v

test-scenario-threads: sync
	@echo "Testing multi-threaded scenario..."
	@uv run pytest tests/test_embedded_replica_comprehensive.py -k "multi_threaded" -v

test-scenario-nogil: sync
	@echo "Testing no-GIL scenario..."
	@PYTHON_GIL=0 uv run python -X gil=0 -m pytest tests/test_embedded_replica_comprehensive.py -k "multi_threaded" -v

# Performance comparison
benchmark: sync
	@echo "🚀 Running performance benchmarks..."
	@echo "1. Remote-only with GIL:"
	@uv run python examples/gil_benchmark/benchmark_embedded.py
	@echo "\n2. Embedded replica with GIL:"
	@USE_EMBEDDED_REPLICA=1 uv run python examples/gil_benchmark/benchmark_embedded.py
	@echo "\n3. Remote-only without GIL:"
	@PYTHON_GIL=0 uv run python -X gil=0 examples/gil_benchmark/benchmark_embedded.py 2>/dev/null || echo "No-GIL not available"
	@echo "\n4. Embedded replica without GIL:"
	@USE_EMBEDDED_REPLICA=1 PYTHON_GIL=0 uv run python -X gil=0 examples/gil_benchmark/benchmark_embedded.py 2>/dev/null || echo "No-GIL not available"

# Run tests with coverage
test-coverage: sync
	@echo "📊 Running tests with coverage..."
	@uv run pytest --cov=django_libsql --cov-report=html --cov-report=term

# Format code
format: sync
	@echo "🎨 Formatting code..."
	@uv run black src/ tests/ examples/
	@uv run ruff check --fix src/ tests/ examples/

# Lint code
lint: sync
	@echo "🔍 Linting code..."
	@uv run black --check src/ tests/ examples/
	@uv run ruff check src/ tests/ examples/
	@uv run mypy src/

# Run a single test file
test-file: sync
	@echo "Running single test file..."
	@uv run pytest $(FILE) -v

# Run individual Django example apps
run-basic-app: sync
	@echo "🏃 Running Basic Todo App..."
	@cd examples/basic_app && uv run python run_app.py

run-blog-app: sync
	@echo "🏃 Running Blog App..."
	@cd examples/blog_app && uv run python run_app.py

run-data-processor: sync
	@echo "🏃 Running Data Processor..."
	@cd examples/data_processor && uv run python run_app.py

run-analytics: sync
	@echo "🏃 Running Real-time Analytics..."
	@cd examples/realtime_analytics && uv run python run_app.py

run-sensors: sync
	@echo "🏃 Running Embedded Replica Sensors..."
	@cd examples/embedded_replica_app && uv run python run_app.py

run-benchmark: sync
	@echo "🏃 Running GIL Benchmark..."
	@cd examples/gil_benchmark && uv run python run_app.py

# Test Django apps in specific modes
test-django-app-nogil: sync
	@echo "🚀 Testing Django app with No-GIL..."
	@cd examples/$(APP) && PYTHON_GIL=0 uv run python -X gil=0 manage.py $(CMD)

test-django-app-embedded: sync
	@echo "🚀 Testing Django app with Embedded Replica..."
	@cd examples/$(APP) && USE_EMBEDDED_REPLICA=1 uv run python manage.py $(CMD)

# Help
help:
	@echo "django-libsql commands (using uv):"
	@echo ""
	@echo "SETUP COMMANDS:"
	@echo "  make install       - Install dependencies with uv"
	@echo "  make setup-examples - Setup all Django apps (migrations + sample data)"
	@echo ""
	@echo "TEST COMMANDS:"
	@echo "  make test-all      - Run ALL tests in ALL modes (comprehensive)"
	@echo "  make test          - Run quick basic tests"
	@echo "  make test-basic    - Run basic functionality tests"
	@echo "  make test-embedded - Run embedded replica tests"
	@echo "  make test-examples - Run all Django apps in all modes"
	@echo "  make benchmark     - Run performance benchmarks"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo ""
	@echo "DJANGO APP COMMANDS:"
	@echo "  make run-basic-app      - Run Todo app (port 8000)"
	@echo "  make run-blog-app       - Run Blog app (port 8001)"
	@echo "  make run-data-processor - Run Data Processor (port 8002)"
	@echo "  make run-analytics      - Run Analytics Dashboard (port 8003)"
	@echo "  make run-sensors        - Run Sensor Simulation"
	@echo "  make run-benchmark      - Run Performance Benchmark"
	@echo ""
	@echo "DEVELOPMENT COMMANDS:"
	@echo "  make format        - Format code with black and ruff"
	@echo "  make lint          - Lint code"
	@echo "  make clean         - Clean up temporary files"
	@echo ""
	@echo "ADVANCED USAGE:"
	@echo "  make test-file FILE=tests/test_backend.py"
	@echo "  make test-django-app-nogil APP=embedded_replica_app CMD='simulate_sensors --threads 8'"
	@echo "  make test-django-app-embedded APP=gil_benchmark CMD='run_benchmark --test crud'"
	@echo ""
	@echo "All tests run automatically with NO MANUAL INTERVENTION!"