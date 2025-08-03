# Embedded Replica Demo App

This Django app demonstrates the power of libSQL embedded replicas with:
- High-performance local writes
- Background syncing to Turso
- Multi-threaded sensor data processing
- Real-world IoT use case

## Features

1. **Sensor Data Simulation**: Simulates multiple IoT sensors generating temperature/humidity readings
2. **Multi-threaded Processing**: Uses Python's threading (even better with no-GIL!)
3. **Local Performance**: Writes go to local SQLite for microsecond latency
4. **Background Sync**: Automatic sync to Turso every 5 seconds
5. **Manual Sync Control**: Sync on-demand for critical operations
6. **Analytics**: Aggregates sensor data with eventual consistency

## Setup

1. Set environment variables:
```bash
export TURSO_DATABASE_URL="libsql://your-database.turso.io"
export TURSO_AUTH_TOKEN="your-auth-token"
```

2. Create the database schema:
```bash
cd examples/embedded_replica_app
python -c "import django; django.setup(); from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', 'migrate'])"
```

## Running the Demo

```bash
cd examples/embedded_replica_app
python demo.py
```

## What It Demonstrates

### 1. Consistency Patterns
- **Write-through**: Immediate sync after critical writes
- **Batch writes**: Let background sync handle non-critical data
- **Fresh reads**: Sync before reading when you need latest data

### 2. Performance Benefits
- Local writes are extremely fast (no network latency)
- Background sync doesn't block your application
- Perfect for IoT, edge computing, or high-throughput scenarios

### 3. Threading + No-GIL
- Multiple threads can write to local replica concurrently
- With no-GIL Python, true parallelism for CPU-intensive operations
- Each thread's writes are immediately visible locally

### 4. Real-World Pattern
The app simulates an IoT scenario where:
- Sensors generate data continuously
- Data is written locally for reliability
- Background sync ensures data reaches the cloud
- Analytics run on aggregated data

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Sensor 001    │     │   Sensor 002    │     │   Sensor 003    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┴───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Local Replica (SQLite)│
                    │   - Fast local writes   │
                    │   - Immediate reads     │
                    └────────────┬────────────┘
                                 │
                         Background Sync
                          (every 5 sec)
                                 │
                    ┌────────────▼────────────┐
                    │   Remote Turso Database │
                    │   - Durable storage     │
                    │   - Global access       │
                    └─────────────────────────┘
```

## Monitoring

The app includes sync monitoring:
- Tracks each sync operation
- Measures sync duration
- Logs success/failure
- Helps optimize SYNC_INTERVAL setting