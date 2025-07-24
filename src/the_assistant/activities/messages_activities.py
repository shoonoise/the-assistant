from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from temporalio import activity


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
        prompt="You need to build a morning brief message for user, this is data: {data}",
        data=input.data,
    )
    return await agent.run(task)
