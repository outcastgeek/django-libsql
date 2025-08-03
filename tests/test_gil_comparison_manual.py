#!/usr/bin/env python
"""
Quick Django ORM GIL vs no-GIL comparison test for django-libsql.
"""

import subprocess
import sys
import os


def run_quick_test(gil_enabled=True):
    """Run quick Django ORM test."""
    env = os.environ.copy()

    if gil_enabled:
        env.pop("PYTHON_GIL", None)
        cmd = [sys.executable, "tests/test_quick_threading.py"]
        mode = "GIL ENABLED"
    else:
        env["PYTHON_GIL"] = "0"
        # Try to use -Xgil=0 flag if available (Python 3.13+)
        cmd = [sys.executable, "-Xgil=0", "tests/test_quick_threading.py"]
        mode = "GIL DISABLED"

    print(f"\n🚀 Running {mode} Django ORM Test")
    print("-" * 40)

    try:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=60
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        # If -Xgil=0 failed, try without it
        if (
            not gil_enabled
            and result.returncode != 0
            and "unknown option" in result.stderr
        ):
            print("Note: -Xgil=0 not supported, trying with PYTHON_GIL=0 only...")
            cmd = [sys.executable, "tests/test_quick_threading.py"]
            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=60
            )
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)

        return result.returncode == 0, result.stdout
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False, ""


def parse_quick_result(output):
    """Parse the RESULT line from output."""
    for line in output.split("\n"):
        if line.startswith("RESULT:"):
            try:
                # Parse "RESULT: 4×3: 12.5 CRUD ops/sec (100% worker efficiency)"
                parts = line.split(":")[1].strip()
                ops_per_sec = float(parts.split()[1])
                return ops_per_sec
            except:
                pass
    return None


def main():
    """Run quick comparison."""
    print("🐍 DJANGO-LIBSQL GIL vs NO-GIL COMPARISON")
    print("=" * 60)

    # Check if Turso is configured
    if os.environ.get("TURSO_DATABASE_URL"):
        print(f"Using Turso database: {os.environ['TURSO_DATABASE_URL'][:40]}...")
    else:
        print("Using local database (set TURSO_DATABASE_URL for Turso testing)")

    # Test both modes
    gil_success, gil_output = run_quick_test(gil_enabled=True)
    nogil_success, nogil_output = run_quick_test(gil_enabled=False)

    # Parse results
    gil_ops = parse_quick_result(gil_output) if gil_success else None
    nogil_ops = parse_quick_result(nogil_output) if nogil_success else None

    # Comparison
    print(f"\n\n📊 COMPARISON RESULTS:")
    print("=" * 40)
    if gil_ops and nogil_ops:
        improvement = (nogil_ops - gil_ops) / gil_ops * 100
        print(f"GIL Enabled:  {gil_ops:.1f} CRUD ops/sec")
        print(f"GIL Disabled: {nogil_ops:.1f} CRUD ops/sec")
        print(f"Improvement:  {improvement:+.1f}%")

        if improvement > 20:
            print("\n✅ Significant NO-GIL advantage!")
        elif improvement > 5:
            print("\n🟨 Moderate NO-GIL advantage")
        elif improvement > -5:
            print("\n🟨 Similar performance")
        else:
            print("\n❌ GIL performs better")
    else:
        print(f"GIL Test: {'✅ Passed' if gil_success else '❌ Failed'}")
        print(f"NO-GIL Test: {'✅ Passed' if nogil_success else '❌ Failed'}")

        if not gil_success and gil_ops is None:
            print("\nGIL test failed to produce results")
        if not nogil_success and nogil_ops is None:
            print("NO-GIL test failed to produce results")
            print("\nNote: NO-GIL requires Python 3.13+ free-threading build")


if __name__ == "__main__":
    main()
