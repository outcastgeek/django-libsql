"""
Setup command that runs migrations and creates sample data.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Setup the app by running migrations and creating sample data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up Basic Todo App...\n')
        
        # Run migrations
        self.stdout.write('Running migrations...')
        call_command('migrate', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✓ Migrations complete'))
        
        # Create sample data
        self.stdout.write('Creating sample data...')
        call_command('create_sample_data', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✓ Sample data created'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ App setup complete!'))