# Utility Scripts

This directory contains helper scripts for database initialization, workflow scheduling, and other utility functions.

## Overview

These scripts provide various utilities for managing The Assistant application:

1. Database initialization and management
2. Workflow scheduling using Temporal's CLI
3. Testing and development utilities
4. User management

## Available Scripts

### 1. Database Initialization

`init_db.py` - Creates the database and tables with proper schema.

```bash
# Basic usage (uses environment variables)
uv run python scripts/init_db.py

# Custom database URL
uv run python scripts/init_db.py --database-url "postgresql://user:password@localhost:5432/the_assistant"

# Verbose logging
uv run python scripts/init_db.py --verbose
```

Required parameters:
- `DB_ENCRYPTION_KEY`: Encryption key for sensitive data (from environment variable or command line)

Optional parameters:
- `--database-url`: Database connection URL (default: from `DATABASE_URL` env var)
- `--encryption-key`: Encryption key (default: from `DB_ENCRYPTION_KEY` env var)
- `--verbose`: Enable verbose logging

### 2. Schedule Morning Briefing

`schedule-morning-briefing.sh` - Creates a recurring schedule for the morning briefing workflow.

```bash
# Basic usage (uses defaults)
./scripts/schedule-morning-briefing.sh

# Custom schedule
./scripts/schedule-morning-briefing.sh --cron "0 7 * * 1-5" --schedule-id "workday-briefing"
```

Default settings:
- Schedule ID: `morning-briefing`
- Cron: `0 8 * * *` (8:00 AM daily)
- Workflow Type: `MorningBriefingWorkflow`
- Task Queue: `the-assistant`

### 2. Schedule Trip Monitor

`schedule-trip-monitor.sh` - Creates a recurring schedule for the trip monitoring workflow.

```bash
# Basic usage (uses defaults)
./scripts/schedule-trip-monitor.sh

# Custom schedule
./scripts/schedule-trip-monitor.sh --cron "0 18 * * *" --schedule-id "evening-trip-check"
```

Default settings:
- Schedule ID: `trip-monitor`
- Cron: `0 9 * * *` (9:00 AM daily)
- Workflow Type: `TripMonitorWorkflow`
- Task Queue: `the-assistant`

### 3. Run Workflow Once

`run-workflow-once.sh` - Executes a workflow once for testing or manual triggering.

```bash
# Run morning briefing workflow once
./scripts/run-workflow-once.sh --workflow-id test-morning-briefing --workflow-type MorningBriefingWorkflow

# Run trip monitor workflow with parameters
./scripts/run-workflow-once.sh --workflow-id test-trip-monitor --workflow-type TripMonitorWorkflow --input '{"daysAhead": 30}'
```

Required parameters:
- `--workflow-id`: Unique identifier for this workflow execution
- `--workflow-type`: Type of workflow to execute

## Common Options for All Scripts

All scripts support the following options:

- `--task-queue`: Temporal task queue (default: `the-assistant`)
- `--address`: Temporal server address (default: `localhost:7233` or `$TEMPORAL_HOST`)
- `--namespace`: Temporal namespace (default: `default` or `$TEMPORAL_NAMESPACE`)
- `--help`: Show help message with all available options

## Managing Schedules with Temporal CLI

### View All Schedules

```bash
temporal schedule list
```

### View Schedule Details

```bash
temporal schedule describe --schedule-id morning-briefing
```

### Pause a Schedule

```bash
temporal schedule pause --schedule-id morning-briefing
```

### Unpause a Schedule

```bash
temporal schedule unpause --schedule-id morning-briefing
```

### Delete a Schedule

```bash
temporal schedule delete --schedule-id morning-briefing
```

### Trigger a Schedule Immediately

```bash
temporal schedule trigger --schedule-id morning-briefing
```

## Environment Variables

The scripts respect the following environment variables:

- `TEMPORAL_HOST`: Temporal server address (default: `localhost:7233`)
- `TEMPORAL_NAMESPACE`: Temporal namespace (default: `default`)

You can set these in your `.env` file or export them in your shell before running the scripts.

## Migrating from Application Scheduling

Previously, The Assistant managed workflow scheduling internally through code. This approach has been replaced with these CLI scripts to:

1. Simplify the codebase
2. Provide more flexibility in scheduling
3. Make scheduling more transparent and easier to manage
4. Allow for manual testing and execution

To schedule workflows, simply run the appropriate script instead of relying on the application to handle scheduling.