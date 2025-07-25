from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from datetime import UTC

    from the_assistant.activities.google_activities import (
        GetImportantEmailsAccountsInput,
        GetUpcomingEventsAccountsInput,
        get_important_emails_accounts,
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

        events = await workflow.execute_activity(
            get_upcoming_events_accounts,
            GetUpcomingEventsAccountsInput(
                user_id=user_id, days_ahead=7, accounts=accounts
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )

        email_data = await workflow.execute_activity(
            get_important_emails_accounts,
            GetImportantEmailsAccountsInput(
                user_id=user_id, max_full=10, max_snippets=10, accounts=accounts
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )

        weather = await workflow.execute_activity(
            get_weather_forecast,
            GetWeatherForecastInput(user_id=user_id),
            start_to_close_timeout=timedelta(seconds=10),
        )

        settings = await workflow.execute_activity(
            get_user_settings,
            GetUserSettingsInput(user_id=user_id),
            start_to_close_timeout=timedelta(seconds=10),
        )

        prompt = await workflow.execute_activity(
            build_briefing_prompt,
            BriefingPromptInput(
                events=events,
                emails_full=email_data.emails_full,
                emails_snippets=email_data.emails_snippets,
                email_total=email_data.total,
                weather=weather[0] if weather else None,
                settings=settings,
                current_time=workflow.now().astimezone(UTC).isoformat(),
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )
        briefing_sammary = await workflow.execute_activity(
            build_briefing_summary,
            BriefingSummaryInput(user_id=user_id, data=prompt),
            start_to_close_timeout=timedelta(seconds=60),
        )

        await workflow.execute_activity(
            send_message,
            SendMessageInput(user_id=user_id, text=briefing_sammary),
            start_to_close_timeout=timedelta(seconds=10),
        )
