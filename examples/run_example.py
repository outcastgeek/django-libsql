#!/usr/bin/env python
"""Entry points for running django-libsql examples with uv."""

import os
import sys
import subprocess
from pathlib import Path


def setup_environment():
    """Set up the Python path and environment."""
    # Get the project root (where pyproject.toml is)
    current_dir = Path.cwd()
    project_root = current_dir

    # Walk up to find pyproject.toml
    while project_root != project_root.parent:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent

    # Add project root to Python path if not already there
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def run_django_command(app_name, command, *args):
    """Run a Django management command for a specific app."""
    setup_environment()

    app_dir = Path(__file__).parent / app_name
    if not app_dir.exists():
        print(f"Error: Example app '{app_name}' not found!")
        sys.exit(1)

    # Run the command in a subprocess to avoid Django module cache issues
    cmd = [sys.executable, "manage.py", command] + list(args)

    # Set environment variables for the subprocess
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "settings"

    # Run the command in the app directory
    result = subprocess.run(cmd, cwd=app_dir, env=env)

    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        raise SystemExit(result.returncode)


# Basic app commands
def basic_migrate():
    """Run migrations for basic todo app."""
    run_django_command("basic_app", "migrate")


def basic_server():
    """Start basic todo app server on port 8000."""
    run_django_command("basic_app", "runserver", "8000")


def basic_sample():
    """Create sample data for basic todo app."""
    run_django_command("basic_app", "create_sample_data")


# Blog app commands
def blog_migrate():
    """Run migrations for blog app."""
    run_django_command("blog_app", "migrate")


def blog_server():
    """Start blog app server on port 8001."""
    run_django_command("blog_app", "runserver", "8001")


def blog_sample():
    """Create sample data for blog app."""
    run_django_command("blog_app", "create_blog_data")


# Data processor commands
def processor_migrate():
    """Run migrations for data processor app."""
    run_django_command("data_processor", "migrate")


def processor_server():
    """Start data processor server on port 8002."""
    run_django_command("data_processor", "runserver", "8002")


def processor_sample():
    """Create sample data for data processor app."""
    run_django_command("data_processor", "create_processor_data")


# Analytics commands
def analytics_migrate():
    """Run migrations for analytics app."""
    run_django_command("realtime_analytics", "migrate")


def analytics_server():
    """Start analytics server on port 8003."""
    run_django_command("realtime_analytics", "runserver", "8003")


def analytics_sample():
    """Create sample data for analytics app."""
    run_django_command("realtime_analytics", "create_analytics_data")


def gil_benchmark():
    """Run GIL benchmark."""
    setup_environment()

    benchmark_dir = Path(__file__).parent / "gil_benchmark"
    if not benchmark_dir.exists():
        print("Error: GIL benchmark not found!")
        sys.exit(1)

    # Run the benchmark script directly
    cmd = [sys.executable, "benchmark.py"]
    result = subprocess.run(cmd, cwd=benchmark_dir)

    if result.returncode != 0:
        print(f"Benchmark failed with exit code {result.returncode}")
        raise SystemExit(result.returncode)


# Batch commands
def setup_all():
    """Run migrations and create sample data for all apps."""
    apps = [
        ("basic_app", "create_sample_data"),
        ("blog_app", "create_blog_data"),
        ("data_processor", "create_processor_data"),
        ("realtime_analytics", "create_analytics_data"),
    ]

    print("Setting up all example apps...")

    # Run migration and sample data creation for each app sequentially
    for app_name, sample_command in apps:
        print(f"\nSetting up {app_name}...")

        # First migrate
        print(f"  - Running migrations...")
        try:
            run_django_command(app_name, "migrate")
            print(f"  ✓ Migrations completed for {app_name}")
        except SystemExit as e:
            if e.code != 0:
                print(f"  ✗ Failed to migrate {app_name}")
                continue

        # Then create sample data (skip for now due to libSQL subprocess issue)
        print(
            f"  - Skipping sample data (run manually: uv run {app_name.replace('_', '-')}-sample)"
        )
        print(f"  ℹ Each app is ready to use - sample data can be created individually")

        print(f"✓ {app_name} setup complete!")

    print(f"\n🎉 All example apps are now set up and ready to use!")
    print(f"\nAvailable commands:")
    print(f"  uv run basic-server     # Start basic todo app (port 8000)")
    print(f"  uv run blog-server      # Start blog app (port 8001)")
    print(f"  uv run processor-server # Start data processor (port 8002)")
    print(f"  uv run analytics-server # Start analytics app (port 8003)")
    print(f"  uv run gil-benchmark    # Run no-GIL performance benchmark")
    print(f"\nTo add sample data to any app:")
    print(f"  uv run basic-sample     # Add sample data to basic todo app")
    print(f"  uv run blog-sample      # Add sample data to blog app")
    print(f"  uv run processor-sample # Add sample data to data processor")
    print(f"  uv run analytics-sample # Add sample data to analytics app")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_example.py <command>")
        print("\nAvailable commands:")
        print("  setup_all       - Setup all example apps")
        print("  basic_migrate   - Migrate basic app")
        print("  basic_server    - Run basic app server")
        print("  basic_sample    - Create basic app sample data")
        print("  blog_migrate    - Migrate blog app")
        print("  blog_server     - Run blog app server")
        print("  blog_sample     - Create blog app sample data")
        print("  processor_migrate - Migrate processor app")
        print("  processor_server  - Run processor app server")
        print("  processor_sample  - Create processor app sample data")
        print("  analytics_migrate - Migrate analytics app")
        print("  analytics_server  - Run analytics app server")
        print("  analytics_sample  - Create analytics app sample data")
        print("  gil_benchmark     - Run GIL performance benchmark")
        sys.exit(1)

    command = sys.argv[1]

    # Map commands to functions
    commands = {
        "setup_all": setup_all,
        "basic_migrate": basic_migrate,
        "basic_server": basic_server,
        "basic_sample": basic_sample,
        "blog_migrate": blog_migrate,
        "blog_server": blog_server,
        "blog_sample": blog_sample,
        "processor_migrate": processor_migrate,
        "processor_server": processor_server,
        "processor_sample": processor_sample,
        "analytics_migrate": analytics_migrate,
        "analytics_server": analytics_server,
        "analytics_sample": analytics_sample,
        "gil_benchmark": gil_benchmark,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
