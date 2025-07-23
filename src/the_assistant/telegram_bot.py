#!/usr/bin/env python3
"""
Telegram Bot service for The Assistant.

This module starts the Telegram bot in polling mode to handle user commands.
"""

import asyncio
import logging

from the_assistant.integrations.telegram.telegram_client import create_telegram_client

from .settings import get_settings

logger = logging.getLogger(__name__)


async def run_telegram_bot() -> None:
    """Start the Telegram bot in polling mode."""
    try:
        client = await create_telegram_client()
        logger.info("Telegram client created successfully")

        # Set up command handlers (already done in create_telegram_client)
        await client.setup_command_handlers()
        logger.info("Command handlers set up successfully")

        # Start polling
        logger.info("Starting Telegram bot in polling mode")
        await client.start_polling()

    except KeyboardInterrupt:
        logger.info("Telegram bot stopped by user")
        if "client" in locals():
            await client.stop_polling()
    except Exception as e:
        logger.error(f"Telegram bot failed: {e}")
        raise


def main():
    """Main entry point for the Telegram bot."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting The Assistant Telegram Bot")
    asyncio.run(run_telegram_bot())


if __name__ == "__main__":
    main()
