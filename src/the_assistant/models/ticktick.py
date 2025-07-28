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
    def from_ticktask(cls, task: object) -> "TickTask":
        if isinstance(task, dict):
            get = task.get
            list_obj = task.get("list") or {}
        else:

            def get(k: str, d=None):
                return getattr(task, k, d)

            list_obj = getattr(task, "list", None) or {}
        return cls(
            id=get("id", ""),
            title=get("title", ""),
            due_date=get("dueDate"),
            start_date=get("startDate"),
            completed=get("is_completed", False) or get("status", 0) > 0,
            project=getattr(list_obj, "name", None)
            if not isinstance(list_obj, dict)
            else list_obj.get("name"),
            tags=list(get("tags", [])),
        )
