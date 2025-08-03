#!/usr/bin/env python
"""
Test runner that automatically runs tests with both GIL modes.

Usage:
    python tests/test_runner_gil.py  # Run all tests with both GIL modes
    python tests/test_runner_gil.py tests/test_threading.py  # Run specific test file
    python tests/test_runner_gil.py -k test_concurrent  # Run tests matching pattern
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests_with_gil_mode(gil_enabled, pytest_args):
    """Run tests with specific GIL mode."""
    env = os.environ.copy()

    # Set up the command
    if gil_enabled:
        env.pop("PYTHON_GIL", None)
        cmd = [sys.executable, "-m", "pytest"] + pytest_args
        mode = "GIL ENABLED"
    else:
        env["PYTHON_GIL"] = "0"
        if sys.version_info >= (3, 13):
            cmd = [sys.executable, "-X", "gil=0", "-m", "pytest"] + pytest_args
        else:
            cmd = [sys.executable, "-m", "pytest"] + pytest_args
        mode = "GIL DISABLED"

    print(f"\n{'=' * 60}")
    print(f"🔧 Running tests with {mode}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(cmd, env=env)
    return result.returncode


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run tests with both GIL modes")
    parser.add_argument("pytest_args", nargs="*", help="Arguments to pass to pytest")
    parser.add_argument(
        "--gil-only", choices=["enabled", "disabled"], help="Run with only one GIL mode"
    )
    args = parser.parse_args()

    # Default pytest arguments if none provided
    if not args.pytest_args:
        args.pytest_args = ["tests/", "-v"]

    results = {}

    if args.gil_only == "enabled":
        # Run only with GIL enabled
        return run_tests_with_gil_mode(True, args.pytest_args)
    elif args.gil_only == "disabled":
        # Run only with GIL disabled
        return run_tests_with_gil_mode(False, args.pytest_args)
    else:
        # Run with both modes
        print("🐍 DJANGO-LIBSQL TEST RUNNER - TESTING BOTH GIL MODES")
        print("=" * 60)

        # Check Python version
        if sys.version_info < (3, 13):
            print("⚠️  Warning: GIL control requires Python 3.13+")
            print("   Running with current GIL state only.\n")
            return run_tests_with_gil_mode(True, args.pytest_args)

        # Run with GIL enabled
        results["enabled"] = run_tests_with_gil_mode(True, args.pytest_args)

        # Run with GIL disabled
        results["disabled"] = run_tests_with_gil_mode(False, args.pytest_args)

        # Summary
        print(f"\n{'=' * 60}")
        print("📊 TEST SUMMARY")
        print(f"{'=' * 60}")
        print(
            f"GIL Enabled:  {'✅ PASSED' if results['enabled'] == 0 else '❌ FAILED'}"
        )
        print(
            f"GIL Disabled: {'✅ PASSED' if results['disabled'] == 0 else '❌ FAILED'}"
        )

        # Return non-zero if any test failed
        return max(results.values())


if __name__ == "__main__":
    sys.exit(main())
