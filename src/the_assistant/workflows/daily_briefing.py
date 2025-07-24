from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from datetime import UTC

    from the_assistant.activities.google_activities import (
        GetEmailsInput,
        GetEventsByDateInput,
        GetTodayEventsInput,
        get_emails,
        get_events_by_date,
        get_today_events,
    )
    from the_assistant.activities.messages_activities import (
        BriefingSummaryInput,
        DailyBriefingInput,
        build_briefing_summary,
        build_daily_briefing,
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
        today_events = await workflow.execute_activity(
            get_today_events,
            GetTodayEventsInput(user_id=user_id),
            start_to_close_timeout=timedelta(seconds=10),
        )

        tomorrow = workflow.now().astimezone(UTC) + timedelta(days=1)
        tomorrow_events = await workflow.execute_activity(
            get_events_by_date,
            GetEventsByDateInput(user_id=user_id, target_date=tomorrow),
            start_to_close_timeout=timedelta(seconds=10),
        )

        weather = await workflow.execute_activity(
            get_weather_forecast,
            GetWeatherForecastInput(user_id=user_id),
            start_to_close_timeout=timedelta(seconds=10),
        )

        emails = await workflow.execute_activity(
            get_emails,
            GetEmailsInput(user_id=user_id, unread_only=True, max_results=5),
            start_to_close_timeout=timedelta(seconds=10),
        )

        briefing = await workflow.execute_activity(
            build_daily_briefing,
            DailyBriefingInput(
                user_id=user_id,
                today_events=today_events,
                tomorrow_events=tomorrow_events,
                weather=weather[0] if weather else None,
                emails=emails,
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )

        briefing_sammary = await workflow.execute_activity(
            build_briefing_summary,
            BriefingSummaryInput(user_id=user_id, data=briefing),
            start_to_close_timeout=timedelta(30),
        )

        await workflow.execute_activity(
            send_message,
            SendMessageInput(user_id=user_id, text=briefing_sammary),
            start_to_close_timeout=timedelta(seconds=10),
        )
