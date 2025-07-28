"""Activities for interacting with TickTick tasks."""

from dataclasses import dataclass
from datetime import date

from temporalio import activity

from the_assistant.integrations.ticktick import TickTickClient
from the_assistant.models.ticktick import TickTask


@dataclass
class GetTasksForDateInput:
    user_id: int
    day: date


@dataclass
class GetUpcomingTasksInput:
    user_id: int
    days: int = 7


@activity.defn
async def get_tasks_for_date(input: GetTasksForDateInput) -> list[TickTask]:
    client = TickTickClient()
    return await client.get_tasks_for_date(input.day)


@activity.defn
async def get_tasks_next_days(input: GetUpcomingTasksInput) -> list[TickTask]:
    client = TickTickClient()
    return await client.get_tasks_ahead(input.days)
