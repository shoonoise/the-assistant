---
inclusion: always
---

# Best Practices

## Simplicity & Iteration
- Favor simple, working solutions over complex architectures
- Iterate rapidly on minimal implementations rather than building comprehensive systems upfront
- Implement only what's needed for the current use case, not what might be needed in the future
- Refactor code when patterns emerge naturally, not based on speculation
- Avoid generating too many tasks for simple specifications

## Code Style & Quality
- Use type hints for all function signatures and return types
- Use modern Python 3.13+ built-in types: `dict`, `list`, `tuple` instead of `Dict`, `List`, `Tuple`
- No need for `from __future__ import annotations` - not required in Python 3.13+
- Follow snake_case naming for Python files, functions, and variables
- Add docstrings to all public functions and classes
- Use async/await patterns consistently throughout the codebase
- Use walrus operator `:=` for assignment expressions where appropriate
- Import order: standard library, third-party, local modules (grouped with blank lines)
- Use full imports within the package: `from the_assistant.integrations import google_client`

## Architecture Patterns
- **Temporal Workflows**: Orchestrate business logic, keep stateful and long-running
- **Temporal Activities**: Atomic operations that interact with external services, must be idempotent
- **Integration Clients**: Wrap all external API calls in dedicated client classes under `integrations/`
- **Error Handling**: Use Temporal's retry mechanisms in activities, fail fast on config errors
- **Human-in-the-Loop**: Use Telegram for user confirmations and inputs within workflows

## Development Conventions
- Environment variables accessed through `utils/helpers.py` centralized functions
- Secrets mounted as files in `/secrets/` directory, never in environment variables
- Tag-based filtering for Obsidian notes (e.g., `#trip`, `#french-lesson`)
- Use structured data types for API responses, not raw JSON
- Log errors with sufficient context for debugging workflow failures

## Testing Requirements
- Mock external integrations in unit tests
- Use Temporal's test framework for workflow testing
- Integration tests should use real services with test data only
- Validate workflow state transitions and activity outcomes
- Test retry logic and error handling paths

## File Organization
- One workflow per file in `workflows/` directory
- Activities grouped by domain in `activities/` directory
- Integration clients named as `{service}_client.py`
- Use `src/` layout for proper package isolation
- All modules must have `__init__.py` files

## Package Management
- Use `uv` for dependency management (preferred over pip)
- Use `uvx` for running one-off Python utilities
- Dependencies organized in groups: main, dev, test
- Use `make` commands for common development tasks
