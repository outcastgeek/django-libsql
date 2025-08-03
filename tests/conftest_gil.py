"""
Additional pytest configuration for GIL testing.
This can be included in the main conftest.py if needed.
"""
import os
import sys
import pytest


def pytest_configure(config):
    """Add custom markers for GIL testing."""
    config.addinivalue_line(
        "markers",
        "gil_required: mark test as requiring specific GIL state"
    )
    config.addinivalue_line(
        "markers", 
        "no_gil_only: mark test to run only when GIL is disabled"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically skip tests based on GIL status."""
    try:
        import _thread
        gil_disabled = not _thread._is_gil_enabled()
    except (ImportError, AttributeError):
        gil_disabled = os.environ.get('PYTHON_GIL', '1') == '0'
    
    skip_no_gil = pytest.mark.skip(reason="Test requires GIL to be disabled")
    
    for item in items:
        if "no_gil_only" in item.keywords and not gil_disabled:
            item.add_marker(skip_no_gil)


@pytest.fixture(scope="session")
def gil_status():
    """Fixture that provides current GIL status."""
    try:
        import _thread
        return "DISABLED" if not _thread._is_gil_enabled() else "ENABLED"
    except (ImportError, AttributeError):
        return "DISABLED" if os.environ.get('PYTHON_GIL', '1') == '0' else "ENABLED"


@pytest.fixture
def with_gil_disabled():
    """Fixture that temporarily sets PYTHON_GIL=0 for a test."""
    old_value = os.environ.get('PYTHON_GIL')
    os.environ['PYTHON_GIL'] = '0'
    yield
    if old_value is None:
        os.environ.pop('PYTHON_GIL', None)
    else:
        os.environ['PYTHON_GIL'] = old_value