---
inclusion: always
---

# The Assistant - Development Guidelines

Personal workflow automation using Temporal orchestration with Google Calendar, Obsidian, and Telegram integrations.

## Execution Requirements

**Python Environment:**
- ALWAYS use `uv run python ...` (never bare `python` commands)
- Python 3.13+ with built-in types (`dict`, `list`, `tuple`)
- Type hints required on all function signatures
- snake_case naming for files, functions, variables

**Package Structure:**
- `src/the_assistant/` - main package using src layout
- `workflows/` - Temporal workflows (business logic orchestration)
- `activities/` - Temporal activities (atomic external operations)
- `integrations/` - external API client wrappers

## Architecture Rules

**Temporal Patterns:**
- Workflows: long-running, stateful orchestration
- Activities: idempotent, retryable external operations
- One workflow per file, activities grouped by service domain
- Use Temporal's retry mechanisms, fail fast on config errors

**File Organization:**
- Integration clients named `{service}_client.py`
- Full imports within package: `from the_assistant.integrations import google_client`
- Import order: standard library, third-party, local (blank line separated)

**Configuration:**
- Environment variables via `utils/config.py` only
- Secrets as files in `/secrets/` (never environment variables)
- Obsidian filtering uses tags: `#trip`, `#french-lesson`

## Code Style

- Docstrings for all public functions/classes
- Async/await patterns consistently
- Walrus operator `:=` where appropriate
- Log with sufficient context for debugging

## Testing

- Mock external integrations in unit tests
- Use Temporal test framework for workflows
- Integration tests use real services with test data only
- Validate workflow state transitions and activity outcomes

## Development Commands

```bash
uv sync --group dev    # Setup
make fix              # Format and lint
make test             # Run tests
make serve            # Start FastAPI
docker-compose up -d  # Start services
```

## AI Assistant Principles

- **Minimal Implementation**: Build working solutions, avoid over-engineering
- **Rapid Iteration**: Basic functionality first, refactor when patterns emerge
- **Human-in-Loop**: Use Telegram for user confirmations in workflows
- **Proactive Automation**: Monitor and initiate workflows automatically