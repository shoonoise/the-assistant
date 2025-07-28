from datetime import datetime

from pydantic import Field

from .base import BaseAssistantModel


class TickTask(BaseAssistantModel):
    """Simple representation of a TickTick task."""

    id: str = Field(description="Task identifier")
    title: str = Field(description="Task title")
    due_date: datetime | None = Field(default=None, description="Due date")
    start_date: datetime | None = Field(default=None, description="Start date")
    completed: bool = Field(description="Task completion status")
    project: str | None = Field(default=None, description="List or project name")
    tags: list[str] = Field(default_factory=list, description="Task tags")

    @classmethod
    def from_ticktask(cls, task: dict[str, object]) -> "TickTask":
        """Create a TickTask from raw API data."""
        status = int(task.get("status", 0))
        list_info = task.get("list")
        return cls.model_validate(
            {
                "id": task["id"],
                "title": task["title"],
                "due_date": task.get("dueDate"),
                "start_date": task.get("startDate"),
                "completed": bool(task.get("is_completed") or status > 0),
                "project": list_info.get("name")
                if isinstance(list_info, dict)
                else None,
                "tags": task.get("tags", []),
            }
        )
