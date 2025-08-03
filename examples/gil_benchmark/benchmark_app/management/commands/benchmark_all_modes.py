"""
Run benchmarks in ALL required modes automatically:
1. Regular Python
2. Python with Threads  
3. Python with Threads + No-GIL
4. Python with Threads + No-GIL + Django ORM

Also tests both remote-only and embedded replica modes.

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
    help = 'Run benchmarks in ALL modes automatically'

    def handle(self, *args, **options):
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write("COMPREHENSIVE BENCHMARK - ALL MODES")
        self.stdout.write(f"{'='*80}\n")
        
        # All test configurations
        configurations = [
            # Remote-only configurations
            {
                'name': 'Remote + Single-thread + GIL',
                'env': {},
                'args': ['--threads', '1', '--operations', '500']
            },
            {
                'name': 'Remote + Multi-thread + GIL',
                'env': {},
                'args': ['--threads', '4', '--operations', '500']
            },
            {
                'name': 'Remote + Multi-thread + No-GIL',
                'env': {'PYTHON_GIL': '0'},
                'args': ['--threads', '8', '--operations', '500']
            },
            # Embedded replica configurations
            {
                'name': 'Embedded + Single-thread + GIL',
                'env': {'USE_EMBEDDED_REPLICA': '1'},
                'args': ['--threads', '1', '--operations', '500']
            },
            {
                'name': 'Embedded + Multi-thread + GIL',
                'env': {'USE_EMBEDDED_REPLICA': '1'},
                'args': ['--threads', '4', '--operations', '500']
            },
            {
                'name': 'Embedded + Multi-thread + No-GIL',
                'env': {'USE_EMBEDDED_REPLICA': '1', 'PYTHON_GIL': '0'},
                'args': ['--threads', '8', '--operations', '500']
            },
        ]
        
        all_results = []
        
        for config in configurations:
            self.stdout.write(f"\n{'='*70}")
            self.stdout.write(f"Configuration: {config['name']}")
            self.stdout.write(f"{'='*70}")
            
            # Skip no-GIL tests if not available
            if config['env'].get('PYTHON_GIL') == '0':
                if not self.check_no_gil():
                    self.stdout.write(self.style.WARNING("⚠️  Skipping - No-GIL not available"))
                    continue
            
            # Run benchmark
            result = self.run_benchmark(config['name'], config['env'], config['args'])
            all_results.append(result)
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS(f"✅ Completed successfully"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Failed: {result['error']}"))
        
        # Generate comparison report
        self.generate_report(all_results)

    def run_benchmark(self, name, env_vars, args):
        """Run benchmark in subprocess with specific configuration."""
        # Build command
        cmd = [sys.executable]
        
        # Add -X gil=0 if no-GIL
        if env_vars.get('PYTHON_GIL') == '0':
            cmd.extend(['-X', 'gil=0'])
        
        cmd.extend(['manage.py', 'run_benchmark'] + args)
        
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
                timeout=120  # 2 minute timeout
            )
            duration = time.time() - start_time
            
            if result.returncode == 0:
                # Parse results from output
                metrics = self.parse_metrics(result.stdout)
                return {
                    'name': name,
                    'success': True,
                    'duration': duration,
                    'metrics': metrics,
                    'stdout': result.stdout[-1000:]  # Last 1000 chars
                }
            else:
                return {
                    'name': name,
                    'success': False,
                    'duration': duration,
                    'error': result.stderr[-500:],
                    'metrics': {}
                }
                
        except subprocess.TimeoutExpired:
            return {
                'name': name,
                'success': False,
                'duration': 120,
                'error': 'Timeout',
                'metrics': {}
            }

    def parse_metrics(self, output):
        """Extract metrics from benchmark output."""
        metrics = {}
        
        # Look for throughput values
        for line in output.split('\n'):
            if 'ops/sec' in line and ':' in line:
                try:
                    # Extract test name and throughput
                    parts = line.strip().split(':')
                    if len(parts) >= 2:
                        test_mode = parts[0].strip()
                        throughput_part = parts[1]
                        # Extract number before "ops/sec"
                        throughput = float(throughput_part.split('ops/sec')[0].strip())
                        metrics[test_mode] = throughput
                except Exception:
                    pass
        
        return metrics

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

    def generate_report(self, results):
        """Generate comprehensive comparison report."""
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write("COMPREHENSIVE BENCHMARK REPORT")
        self.stdout.write(f"{'='*80}\n")
        
        # Success summary
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        self.stdout.write(f"Total configurations tested: {len(results)}")
        self.stdout.write(f"Successful: {len(successful)}")
        self.stdout.write(f"Failed: {len(failed)}")
        
        if failed:
            self.stdout.write("\nFailed configurations:")
            for r in failed:
                self.stdout.write(f"  - {r['name']}: {r['error']}")
        
        # Performance comparisons
        self.stdout.write("\n📊 PERFORMANCE COMPARISONS:")
        
        # 1. GIL vs No-GIL
        self.stdout.write("\n1. GIL vs No-GIL Impact:")
        gil_comparisons = [
            ('Remote + Multi-thread', 'Remote + Multi-thread + No-GIL'),
            ('Embedded + Multi-thread', 'Embedded + Multi-thread + No-GIL'),
        ]
        
        for base_name, nogil_name in gil_comparisons:
            base_result = next((r for r in successful if base_name + ' + GIL' in r['name']), None)
            nogil_result = next((r for r in successful if nogil_name in r['name']), None)
            
            if base_result and nogil_result:
                self.compare_results(base_result, nogil_result)
        
        # 2. Remote vs Embedded
        self.stdout.write("\n2. Remote vs Embedded Replica:")
        embedded_comparisons = [
            ('Remote + Single-thread + GIL', 'Embedded + Single-thread + GIL'),
            ('Remote + Multi-thread + GIL', 'Embedded + Multi-thread + GIL'),
        ]
        
        for remote_name, embedded_name in embedded_comparisons:
            remote_result = next((r for r in successful if remote_name in r['name']), None)
            embedded_result = next((r for r in successful if embedded_name in r['name']), None)
            
            if remote_result and embedded_result:
                self.compare_results(remote_result, embedded_result)
        
        # 3. Threading impact
        self.stdout.write("\n3. Single vs Multi-threading:")
        thread_comparisons = [
            ('Remote + Single-thread + GIL', 'Remote + Multi-thread + GIL'),
            ('Embedded + Single-thread + GIL', 'Embedded + Multi-thread + GIL'),
        ]
        
        for single_name, multi_name in thread_comparisons:
            single_result = next((r for r in successful if single_name in r['name']), None)
            multi_result = next((r for r in successful if multi_name in r['name']), None)
            
            if single_result and multi_result:
                self.compare_results(single_result, multi_result)
        
        # Save detailed report
        report_path = settings.BASE_DIR / 'benchmark_report.json'
        with open(report_path, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'configurations': len(results),
                'successful': len(successful),
                'results': results
            }, f, indent=2)
        
        self.stdout.write(f"\n📄 Detailed report saved to: {report_path}")

    def compare_results(self, result1, result2):
        """Compare two benchmark results."""
        name1 = result1['name'].replace(' + GIL', '').replace(' + No-GIL', '')
        name2 = result2['name'].replace(' + GIL', '').replace(' + No-GIL', '')
        
        self.stdout.write(f"\n  {result1['name']} vs {result2['name']}:")
        
        # Compare each metric
        for test_type in ['crud', 'read', 'write', 'mixed']:
            # Find matching metrics
            metric1 = None
            metric2 = None
            
            for key, value in result1['metrics'].items():
                if test_type in key.lower():
                    metric1 = value
                    break
            
            for key, value in result2['metrics'].items():
                if test_type in key.lower():
                    metric2 = value
                    break
            
            if metric1 and metric2:
                improvement = ((metric2 - metric1) / metric1) * 100
                self.stdout.write(
                    f"    {test_type}: {metric1:.1f} → {metric2:.1f} ops/sec "
                    f"({improvement:+.1f}%)"
                )