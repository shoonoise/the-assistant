# Database Migrations

This document explains how to manage database migrations in The Assistant project.

## Overview

The project uses Alembic for database migrations with SQLAlchemy models. The migration system has been configured to avoid circular import issues and provides convenient scripts for common operations.

## Quick Start

### Check Current Migration Status
```bash
make migration-status
```

### Apply All Pending Migrations
```bash
make migrate
```

### Create a New Migration
```bash
make migration MESSAGE="add_user_preferences_table"
```

### View Migration History
```bash
make migration-history
```

## Migration Scripts

### `scripts/manage_migrations.py`

The main migration management script that provides a unified interface for all migration operations.

**Usage:**
```bash
# Create a new migration with auto-detection
uv run python scripts/manage_migrations.py create --message "add_user_preferences" --autogenerate --local

# Apply all pending migrations
uv run python scripts/manage_migrations.py apply --local

# Show current migration status
uv run python scripts/manage_migrations.py current --local

# Show migration history
uv run python scripts/manage_migrations.py history --local

# Downgrade one migration
uv run python scripts/manage_migrations.py downgrade -1 --local
```

**Options:**
- `--local`: Use localhost instead of docker hostname for database connection
- `--autogenerate`: Auto-detect model changes when creating migrations
- `--target`: Specify target revision for apply/downgrade operations

## Database Configuration

The migration system automatically detects database configuration from:

1. Environment variables:
   - `DATABASE_URL`: Full database URL (if set)
   - `POSTGRES_USER`: Database user (default: "temporal")
   - `POSTGRES_PASSWORD`: Database password (default: "temporal")
   - `POSTGRES_HOST`: Database host (default: "postgresql" or "localhost" with --local)
   - `POSTGRES_PORT`: Database port (default: "5432")
   - `POSTGRES_DB`: Database name (default: "the_assistant")

2. `.env` file in project root

## Development Workflow

### 1. Start Database
```bash
docker-compose up -d postgresql
```

### 2. Check Current Status
```bash
make migration-status
```

### 3. Apply Existing Migrations
```bash
make migrate
```

### 4. Make Model Changes
Edit files in `src/the_assistant/db/models.py`

### 5. Generate Migration
```bash
make migration MESSAGE="describe_your_changes"
```

### 6. Review Generated Migration
Check the generated file in `alembic/versions/`

### 7. Apply Migration
```bash
make migrate
```

## Production Deployment

For production deployments, use the scripts without the `--local` flag:

```bash
# Apply migrations in production
uv run python scripts/manage_migrations.py apply

# Check status in production
uv run python scripts/manage_migrations.py current
```

## Troubleshooting

### Circular Import Issues
The migration system has been configured to avoid circular imports by:
- Importing models directly in `alembic/env.py`
- Using environment variables for database configuration
- Avoiding imports from the main application modules

### Database Connection Issues
- Ensure PostgreSQL is running: `docker-compose up -d postgresql`
- Check database exists: The `the_assistant` database should exist
- Verify credentials match your environment configuration

### Migration Conflicts
If you encounter migration conflicts:
1. Check current status: `make migration-status`
2. Review history: `make migration-history`
3. Resolve conflicts manually or downgrade: `make migration-downgrade TARGET="-1"`

## Best Practices

1. **Always review generated migrations** before applying them
2. **Use descriptive migration messages** that explain what changed
3. **Test migrations on development data** before production
4. **Backup production database** before applying migrations
5. **Use `--autogenerate`** to detect model changes automatically
6. **Keep migrations small and focused** on single changes when possible

## File Structure

```
alembic/
├── versions/           # Migration files
├── env.py             # Alembic environment configuration
└── script.py.mako     # Migration template

scripts/
├── manage_migrations.py    # Main migration management script
├── create_migration.py     # Legacy creation script
└── apply_migrations.py     # Legacy application script

src/the_assistant/db/
├── models.py          # SQLAlchemy models
├── database.py        # Database connection management
└── service.py         # Database service layer
```