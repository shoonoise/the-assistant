#!/usr/bin/env python3
"""
Simplified Temporal worker for The Assistant.

This module starts a basic Temporal worker that only registers activities.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

# Import activities from new organization
from the_assistant.activities.google_activities import (
    get_calendar_events,
    get_emails,
    get_events_by_date,
    get_today_events,
    get_upcoming_events,
)
from the_assistant.activities.messages_activities import (
    build_briefing_summary,
    build_daily_briefing,
)
from the_assistant.activities.obsidian_activities import (
    scan_vault_notes,
)
from the_assistant.activities.telegram_activities import (
    send_message,
)
from the_assistant.activities.weather_activities import get_weather_forecast
from the_assistant.workflows.daily_briefing import DailyBriefing

from .settings import get_settings

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Start the simplified Temporal worker."""
    try:
        settings = get_settings()
        logging.basicConfig(
            level=getattr(logging, settings.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        # Connect to Temporal with Pydantic V2 converter
        temporal_host = settings.temporal_host
        logger.info(f"Connecting to Temporal server at {temporal_host}")
        client = await Client.connect(
            temporal_host,
            data_converter=pydantic_data_converter,
        )
        logger.info("Connected to Temporal server")

        # Create worker with only activities (no workflows)
        task_queue = settings.temporal_task_queue
        worker = Worker(
            client,
            task_queue=task_queue,
            activities=[
                # Google activities
                get_calendar_events,
                get_upcoming_events,
                get_events_by_date,
                get_today_events,
                get_emails,
                # Obsidian activities
                scan_vault_notes,
                # Weather activities
                get_weather_forecast,
                # Messages activities
                build_daily_briefing,
                build_briefing_summary,
                # Telegram activities
                send_message,
            ],
            workflows=[DailyBriefing],
        )

        logger.info(f"Starting Temporal worker on task queue: {task_queue}")
        logger.info("Worker started successfully. Press Ctrl+C to stop.")

        # Start worker
        await worker.run()

    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed: {e}")
        raise


def main():
    """Main entry point for the worker."""
    logger.info("Starting The Assistant Temporal Worker")
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
