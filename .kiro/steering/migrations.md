---
inclusion: always
---

# DATABASE MIGRATIONS GUIDE

## Quick Commands (USE THESE FIRST!)
```bash
# ✅ ALWAYS TRY THESE MAKEFILE COMMANDS FIRST
make migrate                 # Apply all pending migrations
make migration-status        # Check current migration state  
make migration-history       # View migration history
make migration MESSAGE="add_new_table"  # Create new migration

# Check if services are running
docker-compose ps           # Ensure postgresql is running
```

## Common Migration Scenarios

### 1. Fresh Setup - Apply All Migrations
```bash
# Start services first
docker-compose up -d

# Apply migrations
make migrate

# Verify
make migration-status
```

### 2. Create New Migration
```bash
# After modifying models in src/the_assistant/db/models.py
make migration MESSAGE="add_user_preferences_table"

# Review the generated migration file in alembic/versions/
# Then apply it
make migrate
```

### 3. Check Migration Status
```bash
make migration-status       # Shows current revision
make migration-history      # Shows all migrations and their relationships
```

## Troubleshooting Migration Issues

### Issue: "Can't locate revision identified by 'XXXXX'"
**Cause**: Database has a revision that doesn't exist in current migration files

**Solution**:
```bash
# 1. Check what revision database thinks it's at
docker exec temporal-postgresql psql -U temporal -d the_assistant -c "SELECT * FROM alembic_version;"

# 2. Check available revisions
make migration-history

# 3. If revision doesn't exist, reset to a valid one (use base revision from history)
docker exec temporal-postgresql psql -U temporal -d the_assistant -c "UPDATE alembic_version SET version_num = '7cc1a1bbfedb';"

# 4. Apply migrations
make migrate
```

### Issue: Multiple heads in migration history
**Cause**: Parallel development created branching migrations

**Solution**:
```bash
# 1. Check for multiple heads
make migration-history

# 2. Merge heads (creates a merge migration)
DATABASE_URL="postgresql+asyncpg://temporal:temporal@localhost:5432/the_assistant" uv run alembic merge heads -m "merge migration heads"

# 3. Apply the merge
make migrate
```

### Issue: Database connection failed
**Cause**: PostgreSQL not running or wrong credentials

**Solution**:
```bash
# 1. Check if database is running
docker-compose ps

# 2. Start if not running
docker-compose up -d postgresql

# 3. Wait a moment for startup, then try again
make migrate
```

## Database Connection Details
- **Host**: localhost (when running locally)
- **Port**: 5432
- **User**: temporal
- **Password**: temporal  
- **Database**: the_assistant
- **Full URL**: `postgresql://temporal:temporal@localhost:5432/the_assistant`

## Migration File Locations
- **Migration files**: `alembic/versions/`
- **Alembic config**: `alembic.ini`
- **Alembic env**: `alembic/env.py`
- **Database models**: `src/the_assistant/db/models.py`

## Best Practices
1. **Always use Makefile commands first** - they handle environment setup correctly
2. **Review generated migrations** before applying them
3. **Test migrations on development data** before production
4. **Keep migration messages descriptive**: "add_user_preferences_table" not "update"
5. **One logical change per migration** - don't bundle unrelated changes

## Emergency Reset (DESTRUCTIVE - USE WITH CAUTION)
```bash
# ⚠️ THIS WILL DELETE ALL DATA ⚠️
# Only use in development when you need a clean slate

# 1. Stop services
docker-compose down

# 2. Remove database volume
docker volume rm the-assistant_postgres-data

# 3. Start services (creates fresh database)
docker-compose up -d

# 4. Initialize database with all migrations
uv run python scripts/init_db_with_migrations.py --verbose
```