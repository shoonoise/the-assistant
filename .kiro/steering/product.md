---
inclusion: always
---

# PROJECT CONTEXT & PATTERNS

## What We're Building
Personal workflow automation using **Temporal orchestration** with Google Calendar, Obsidian, and Telegram integrations.

## Implementation Philosophy (CRITICAL MINDSET)

### Build Minimal, Iterate Fast
- ✅ Simple working solution → Test → Improve
- ❌ Complex architecture → Over-engineering → Never ships
- Implement ONLY current requirements, not future speculation
- Refactor when patterns emerge naturally

### Human-in-the-Loop Design
```python
# Use Telegram for confirmations in workflows
await workflow.execute_activity(
    send_telegram_confirmation,
    "Process 5 calendar events?",
    start_to_close_timeout=timedelta(hours=1)  # Wait for human response
)
```

## Domain-Specific Patterns

### Obsidian Integration
```python
# Tag-based filtering for notes
notes = await obsidian_client.get_notes_by_tags(["#trip", "#work"])

# Always backup before modifications
await obsidian_client.backup_note(note_path)
await obsidian_client.update_note(note_path, new_content)
```

### Google Calendar Integration
```python
# Return structured data, not raw JSON
@activity.defn
async def get_calendar_events(date_range: DateRange) -> list[CalendarEvent]:
    client = GoogleClient()
    return await client.get_events(date_range)  # Returns Pydantic models
```
