from datetime import UTC, datetime, timedelta

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
    is_all_day: bool = Field(default=False, description="Task spans the entire day")
    project_id: str | None = Field(default=None, description="Project identifier")
    repeat_flag: bool = Field(default=False, description="Task has a repeat rule")
    priority: int | None = Field(default=None, description="Priority level")

    @classmethod
    def from_ticktask(cls, task: dict[str, Any]) -> "TickTask":
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
                "is_all_day": bool(task.get("isAllDay")),
                "project_id": task.get("projectId"),
                "repeat_flag": bool(task.get("repeatFlag")),
                "priority": task.get("priority"),
            }
        )


class TickToken(BaseAssistantModel):
    """OAuth2 token for TickTick API."""

    access_token: str = Field(description="Access token")
    refresh_token: str | None = Field(default=None, description="Refresh token")
    expires_at: datetime | None = Field(
        default=None, description="Access token expiration time"
    )
    token_type: str = Field(default="Bearer", description="Token type")

    @classmethod
    def from_token_response(cls, data: dict[str, Any]) -> "TickToken":
        """Create :class:`TickToken` from token endpoint response."""
        expires_in = int(data.get("expires_in", 0))
        expires_at = (
            datetime.now(UTC) + timedelta(seconds=expires_in) if expires_in else None
        )
        return cls(
            access_token=str(data["access_token"]),
            refresh_token=data.get("refresh_token"),
            expires_at=expires_at,
            token_type=str(data.get("token_type", "Bearer")),
        )

    @property
    def is_expired(self) -> bool:
        """Return ``True`` if the token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) >= self.expires_at
