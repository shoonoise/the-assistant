---
inclusion: always
---

# PROJECT STRUCTURE (STRICT LAYOUT)

## Directory Organization
```
src/the_assistant/           # Main package (src layout)
├── workflows/               # Temporal workflows (business logic)
│   ├── daily_briefing.py    # Morning routine workflow
│   └── trip_planning.py     # Travel planning workflow
├── activities/              # Temporal activities (atomic operations)
│   ├── google_activities.py # Google Calendar operations
│   └── obsidian_activities.py # Obsidian note operations
├── integrations/            # External service clients
│   ├── google_client.py     # Google API wrapper
│   └── obsidian_client.py   # Obsidian vault operations
├── models/                  # Pydantic data models
│   ├── calendar.py          # Calendar event models
│   └── obsidian.py          # Note and task models
└── db/                      # Database operations
    └── models.py            # SQLAlchemy models
```

## File Naming Rules (ENFORCED)
- **Workflows**: `{purpose}_workflow.py` → `daily_briefing.py`
- **Activities**: `{domain}_activities.py` → `google_activities.py`
- **Clients**: `{service}_client.py` → `google_client.py`
- **Models**: `{domain}.py` → `calendar.py`
- **Tests**: Mirror source structure in `tests/`

## Module Organization Patterns

### One Workflow Per File
```python
# workflows/daily_briefing.py
# ✅ CORRECT - All imports at top of file
from datetime import timedelta
from temporalio import workflow
from the_assistant.models.briefing import BriefingResult

@workflow.defn
class DailyBriefingWorkflow:
    @workflow.run
    async def run(self) -> BriefingResult:
        # Single entry point per workflow
        pass
```

### Activities Grouped by Domain
```python
# activities/google_activities.py
# ✅ CORRECT - All imports at top of file
from temporalio import activity
from the_assistant.integrations.google_client import GoogleClient
from the_assistant.models.calendar import CalendarEvent, DateRange

@activity.defn
async def get_calendar_events(date_range: DateRange) -> list[CalendarEvent]:
    pass

@activity.defn
async def create_calendar_event(event: CalendarEvent) -> str:
    pass
```

### Integration Clients as Classes
```python
# integrations/google_client.py
# ✅ CORRECT - All imports at top of file
from typing import Optional
from google.oauth2.credentials import Credentials
from the_assistant.models.calendar import CalendarEvent, DateRange
from the_assistant.models.google import GoogleCredentials

class GoogleClient:
    def __init__(self, credentials: GoogleCredentials):
        self.credentials = credentials
    
    async def get_events(self, date_range: DateRange) -> list[CalendarEvent]:
        # Return Pydantic models, not raw JSON
        pass
```

## Testing Structure
```
tests/
├── unit/                    # Mock external dependencies
│   ├── test_activities.py   # Test individual activities
│   └── integrations/        # Test client logic
├── integration/             # Real services, test data only
│   ├── test_workflows.py    # End-to-end workflow testing
│   └── test_google_integration.py # Real API integration
└── conftest.py             # Shared test fixtures
```