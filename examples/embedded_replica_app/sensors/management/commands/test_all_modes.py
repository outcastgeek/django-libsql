"""
Management command that runs the app in ALL required modes automatically:
1. Regular Python
2. Python with Threads  
3. Python with Threads + No-GIL
4. Python with Threads + No-GIL + Django ORM

NO MANUAL INTERVENTION REQUIRED!
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Test embedded replica app in ALL modes automatically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--duration',
            type=int,
            default=10,
            help='Duration for each test (seconds)'
        )

    def handle(self, *args, **options):
        duration = options['duration']
        
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write("EMBEDDED REPLICA APP - ALL MODES TEST")
        self.stdout.write(f"{'='*80}\n")
        
        # Define all test modes
        test_modes = [
            {
                'name': 'Regular Python (Single-threaded)',
                'env': {},
                'args': ['--mode', 'single', '--duration', str(duration)]
            },
            {
                'name': 'Python with Threads',
                'env': {},
                'args': ['--mode', 'multi', '--threads', '4', '--duration', str(duration)]
            },
            {
                'name': 'Python with Threads + No-GIL',
                'env': {'PYTHON_GIL': '0'},
                'args': ['--mode', 'multi', '--threads', '8', '--duration', str(duration)]
            },
            {
                'name': 'Embedded Replica + Threads',
                'env': {'USE_EMBEDDED_REPLICA': '1'},
                'args': ['--mode', 'multi', '--threads', '4', '--duration', str(duration)]
            },
            {
                'name': 'Embedded Replica + Threads + No-GIL',
                'env': {'USE_EMBEDDED_REPLICA': '1', 'PYTHON_GIL': '0'},
                'args': ['--mode', 'multi', '--threads', '8', '--duration', str(duration)]
            }
        ]
        
        results = []
        
        for mode in test_modes:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"Testing: {mode['name']}")
            self.stdout.write(f"{'='*70}")
            
            # Check if no-GIL is available
            if mode['env'].get('PYTHON_GIL') == '0':
                if not self.check_no_gil():
                    self.stdout.write(self.style.WARNING("⚠️  Skipping - No-GIL not available"))
                    continue
            
            # Run test in subprocess
            result = self.run_test_mode(mode['env'], mode['args'])
            result['mode'] = mode['name']
            results.append(result)
            
            # Show result
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"✅ PASSED - {result['throughput']:.2f} records/sec"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ FAILED - {result['error']}"))
        
        # Summary
        self.show_summary(results)

    def run_test_mode(self, env_vars, args):
        """Run simulate_sensors command in specific mode."""
        # Build command
        cmd = [
            sys.executable,
            'manage.py',
            'simulate_sensors'
        ] + args
        
        # Add -X gil=0 if no-GIL
        if env_vars.get('PYTHON_GIL') == '0':
            cmd.insert(1, '-X')
            cmd.insert(2, 'gil=0')
        
        # Set up environment
        env = os.environ.copy()
        env.update(env_vars)
        
        # Run command
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                cwd=settings.BASE_DIR,
                timeout=60
            )
            duration = time.time() - start_time
            
            if result.returncode == 0:
                # Parse output for metrics
                throughput = self.parse_throughput(result.stdout)
                return {
                    'success': True,
                    'duration': duration,
                    'throughput': throughput,
                    'stdout': result.stdout[-500:]  # Last 500 chars
                }
            else:
                return {
                    'success': False,
                    'duration': duration,
                    'error': result.stderr[-500:],
                    'throughput': 0
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'duration': 60,
                'error': 'Timeout',
                'throughput': 0
            }

    def parse_throughput(self, output):
        """Extract throughput from command output."""
        for line in output.split('\n'):
            if 'Throughput:' in line:
                try:
                    parts = line.split(':')
                    value = float(parts[1].split()[0])
                    return value
                except:
                    pass
        return 0

    def check_no_gil(self):
        """Check if no-GIL Python is available."""
        try:
            result = subprocess.run(
                [sys.executable, '-X', 'gil=0', '-c', 'import sys; sys.exit(0)'],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False

    def show_summary(self, results):
        """Show performance comparison summary."""
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write("PERFORMANCE SUMMARY")
        self.stdout.write(f"{'='*80}\n")
        
        # Group by configuration
        gil_results = [r for r in results if 'No-GIL' not in r['mode']]
        nogil_results = [r for r in results if 'No-GIL' in r['mode']]
        embedded_results = [r for r in results if 'Embedded' in r['mode']]
        remote_results = [r for r in results if 'Embedded' not in r['mode']]
        
        # Calculate improvements
        if gil_results and nogil_results:
            self.stdout.write("GIL vs No-GIL Performance:")
            for gil_r in gil_results:
                # Find matching no-GIL result
                base_name = gil_r['mode'].replace('Python with Threads', '').strip()
                for nogil_r in nogil_results:
                    if base_name in nogil_r['mode']:
                        if gil_r['throughput'] > 0:
                            improvement = ((nogil_r['throughput'] - gil_r['throughput']) / gil_r['throughput']) * 100
                            self.stdout.write(
                                f"  {base_name}: {gil_r['throughput']:.1f} → {nogil_r['throughput']:.1f} "
                                f"({improvement:+.1f}%)"
                            )
                        break
        
        self.stdout.write("\nAll Results:")
        for result in results:
            status = "✅" if result['success'] else "❌"
            self.stdout.write(
                f"  {status} {result['mode']}: {result['throughput']:.2f} records/sec"
            )
        
        # Save results
        report_path = settings.BASE_DIR / 'test_report.json'
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': results
            }, f, indent=2)
        
        self.stdout.write(f"\nDetailed report saved to: {report_path}")