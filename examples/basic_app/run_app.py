#!/usr/bin/env python
"""Run the app with cleanup before and after."""

import os
import sys
import signal
import atexit
from django.core.management import call_command

def cleanup():
    """Run cleanup command."""
    print("\n🧹 Cleaning up todo app data...")
    try:
        call_command('cleanup_todo')
    except Exception as e:
        print(f"Cleanup error: {e}")

def signal_handler(sig, frame):
    """Handle shutdown signals."""
    print("\n👋 Shutting down...")
    cleanup()  # Clean AFTER running
    sys.exit(0)

if __name__ == "__main__":
    # Only run setup on main process, not on reload
    if os.environ.get('RUN_MAIN') != 'true':
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
        
        # Setup Django
        import django
        django.setup()
        
        # Register cleanup handlers
        atexit.register(cleanup)  # Clean on normal exit
        signal.signal(signal.SIGINT, signal_handler)  # Clean on Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Clean on termination
        
        # Clean before starting
        cleanup()
        
        # Run migrations
        print("\n📦 Running migrations...")
        call_command('migrate', '--noinput')
        
        # Create sample data
        print("\n📝 Creating sample data...")
        try:
            call_command('create_sample_data')
        except Exception as e:
            print(f"Sample data creation failed: {e}")
    
    # Start server (this will run on both main and reload)
    print("\n🚀 Starting server...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'runserver', '8000'])