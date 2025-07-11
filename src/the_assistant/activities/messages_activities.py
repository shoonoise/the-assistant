from dataclasses import dataclass
from datetime import date

from temporalio import activity

from the_assistant.models.google import CalendarEvent
from the_assistant.models.obsidian import NoteList

logger = activity.logger


@dataclass
class DailyBriefingInput:
    user_id: int
    trip_notes: NoteList
    events: list[CalendarEvent]


@activity.defn
async def build_daily_briefing(
    input: DailyBriefingInput,
) -> str:
    """
    Activity to build a daily briefing message from trip notes and calendar events.
    """

    task_per_note = {note.title: note.pending_tasks for note in input.trip_notes}
    tasks_block = """
    ## Tasks
    There are some pending tasks related to your trips.

    """

    for note, tasks in task_per_note.items():
        tasks_block += f"""
        ### {note}
        """
        for task in tasks:
            tasks_block += f"        - [ ] {task.text}\n"

    events_block = f"""
    ## Events
    You have the following events scheduled for today:
    {"\n-".join([event.summary for event in input.events])}
    """

    template = f"""
    Here's your daily briefing for {date.today().strftime("%B %d, %Y")}.

    {events_block}

    {tasks_block}
    """

    logger.info(f"Built daily briefing message: {template}\nlenght: {len(template)}")

    return template[:4000]
