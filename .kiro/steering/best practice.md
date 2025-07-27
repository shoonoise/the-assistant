---
inclusion: always
---

# DEVELOPMENT PRINCIPLES

## Code Quality (NON-NEGOTIABLE)

### Function Signatures & Import Rules
```python
# ✅ CORRECT - Imports at top, type hints required
from datetime import datetime
from the_assistant.models.calendar import CalendarEvent, ProcessResult

async def process_events(events: list[CalendarEvent]) -> ProcessResult:
    """Process calendar events and return summary."""
    pass

# ❌ WRONG - Missing type hints AND imports inside function
async def process_events(events):
    from datetime import datetime  # Never import inside functions!
    pass
```

### Import Organization (ALWAYS AT TOP OF FILE)
```python
# ✅ CORRECT - All imports at the very top
# Standard library
from datetime import datetime, timedelta
from pathlib import Path

# Third-party
from pydantic import BaseModel
from temporalio import workflow

# Local modules
from the_assistant.integrations.google_client import GoogleClient
from the_assistant.models.calendar import CalendarEvent

# ❌ WRONG - Never import inside functions or classes
def some_function():
    from datetime import datetime  # This breaks PEP 8
    pass
```

### Error Handling Strategy
```python
# ✅ CORRECT - All imports at top of file
from temporalio import activity
from the_assistant.integrations.google_client import GoogleClient, AuthenticationError, RateLimitError
from the_assistant.models.calendar import CalendarEvent, DateRange

@activity.defn
async def get_calendar_events(date_range: DateRange) -> list[CalendarEvent]:
    """Activities must be idempotent and handle retries gracefully."""
    try:
        client = GoogleClient()
        return await client.get_events(date_range)
    except AuthenticationError:
        # Fail fast on config errors - don't retry
        raise
    except RateLimitError:
        # Let Temporal handle retries with exponential backoff
        raise
```

## Testing Strategy (COMPREHENSIVE)

### Unit Tests - Mock Everything External
```python
# ✅ CORRECT - All imports at top, including test imports
from unittest.mock import patch

import pytest

from the_assistant.activities.google_activities import get_calendar_events
from the_assistant.models.calendar import CalendarEvent

@pytest.mark.asyncio
async def test_process_calendar_events():
    with patch('the_assistant.integrations.google_client.GoogleClient') as mock_client:
        mock_client.return_value.get_events.return_value = [mock_event]
        
        result = await get_calendar_events(date_range)
        
        assert len(result) == 1
        assert isinstance(result[0], CalendarEvent)
```

### Integration Tests - Real Services, Test Data Only
```python
# ✅ CORRECT - All imports at top
import pytest

from the_assistant.integrations.google_client import GoogleClient
from the_assistant.models.calendar import CalendarEvent

@pytest.mark.integration
async def test_google_calendar_integration():
    """Test with real Google API using test calendar."""
    client = GoogleClient(test_credentials)
    events = await client.get_events(test_date_range)
    assert all(isinstance(event, CalendarEvent) for event in events)
```

## Development Workflow (EFFICIENT)

### Quick Development Cycle
```bash
# Format, lint, test in one command
make fix && make ci

# Start development environment
docker-compose up -d && make serve

# Restart after changes
docker-compose build && docker-compose up -d
```

### Debugging Workflow Failures
```python
# ✅ CORRECT - Import logger at top of file
import logging
from temporalio import workflow

logger = logging.getLogger(__name__)

# Then use in functions
def log_workflow_progress(events, date_range):
    logger.info(
        "Processing calendar events",
        extra={
            "workflow_id": workflow.info().workflow_id,
            "event_count": len(events),
            "date_range": str(date_range)
        }
    )
```