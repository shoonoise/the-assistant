---
inclusion: always
---

# PROJECT STRUCTURE & ARCHITECTURE

## Core Architecture Principles

This is a **Temporal-based personal workflow automation** system with Google Calendar, Obsidian, and Telegram integrations. Follow these patterns strictly:

### Temporal Architecture (MANDATORY)
- **Workflows** = Orchestration logic only (no external calls)
- **Activities** = Atomic external operations (idempotent, retryable)
- **Clients** = API wrappers returning Pydantic models

### Directory Structure (CURRENT STATE)
```
src/the_assistant/
├── workflows/               # Business logic orchestration
│   └── daily_briefing.py    # Morning summary workflow (only workflow so far)
├── activities/              # External operations (grouped by domain)
│   ├── google_activities.py # Calendar operations
│   ├── obsidian_activities.py # Note reading, writing, parsing
│   ├── telegram_activities.py # Message sending, user interaction
│   ├── messages_activities.py # Message processing and formatting
│   ├── user_activities.py   # User preference management
│   └── weather_activities.py # Weather data fetching
├── integrations/            # Service clients (organized by service)
│   ├── google/              # Google API integration
│   │   ├── client.py        # Main Google API client
│   │   ├── credential_store.py # OAuth credential management
│   │   ├── oauth_router.py  # OAuth flow handling
│   │   └── oauth_state.py   # OAuth state management
│   ├── obsidian/            # Obsidian vault integration
│   │   ├── obsidian_client.py # Main Obsidian client
│   │   ├── vault_manager.py # Vault file operations
│   │   ├── markdown_parser.py # Markdown parsing logic
│   │   ├── metadata_extractor.py # Note metadata extraction
│   │   ├── filter_engine.py # Note filtering and search
│   │   ├── models.py        # Obsidian-specific models
│   │   └── exceptions.py    # Obsidian-specific errors
│   ├── telegram/            # Telegram bot integration
│   │   ├── telegram_client.py # Bot API client
│   │   └── constants.py     # Telegram-specific constants
│   ├── llm/                 # LLM integration
│   │   ├── agent.py         # LLM agent wrapper
│   │   ├── task_parser.py   # Task extraction from text
│   │   └── countdown_parser.py # Date/time parsing
│   ├── weather/             # Weather service integration
│   │   └── weather_client.py # Weather API client
│   ├── agent_tools.py       # MCP agent tools
│   └── mcp_client.py        # Model Context Protocol client
├── models/                  # Pydantic models (grouped by domain)
│   ├── base.py              # Base model classes
│   ├── activity_models.py   # Activity input/output models
│   ├── google.py            # Google API models
│   ├── obsidian.py          # Obsidian note models
│   └── weather.py           # Weather data models
├── db/                      # Database operations
│   ├── models.py            # SQLAlchemy table definitions
│   ├── database.py          # Database connection setup
│   └── service.py           # Database service layer
├── static/                  # Static web assets
│   ├── auth-success.html    # OAuth success page
│   └── auth-error.html      # OAuth error page
├── main.py                  # FastAPI application entry point
├── worker.py                # Temporal worker setup
├── telegram_bot.py          # Telegram bot setup
├── settings.py              # Configuration management
└── user_settings.py         # User preference handling
```

## File Naming Conventions (STRICT)
- **Workflows**: `{purpose}.py` → `daily_briefing.py`, `trip_planning.py`
- **Activities**: `{domain}_activities.py` → `google_activities.py`, `obsidian_activities.py`
- **Clients**: `{service}_client.py` → `google_client.py`, `telegram_client.py`
- **Models**: `{domain}.py` → `calendar.py`, `obsidian.py`

## Component Responsibilities

### Workflows (Orchestration Only)
- **Purpose**: Define business logic flow, coordinate activities
- **Rules**: No direct external API calls, only activity orchestration
- **Contains**: State management, decision logic, error handling
- **Example**: Daily briefing that fetches calendar, processes notes, sends summary

### Activities (Atomic Operations)
- **Purpose**: Single external operation that can be retried safely
- **Rules**: Must be idempotent, handle their own errors appropriately
- **Contains**: API calls, file operations, data transformations
- **Example**: Fetch calendar events for date range, parse Obsidian note

### Integrations (API Wrappers)
- **Purpose**: Abstract external service APIs, handle auth and rate limits
- **Rules**: Return Pydantic models, not raw JSON. Do NOT handle retries - let Temporal do that
- **Contains**: Authentication, request/response mapping, error translation
- **Example**: Google Calendar client that handles OAuth and returns CalendarEvent objects

### Models (Data Structures)
- **Purpose**: Define data contracts between components
- **Rules**: Use Pydantic for validation, group by business domain
- **Contains**: Field definitions, validation rules, serialization logic
- **Example**: CalendarEvent with start/end times, attendees, location

### Database Layer
- **Purpose**: Persistent storage for workflow state and user data
- **Rules**: Use repository pattern, async operations, proper transactions
- **Contains**: SQLAlchemy models, data access objects, connection management
- **Example**: Store workflow execution history, user preferences, cached data

## Testing Structure
```
tests/
├── unit/                    # Mock all external dependencies
│   ├── test_activities/     # Activity unit tests
│   ├── test_workflows/      # Workflow unit tests
│   ├── test_integrations/   # Client unit tests
│   └── test_db/            # Database operation tests
├── integration/             # Real services with test data only
│   ├── test_google_integration.py
│   ├── test_obsidian_integration.py
│   └── test_telegram_integration.py
└── conftest.py             # Shared fixtures and test configuration
```