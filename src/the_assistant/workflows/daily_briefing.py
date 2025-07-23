from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from the_assistant.activities.google_activities import (
        GetTodayEventsInput,
        get_today_events,
    )
    from the_assistant.activities.messages_activities import (
        DailyBriefingInput,
        build_daily_briefing,
    )
    from the_assistant.activities.obsidian_activities import (
        ScanVaultNotesInput,
        scan_vault_notes,
    )
    from the_assistant.activities.telegram_activities import (
        SendMessageInput,
        send_message,
    )
    from the_assistant.models.obsidian import NoteFilters


@workflow.defn
class DailyBriefing:
    @workflow.run
    async def run(self, user_id: int) -> None:
        trip_notes = await workflow.execute_activity(
            scan_vault_notes,
            ScanVaultNotesInput(user_id=user_id, filters=NoteFilters(tags=["trip"])),
            start_to_close_timeout=timedelta(seconds=10),
        )

        events = await workflow.execute_activity(
            get_today_events,
            GetTodayEventsInput(user_id=user_id),
            start_to_close_timeout=timedelta(seconds=10),
        )

        briefing = await workflow.execute_activity(
            build_daily_briefing,
            DailyBriefingInput(user_id=user_id, trip_notes=trip_notes, events=events),
            start_to_close_timeout=timedelta(seconds=10),
        )

        chat_id = user_id  # TODO: should fetch chat ID per user

        await workflow.execute_activity(
            send_message,
            SendMessageInput(
                user_id=user_id,
                chat_id=chat_id,
                text=briefing,
            ),
            start_to_close_timeout=timedelta(seconds=10),
        )
