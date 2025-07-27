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

BRIEF_PROMPT = """
You are a thoughtful and friendly personal assistant writing a **daily briefing** for the USER, using given CONTEXT.
Consider time, day of the week (workday, weekend), time of the year.

Your tone should be natural, human, and warm — like a trusted assistant who knows the user's habits and priorities.
Keep it concise, engaging, and helpful. This is a friendly secretary message, not a formal report.
Reference dates in natural ways, e.g. "This Friday", "Tomorrow", "Yesterday", "Next week", "In 2 days"

**IMPORTANT**: Pay special attention to the USER PROFILE section - this contains crucial information about the user's preferences, habits, priorities, and personal context that should heavily influence your briefing style and content focus.

Use this structure:
- Start with a **short, warm greeting**, comment on the **day of the week and weather**.
- Mention anything important or unusual **happening today** if morning, **planned tomorrow** if evening. Plus **planned next week** if Sunday, **planned weekend** if Friday, etc.
- Prioritize what truly matters in **email summaries**:
  - Focus on emails with action items, personal relevance, or urgency.
  - Group minor items into a sentence or skip them entirely.
  - Translate and explain non-English/Russian emails in detail if any.
- Add light personal suggestions if helpful (“Might be worth prepping for Monday” or “Good day to catch up on that backlog.”)
- Never just list all events or emails. Use discretion.

Be brief, human, and helpful. Max response length: 4000 characters. Use markdown.
Use web search tool to find the most important and relevant news of the day.

<CONTEXT>{data}</CONTEXT>
"""


def _format_user_profile(settings: dict[str, Any]) -> str:
    """Format user settings into a comprehensive user profile for the LLM."""
    if not settings:
        return ""

    profile_sections = []

    # Personal preferences and habits
    personal_items = []
    work_items = []
    communication_items = []
    schedule_items = []
    other_items = []

    for key, value in settings.items():
        key_lower = key.lower()

        # Categorize settings based on key patterns
        if any(
            word in key_lower
            for word in ["prefer", "like", "favorite", "habit", "routine", "style"]
        ):
            personal_items.append(f"• {key}: {value}")
        elif any(
            word in key_lower
            for word in ["work", "job", "career", "office", "meeting", "project"]
        ):
            work_items.append(f"• {key}: {value}")
        elif any(
            word in key_lower
            for word in ["email", "message", "notification", "communication", "contact"]
        ):
            communication_items.append(f"• {key}: {value}")
        elif any(
            word in key_lower
            for word in ["schedule", "time", "calendar", "availability", "timezone"]
        ):
            schedule_items.append(f"• {key}: {value}")
        else:
            other_items.append(f"• {key}: {value}")

    # Build profile sections with meaningful headers
    if personal_items:
        profile_sections.append(
            "**Personal Preferences & Habits:**\n" + "\n".join(personal_items)
        )

    if work_items:
        profile_sections.append(
            "**Work & Professional Context:**\n" + "\n".join(work_items)
        )

    if communication_items:
        profile_sections.append(
            "**Communication Preferences:**\n" + "\n".join(communication_items)
        )

    if schedule_items:
        profile_sections.append(
            "**Schedule & Time Preferences:**\n" + "\n".join(schedule_items)
        )

    if other_items:
        profile_sections.append("**Additional Context:**\n" + "\n".join(other_items))

    if profile_sections:
        return "<USER_PROFILE>\n" + "\n\n".join(profile_sections) + "\n</USER_PROFILE>"

    return ""


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
    emails: list[GmailMessage]
    settings: dict[str, Any]
    current_time: str
    weather: WeatherForecast | None = None


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
        prompt=BRIEF_PROMPT,
        data=input.data,
    )
    return await agent.run(task, user_id=input.user_id)


@activity.defn
async def get_user_settings(input: GetUserSettingsInput) -> dict[str, Any]:
    """Return all settings for the given user."""
    service = get_user_service()
    return await service.get_all_settings(input.user_id)


@activity.defn
async def build_briefing_prompt(input: BriefingPromptInput) -> str:
    """Render context data into a prompt string for the LLM."""
    MAX_FULL = 10
    MAX_SNIPPETS = 10

    lines: list[str] = [f"<DATETIME>{input.current_time}</DATETIME>"]

    if input.weather:
        w = input.weather
        lines.append(
            f"<WEATHER>{w.condition}, high {w.temperature_max}°C low {w.temperature_min}°C at {w.location}</WEATHER>"
        )

    if input.events:
        ev_lines = []
        for e in input.events:
            start = e.start_time.strftime("%Y-%m-%d %H:%M")
            ev_lines.append(
                f"<EVENT><ACCOUNT>{e.account}</ACCOUNT><SUMMARY>{e.summary}</SUMMARY><START>{start}</START><LOCATION>{e.location}</LOCATION></EVENT>"
            )
        lines.append("<EVENTS>" + "\n".join(ev_lines) + "</EVENTS>")

    if input.emails:
        full_lines: list[str] = []
        snippet_lines: list[str] = []
        for idx, e in enumerate(input.emails):
            if idx < MAX_FULL:
                full_lines.append(
                    f"<EMAIL><ACCOUNT>{e.account}</ACCOUNT><SUBJECT>{e.subject}</SUBJECT><SENDER>{e.sender}</SENDER><UNREAD>{e.is_unread}</UNREAD><BODY>{e.body}</BODY></EMAIL>"
                )
            elif idx < MAX_FULL + MAX_SNIPPETS:
                snippet_lines.append(
                    f"<EMAIL><ACCOUNT>{e.account}</ACCOUNT><SUBJECT>{e.subject}</SUBJECT><SENDER>{e.sender}</SENDER><UNREAD>{e.is_unread}</UNREAD><SNIPPET>{e.snippet}</SNIPPET></EMAIL>"
                )
            else:
                break
        if full_lines:
            lines.append(
                f"Today emails (total {len(full_lines)}):\n<EMAILS>\n"
                + "\n".join(full_lines)
                + "\n</EMAILS>"
            )
        if snippet_lines:
            lines.append(
                "Snippets:\n<EMAIL_SNIPPETS>\n"
                + "\n".join(snippet_lines)
                + "\n</EMAIL_SNIPPETS>"
            )
        lines.append(f"Overall in the inbox: {len(input.emails)} emails")

    if input.settings:
        lines.append(_format_user_profile(input.settings))

    return "\n\n".join(lines)
