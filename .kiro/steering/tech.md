---
inclusion: always
---

# Technology Stack & Development Guidelines

## Core Technologies
- **Python 3.13+**: Use modern syntax, built-in types (`dict`, `list`, `tuple`), async/await patterns
- **Temporal**: Workflow orchestration - workflows orchestrate, activities execute external operations
- **FastAPI**: Web framework for webhooks and API endpoints
- **Docker Compose**: Container orchestration for development and deployment

## Code Style Requirements
- Type hints required for all function signatures and return types
- Use modern Python 3.13+ built-in types (no `from __future__ import annotations` needed)
- snake_case naming for files, functions, variables
- Docstrings for all public functions and classes
- Import order: standard library, third-party, local modules (grouped with blank lines)
- Use full imports within package: `from the_assistant.integrations import google_client`

## Architecture Patterns
- **Workflows** (`workflows/`): Orchestrate business logic, keep stateful and long-running
- **Activities** (`activities/`): Atomic, idempotent operations for external services
- **Integration Clients** (`integrations/`): Wrap all external API calls in dedicated client classes
- **Error Handling**: Use Temporal's retry mechanisms in activities, fail fast on config errors
- **Human-in-the-Loop**: Use Telegram for user confirmations within workflows

## Package Management
- **Always use `uv`** for Python execution and dependency management (never pip)
- **uvx**: For running one-off Python utilities
- Dependencies organized in groups: main, dev, test
- Use `make` commands for common development tasks

## Development Commands
```bash
# Setup
uv sync --group dev
uv run lefthook install

# Code quality
make fix        # Format and lint (auto-fix)
make check      # Check without fixing
make test       # Run tests
make test-cov   # Run tests with coverage

# Development
make serve      # Start FastAPI server
docker-compose up -d  # Start all services

# Running Python scripts
uv run python script_name.py  # Always use uv run, never just python
```

## Python Execution Guidelines
- **ALWAYS use `uv run python ...`** instead of just `python ...`
- The virtual environment is managed by uv, so direct python calls won't work
- For one-off utilities, use `uvx package_name` 
- Never activate venv manually - let uv handle it

## Configuration & Security
- Environment variables accessed through `utils/helpers.py` centralized functions
- Secrets mounted as files in `/secrets/` directory (never in environment variables)
- Use `.env` files for configuration (never commit secrets)
- Tag-based filtering for Obsidian notes (e.g., `#trip`, `#french-lesson`)

## Testing Requirements
- Mock external integrations in unit tests
- Use Temporal's test framework for workflow testing
- Integration tests use real services with test data only
- Validate workflow state transitions and activity outcomes