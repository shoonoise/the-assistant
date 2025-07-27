---
inclusion: always
---

# CRITICAL EXECUTION RULES

## Python Environment (MANDATORY - WILL FAIL OTHERWISE)
```bash
# ✅ CORRECT - Always use uv
uv run python script.py
uvx package_name

# ❌ WRONG - Will fail in this environment
python script.py
pip install package
```

## Code Style (NON-NEGOTIABLE)
- **Type hints**: REQUIRED on ALL functions: `def func(x: str) -> dict[str, int]:`
- **Built-in types**: Use `dict`, `list`, `tuple` (NOT `Dict`, `List`, `Tuple`)
- **Naming**: snake_case for files/functions/variables (NEVER camelCase)
- **Async**: Use async/await consistently throughout
- **Imports**: ALWAYS at top of file - Standard library → Third-party → Local (blank line separated)

## Architecture Patterns (TEMPORAL-FIRST)

### Workflows = Orchestration Only
```python
@workflow.defn
class ProcessTripWorkflow:
    @workflow.run
    async def run(self, trip_data: TripInput) -> TripResult:
        # Orchestrate activities, handle state
        calendar_events = await workflow.execute_activity(
            get_calendar_events,
            trip_data.date_range,
            start_to_close_timeout=timedelta(minutes=2)
        )
        return TripResult(events=calendar_events)
```

### Activities = Atomic External Operations
```python
@activity.defn
async def get_calendar_events(date_range: DateRange) -> list[CalendarEvent]:
    """Must be idempotent - can be retried safely"""
    client = GoogleClient()
    return await client.get_events(date_range)
```

### Integration Clients = API Wrappers
```python
class GoogleClient:
    async def get_events(self, date_range: DateRange) -> list[CalendarEvent]:
        """Return Pydantic models, not raw JSON"""
        # Handle auth, retries, rate limits
        pass
```

## Essential Commands
```bash
# Setup
uv sync --group dev && uv run lefthook install

# Development cycle
make fix && make test        # Format, lint, test
make serve                   # Start FastAPI server
docker-compose up -d         # Start all services

# Database migrations
uv run python scripts/create_migration.py "description"
uv run python scripts/init_db_with_migrations.py
```

## Security & Configuration (CRITICAL)

### Secrets = Files Only
```bash
# ✅ CORRECT - Secrets as mounted files
/secrets/google_credentials.json
/secrets/telegram_token

# ❌ WRONG - Never in environment variables
GOOGLE_CREDENTIALS="{...}"
```

### Settings Pattern
```python
# Access config through centralized settings
from the_assistant.settings import get_settings
settings = get_settings()
```

## File Organization (STRICT STRUCTURE)
```
src/the_assistant/
├── workflows/           # One workflow per file
├── activities/          # Grouped by domain (google_activities.py)
├── integrations/        # Named {service}_client.py
├── models/             # Pydantic models by domain
└── db/                 # Database operations
```

## Testing Patterns
```python
# Unit tests - Mock everything external
@pytest.mark.asyncio
async def test_get_calendar_events():
    with patch('google_client.GoogleClient') as mock:
        result = await get_calendar_events(date_range)
        assert isinstance(result, list)

# Workflow tests - Use Temporal test framework
async def test_trip_workflow():
    async with WorkflowEnvironment() as env:
        result = await env.client.execute_workflow(
            ProcessTripWorkflow.run,
            trip_input,
            id="test-trip",
            task_queue="test"
        )
```