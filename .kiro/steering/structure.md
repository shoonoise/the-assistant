# Project Structure

## Directory Organization

```
the-assistant/
├── src/the_assistant/           # Main package (src layout)
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── activities/              # Temporal activities (atomic operations)
│   ├── integrations/            # External service clients
│   ├── utils/                   # Shared utility functions
│   └── workflows/               # Temporal workflows (business logic)
├── tests/                       # Test suite
├── obsidian_vault/             # Mount point for Obsidian vault
├── secrets/                    # File-based secrets (gitignored)
├── .kiro/                      # Kiro IDE configuration
└── dist/                       # Build artifacts
```

## Code Organization Patterns

### Temporal Architecture
- **Workflows** (`workflows/`): High-level business logic, orchestrate activities
- **Activities** (`activities/`): Atomic operations that interact with external services
- **Integrations** (`integrations/`): Client modules for external APIs (Google, Telegram, Obsidian)

### Module Naming Conventions
- Use snake_case for all Python files and directories
- Descriptive names that indicate purpose (e.g., `get_calendar_events.py`, `morning_briefing.py`)
- Integration clients named as `{service}_client.py`

### Import Structure
- Use full imports within the package (`from the_assistant.integrations import google_client`)
- Absolute imports for external dependencies
- Group imports: standard library, third-party, local modules

## File Patterns

### Workflow Files
- Each workflow in separate file under `workflows/`
- Class-based workflow definitions with `@workflow.defn` decorator
- Single `@workflow.run` method as entry point

### Activity Files
- Functions decorated with `@activity.defn`
- Pure functions that can be retried safely
- Error handling with proper logging

### Integration Files
- Client classes or functions for external services
- Credential management and authentication
- Consistent error handling and return types

### Configuration Files
- `pyproject.toml`: Python package configuration and dependencies
- `.env.example`: Template for environment variables
- `docker-compose.yml`: Service orchestration
- `Makefile`: Development commands and shortcuts

## Testing Structure
- `tests/unit/`: Unit tests for individual functions
  - `tests/unit/test_activities.py`: Tests for Temporal activities
  - `tests/unit/test_utils.py`: Tests for utility functions
  - `tests/unit/integrations/`: Tests for integration clients
    - `tests/unit/integrations/obsidian/`: Obsidian-specific tests
- `tests/integration/`: End-to-end workflow testing
  - `tests/integration/test_workflows.py`: Workflow integration tests
  - `tests/integration/test_obsidian_integration.py`: Obsidian integration tests
  - `tests/integration/test_google_integration.py`: Google API integration tests
- Use `pytest` framework with async support
- Mock external dependencies in unit tests

## Development Conventions
- Use `src/` layout for proper package isolation
- All modules have `__init__.py` files
- Type hints on function signatures
- Docstrings for public functions and classes
- Environment variables accessed through `utils/helpers.py`
- Secrets mounted as files, not environment variables