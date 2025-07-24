---
inclusion: always
---

# The Assistant - AI Development Guidelines

Personal workflow automation system using Temporal orchestration with Google Calendar, Obsidian, and Telegram integrations.

## Critical Execution Rules

**Python Environment (MANDATORY):**
- ALWAYS use `uv run python ...` - never bare `python` commands
- Python 3.13+ with built-in types (`dict`, `list`, `tuple`) - no `typing` imports needed
- Type hints REQUIRED on ALL function signatures and return types
- snake_case naming for files, functions, variables (never camelCase)

**Package Structure (STRICT):**
- `src/the_assistant/` - main package using src layout
- `workflows/` - Temporal workflows (orchestrate business logic)
- `activities/` - Temporal activities (atomic external operations)
- `integrations/` - external API client wrappers
- `models/` - Pydantic data models
- `db/` - database operations

## Temporal Architecture (CORE PATTERNS)

**Workflows:**
- Long-running, stateful orchestration only
- One workflow per file in `workflows/`
- Use `@workflow.defn` decorator
- Single `@workflow.run` method as entry point
- Handle human-in-the-loop via Telegram confirmations

**Activities:**
- Atomic, idempotent external operations
- Use `@activity.defn` decorator
- Group by service domain in `activities/`
- Must be retryable - use Temporal's retry mechanisms
- Fail fast on configuration errors

**Integration Clients:**
- Named `{service}_client.py` (e.g., `google_client.py`)
- Wrap ALL external API calls
- Handle authentication and credential management
- Return structured data types, not raw JSON

## Code Style Requirements

**Imports (ENFORCED ORDER):**
1. Standard library
2. Third-party packages
3. Local modules (`from the_assistant.integrations import google_client`)
- Separate groups with blank lines
- Use full imports within package

**Function Requirements:**
- Docstrings for ALL public functions and classes
- Async/await patterns consistently
- Use walrus operator `:=` for assignment expressions
- Log with sufficient context for debugging workflow failures

**Error Handling:**
- Use Temporal's built-in retry mechanisms in activities
- Structured logging with context
- Fail fast on configuration/authentication errors

## Configuration & Security

**Environment Variables:**
- Access ONLY through centralized `utils/config.py` functions
- Never hardcode values in source code

**Secrets Management:**
- Secrets as files in `/secrets/` directory (mounted volumes)
- NEVER store secrets in environment variables
- Use proper credential stores for OAuth tokens

**Obsidian Integration:**
- Tag-based filtering: `#trip`, `#french-lesson`, `#work`
- Markdown parsing with metadata extraction
- Backup files before modifications

## Testing Strategy

**Unit Tests:**
- Mock ALL external integrations
- Test individual functions in isolation
- Use pytest with async support

**Integration Tests:**
- Use Temporal test framework for workflows
- Real services with test data only
- Validate state transitions and activity outcomes
- Test retry logic and error handling paths

## Development Workflow

**Setup Commands:**
```bash
uv sync --group dev    # Install dependencies
make fix              # Format and lint code
make test             # Run test suite
make serve            # Start FastAPI server
docker-compose up -d  # Start all services
```

**File Creation Patterns:**
- Activities: `{domain}_activities.py` (e.g., `google_activities.py`)
- Workflows: `{purpose}_workflow.py` (e.g., `daily_briefing.py`)
- Models: `{domain}.py` in `models/` (e.g., `google.py`)
- Tests: Mirror source structure in `tests/`

## AI Assistant Principles

**Implementation Strategy:**
- Build minimal working solutions first
- Iterate rapidly, avoid over-engineering
- Implement only current requirements, not future speculation
- Refactor when patterns emerge naturally

**Human Interaction:**
- Use Telegram for user confirmations in workflows
- Provide clear status updates and error messages
- Enable manual intervention points in automated processes

**Automation Goals:**
- Monitor external systems proactively
- Initiate workflows based on triggers
- Maintain data consistency across integrations
- Provide intelligent scheduling and reminders