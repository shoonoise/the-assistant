import asyncio
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

NO_RETRY = RetryPolicy(maximum_attempts=1)

with workflow.unsafe.imports_passed_through():
    from the_assistant.activities.google_activities import (
        GetEmailsInput,
        GetUpcomingEventsAccountsInput,
        get_emails,
        get_upcoming_events_accounts,
    )
    from the_assistant.activities.messages_activities import (
        BriefingPromptInput,
        BriefingSummaryInput,
        GetUserSettingsInput,
        build_briefing_prompt,
        build_briefing_summary,
        get_user_settings,
    )
    from the_assistant.activities.telegram_activities import (
        SendMessageInput,
        send_message,
    )
    from the_assistant.activities.weather_activities import (
        GetWeatherForecastInput,
        get_weather_forecast,
    )


@workflow.defn
class DailyBriefing:
    @workflow.run
    async def run(self, user_id: int) -> None:
        accounts = ["personal", "work"]

        settings = await workflow.execute_activity(
            get_user_settings,
            GetUserSettingsInput(user_id=user_id),
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=NO_RETRY,
        )

        events = await workflow.execute_activity(
            get_upcoming_events_accounts,
            GetUpcomingEventsAccountsInput(
                user_id=user_id, days_ahead=7, accounts=accounts
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=NO_RETRY,
        )

        email_tasks = [
            workflow.execute_activity(
                get_emails,
                GetEmailsInput(
                    user_id=user_id,
                    account=account,
                    max_results=35,
                    query="in:inbox",
                    include_body=True,
                    ignored_senders=settings.get("ignore_emails") if settings else None,
                    unread_only=None,
                    sender=None,
                ),
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=NO_RETRY,
            )
            for account in accounts
        ]
        email_lists = await asyncio.gather(*email_tasks)
        emails = [e for sub in email_lists for e in sub]

        weather = await workflow.execute_activity(
            get_weather_forecast,
            GetWeatherForecastInput(user_id=user_id),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=NO_RETRY,
        )

        prompt = await workflow.execute_activity(
            build_briefing_prompt,
            BriefingPromptInput(
                events=events,
                emails=emails,
                max_full=15,
                max_snippets=20,
                weather=weather[0] if weather else None,
                settings=settings,
                current_time=workflow.now().strftime("%Y-%m-%d %A %H:%M"),
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=NO_RETRY,
        )

        briefing_sammary = await workflow.execute_activity(
            build_briefing_summary,
            BriefingSummaryInput(user_id=user_id, data=prompt),
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=NO_RETRY,
        )

        await workflow.execute_activity(
            send_message,
            SendMessageInput(user_id=user_id, text=briefing_sammary),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=NO_RETRY,
        )
