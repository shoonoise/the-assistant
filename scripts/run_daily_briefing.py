#!/usr/bin/env python3
"""
Script to trigger the daily briefing workflow.
"""

import asyncio
import logging
import os

import dotenv
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from the_assistant.workflows.daily_briefing import DailyBriefing

# Load environment variables
dotenv.load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def trigger_daily_briefing():
    """Trigger the daily briefing workflow."""
    try:
        # Connect to Temporal with Pydantic V2 converter
        temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
        logger.info(f"Connecting to Temporal server at {temporal_host}")
        client = await Client.connect(
            temporal_host,
            data_converter=pydantic_data_converter,
        )
        logger.info("Connected to Temporal server")

        # Start the workflow
        task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "the-assistant")
        logger.info(f"Starting DailyBriefing workflow on task queue: {task_queue}")
        
        handle = await client.start_workflow(
            DailyBriefing.run,
            1,  # user_id=1 as default
            id="daily-briefing-" + str(int(asyncio.get_event_loop().time())),
            task_queue=task_queue,
        )
        
        logger.info(f"Workflow started with ID: {handle.id}")
        
        # Wait for completion
        result = await handle.result()
        logger.info(f"Workflow completed successfully: {result}")
        
    except Exception as e:
        logger.error(f"Failed to trigger daily briefing: {e}")
        raise


def main():
    """Main entry point."""
    logger.info("Triggering Daily Briefing Workflow")
    asyncio.run(trigger_daily_briefing())


if __name__ == "__main__":
    main() 