from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from temporalio import activity

from the_assistant.db import get_user_service
from the_assistant.integrations.llm import LLMAgent, Task
from the_assistant.models.google import CalendarEvent, GmailMessage
from the_assistant.models.weather import WeatherForecast

logger = activity.logger


@dataclass
class DailyBriefingInput:
    user_id: int
    today_events: list[CalendarEvent]
    tomorrow_events: list[CalendarEvent]
    weather: WeatherForecast | None = None
    emails: list[GmailMessage] | None = None


@dataclass
class BriefingPromptInput:
    events: list[CalendarEvent]
    emails_full: list[GmailMessage]
    emails_snippets: list[GmailMessage]
    email_total: int
    weather: WeatherForecast | None
    settings: dict[str, Any]
    current_time: str


@dataclass
class GetUserSettingsInput:
    user_id: int


@activity.defn
async def build_daily_briefing(input: DailyBriefingInput) -> str:
    """Build a daily briefing message from various data blocks."""

    def render_events(title: str, events: Iterable[CalendarEvent]) -> str:
        if not events:
            return ""
        lines = "\n".join(f"- {event.summary}" for event in events)
        return f"## {title}\n{lines}"

    blocks: list[str] = []

    if input.weather:
        w = input.weather
        blocks.append(
            f"## Weather\n{w.location}: {w.condition}, high {w.temperature_max}°C low {w.temperature_min}°C"
        )

    blocks.append(render_events("Today's Events", input.today_events))
    blocks.append(render_events("Tomorrow's Events", input.tomorrow_events))

    if input.emails:
        email_lines = "\n".join(
            f"- {email.subject or email.snippet}" for email in input.emails
        )
        blocks.append(f"## Unread Emails\n{email_lines}")

    # Filter out empty blocks
    content = "\n\n".join(block for block in blocks if block)

    template = (
        f"Here's your daily briefing for {date.today().strftime('%B %d, %Y')}"
        f"\n\n{content}"
    )

    logger.info(f"Built daily briefing message: {template}\nlenght: {len(template)}")

    return template[:4000]


@dataclass
class BriefingSummaryInput:
    """Input for building LLM-based morning briefing summary."""

    user_id: int
    data: str


@activity.defn
async def build_briefing_summary(input: BriefingSummaryInput) -> str:
    """Use the LLM agent to create a morning briefing summary."""

    agent = LLMAgent()
    task = Task(
        prompt=(
            "Using the provided context, write a concise daily briefing. "
            "Summarize calendar events highlighting those that may require preparation, "
            "summarize the emails generally but give individual short summaries for anything that looks important, "
            "translate and summarize any French emails, and include the weather if available. Context: {data}"
        ),
        data=input.data,
    )
    return await agent.run(task)


@activity.defn
async def get_user_settings(input: GetUserSettingsInput) -> dict[str, Any]:
    """Return all settings for the given user."""
    service = get_user_service()
    return await service.get_all_settings(input.user_id)


@activity.defn
async def build_briefing_prompt(input: BriefingPromptInput) -> str:
    """Render context data into a prompt string for the LLM."""

    lines: list[str] = [f"Current time: {input.current_time}"]

    if input.weather:
        w = input.weather
        lines.append(
            f"Weather for {w.location}: {w.condition}, high {w.temperature_max}°C low {w.temperature_min}°C"
        )

    if input.events:
        ev_lines = []
        for e in input.events:
            start = e.start_time.strftime("%Y-%m-%d %H:%M")
            ev_lines.append(
                f"- {e.summary} ({start}) {e.location or ''} [{e.calendar_id}]"
            )
        lines.append("Events next 7 days:\n" + "\n".join(ev_lines))

    if input.emails_full or input.emails_snippets:
        email_lines = []
        for e in input.emails_full:
            email_lines.append(
                f"- {e.subject} from {e.sender} unread:{e.is_unread}\n{e.body}"
            )
        if input.emails_snippets:
            email_lines.append("Snippets:")
            for e in input.emails_snippets:
                email_lines.append(
                    f"- {e.subject} from {e.sender} unread:{e.is_unread} snippet:{e.snippet}"
                )
        lines.append(
            f"Important emails (total inbox: {input.email_total}):\n"
            + "\n".join(email_lines)
        )

    if input.settings:
        set_lines = "\n".join(f"- {k}: {v}" for k, v in input.settings.items())
        lines.append("User settings:\n" + set_lines)

    return "\n\n".join(lines)
