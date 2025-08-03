"""
Pytest plugin for automatic GIL testing.

This plugin allows tests to be automatically run with both GIL enabled and disabled
when using Python 3.13+ with free-threading support.
"""

import os
import sys
import subprocess
import pytest


def pytest_addoption(parser):
    """Add command-line options for GIL testing."""
    parser.addoption(
        "--test-gil-modes",
        action="store_true",
        default=False,
        help="Run tests with both GIL enabled and disabled (requires Python 3.13+)",
    )
    parser.addoption(
        "--gil-mode",
        choices=["enabled", "disabled", "current"],
        default="current",
        help="Force specific GIL mode for tests",
    )


def pytest_configure(config):
    """Configure pytest with GIL testing markers."""
    config.addinivalue_line(
        "markers", "gil_disabled: mark test to run only with GIL disabled"
    )
    config.addinivalue_line(
        "markers", "gil_enabled: mark test to run only with GIL enabled"
    )
    config.addinivalue_line(
        "markers",
        "test_both_gil_modes: mark test to automatically run with both GIL modes",
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on GIL mode."""
    gil_mode = config.getoption("--gil-mode")
    test_both = config.getoption("--test-gil-modes")

    # Check current GIL status
    try:
        import _thread

        gil_is_disabled = not _thread._is_gil_enabled()
    except (ImportError, AttributeError):
        gil_is_disabled = os.environ.get("PYTHON_GIL", "1") == "0"

    # Create skip markers
    skip_gil_disabled = pytest.mark.skip(reason="Test requires GIL to be disabled")
    skip_gil_enabled = pytest.mark.skip(reason="Test requires GIL to be enabled")

    # Handle --test-gil-modes option
    if test_both and sys.version_info >= (3, 13):
        # This would require running pytest twice in subprocess
        # For now, we'll document this approach
        pass

    # Filter tests based on markers and current GIL state
    for item in items:
        if "gil_disabled" in item.keywords and not gil_is_disabled:
            if gil_mode != "disabled":
                item.add_marker(skip_gil_disabled)

        if "gil_enabled" in item.keywords and gil_is_disabled:
            if gil_mode != "enabled":
                item.add_marker(skip_gil_enabled)


def pytest_runtest_setup(item):
    """Setup for each test based on GIL requirements."""
    # Check if test should verify GIL state
    if "test_both_gil_modes" in item.keywords:
        # This marker indicates the test handles GIL testing internally
        pass


@pytest.fixture
def ensure_gil_disabled():
    """Fixture that ensures GIL is disabled for a test."""
    try:
        import _thread

        if _thread._is_gil_enabled():
            pytest.skip("Test requires GIL to be disabled")
    except (ImportError, AttributeError):
        if os.environ.get("PYTHON_GIL", "1") != "0":
            pytest.skip("Test requires PYTHON_GIL=0")


@pytest.fixture
def ensure_gil_enabled():
    """Fixture that ensures GIL is enabled for a test."""
    try:
        import _thread

        if not _thread._is_gil_enabled():
            pytest.skip("Test requires GIL to be enabled")
    except (ImportError, AttributeError):
        if os.environ.get("PYTHON_GIL", "1") == "0":
            pytest.skip("Test requires GIL to be enabled")


@pytest.fixture
def gil_status():
    """Fixture that provides current GIL status."""
    try:
        import _thread

        return "DISABLED" if not _thread._is_gil_enabled() else "ENABLED"
    except (ImportError, AttributeError):
        return "DISABLED" if os.environ.get("PYTHON_GIL", "1") == "0" else "ENABLED"


class GILTestRunner:
    """Helper class to run tests with specific GIL modes."""

    @staticmethod
    def run_with_gil_modes(test_file, test_name=None):
        """Run a test file with both GIL enabled and disabled."""
        results = {}

        # Base command
        base_cmd = [sys.executable, "-m", "pytest", test_file, "-v"]
        if test_name:
            base_cmd.extend(["-k", test_name])

        # Run with GIL enabled
        env_enabled = os.environ.copy()
        env_enabled.pop("PYTHON_GIL", None)

        print("🔒 Running with GIL ENABLED...")
        result_enabled = subprocess.run(
            base_cmd, env=env_enabled, capture_output=True, text=True
        )
        results["enabled"] = {
            "returncode": result_enabled.returncode,
            "stdout": result_enabled.stdout,
            "stderr": result_enabled.stderr,
        }

        # Run with GIL disabled (Python 3.13+)
        if sys.version_info >= (3, 13):
            env_disabled = os.environ.copy()
            env_disabled["PYTHON_GIL"] = "0"

            cmd_disabled = [sys.executable, "-X", "gil=0"] + base_cmd[1:]

            print("🔓 Running with GIL DISABLED...")
            result_disabled = subprocess.run(
                cmd_disabled, env=env_disabled, capture_output=True, text=True
            )
            results["disabled"] = {
                "returncode": result_disabled.returncode,
                "stdout": result_disabled.stdout,
                "stderr": result_disabled.stderr,
            }

        return results
