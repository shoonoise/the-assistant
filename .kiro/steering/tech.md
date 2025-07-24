---
inclusion: always
---

# Technical Implementation Guidelines

## Critical Execution Rules

**Python Environment (MANDATORY):**
- ALWAYS use `uv run python ...` - never bare `python` commands
- Use `uvx package_name` for one-off utilities
- Virtual environment managed by uv - direct python calls will fail

**Code Style Requirements:**
- Python 3.13+ built-in types: `dict`, `list`, `tuple` (not `Dict`, `List`, `Tuple`)
- Type hints REQUIRED on ALL function signatures and return types
- snake_case naming for files, functions, variables
- Async/await patterns consistently throughout
- Import order: standard library, third-party, local modules (with blank line separation)

## Core Technology Stack

- **Temporal**: Workflow orchestration - use for business logic and external service coordination
- **FastAPI**: Web framework for webhooks and API endpoints
- **SQLAlchemy + Alembic**: Database ORM with async sessions and migrations
- **Pydantic**: Data validation and serialization for all models
- **Docker Compose**: Development environment orchestration

## Temporal Architecture Patterns

**Workflows** - Orchestration only:
```python
@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input_data: MyInput) -> MyOutput:
        result = await workflow.execute_activity(
            my_activity,
            input_data,
            start_to_close_timeout=timedelta(minutes=5)
        )
        return result
```

**Activities** - Atomic external operations:
```python
@activity.defn
async def my_activity(input_data: MyInput) -> MyOutput:
    # Must be idempotent and handle retries gracefully
    # Fail fast on authentication/configuration errors
    pass
```

**Error Handling:**
- Use `RetryPolicy` for activities with exponential backoff
- Structured logging with workflow_id and activity_id context
- Fail fast on authentication/configuration errors

## Development Commands

**Setup:**
```bash
uv sync --group dev          # Install dependencies
uv run lefthook install      # Setup git hooks
```

**Quality & Testing:**
```bash
make fix                     # Auto-format and lint
make test                    # Run test suite
make test-cov               # Run with coverage
```

**Services:**
```bash
make serve                   # Start FastAPI server
docker-compose up -d         # Start all services
```

**Database:**
```bash
uv run python scripts/create_migration.py "description"
uv run python scripts/init_db_with_migrations.py
```

## Configuration & Security

**Environment Variables:**
- Access through centralized `src/the_assistant/settings.py`
- Use Pydantic `BaseSettings` for validation
- Never hardcode configuration values

**Secrets Management:**
- Mount secrets as files in `/secrets/` directory
- OAuth tokens stored in database with encryption
- NEVER store secrets in environment variables or code

**Database:**
- Use Alembic for schema migrations
- Async SQLAlchemy sessions throughout
- Connection pooling configured in `database.py`

## Integration Client Patterns

**Client Structure:**
```python
class ServiceClient:
    def __init__(self, credentials: ServiceCredentials):
        self.credentials = credentials
        self._service = None
    
    async def _get_service(self):
        if not self._service:
            # Initialize service with credentials
            pass
        return self._service
```

**Requirements:**
- Wrap ALL external API calls with proper exception handling
- Return structured Pydantic models, not raw JSON
- Implement exponential backoff for rate limits
- Named as `{service}_client.py` (e.g., `google_client.py`)

## Testing Requirements

**Unit Tests:**
```python
@pytest.mark.asyncio
async def test_activity_function():
    with patch('external_service') as mock_service:
        result = await my_activity(test_input)
        assert result.expected_field == "expected_value"
```

**Temporal Workflow Tests:**
```python
async def test_workflow():
    async with WorkflowEnvironment() as env:
        async with Worker(env.client, task_queue="test"):
            result = await env.client.execute_workflow(
                MyWorkflow.run,
                test_input,
                id="test-workflow",
                task_queue="test"
            )
```

**Testing Strategy:**
- Mock ALL external integrations in unit tests
- Use Temporal test framework for workflow testing
- Integration tests with real services using test data only
- Test retry logic and error handling paths