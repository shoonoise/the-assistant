"""Telegram client for The Assistant."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.error import (
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
    TimedOut,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from the_assistant.db import get_user_service
from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


class TelegramClient:
    """Client for interacting with the Telegram Bot API."""

    def __init__(self, user_id: int | None = None):
        """Initialize the Telegram client.

        Args:
            user_id: The user ID for user-specific operations.

        Raises:
            ValueError: If the bot token is not configured.
        """
        token = get_settings().telegram_token
        if not token:
            raise ValueError("Telegram bot token cannot be empty")

        self.token = token
        self.user_id = user_id
        self.bot = Bot(token=token)
        self.application: Application | None = None
        self._command_handlers: dict[
            str, Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
        ] = {}

        logger.info(f"Telegram client initialized for user_id: {user_id}")

    async def validate_credentials(self) -> bool:
        """Validate the bot token by getting the bot info.

        Returns:
            bool: True if the token is valid, False otherwise.
        """
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Bot validation successful: @{bot_info.username}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to validate bot token: {e}")
            return False

    async def _respect_rate_limit(self, e: Exception) -> bool:
        """Handle rate limiting from the Telegram API.

        Args:
            e: The exception that occurred.

        Returns:
            bool: True if rate limiting was handled, False otherwise.
        """
        if isinstance(e, RetryAfter):
            wait_time = e.retry_after
            # Convert timedelta to seconds if needed
            if hasattr(wait_time, "total_seconds") and callable(
                wait_time.total_seconds
            ):
                wait_seconds = float(wait_time.total_seconds())
            else:
                wait_seconds = float(wait_time)
            logger.warning(
                f"Rate limited by Telegram API. Waiting for {wait_seconds} seconds"
            )
            await asyncio.sleep(wait_seconds)
            return True
        return False

    async def _handle_message_error(
        self, e: Exception, chat_id: int, retry_count: int = 0
    ) -> bool:
        """Handle errors that occur when sending messages.

        Args:
            e: The exception that occurred.
            chat_id: The chat ID where the message was being sent.
            retry_count: The current retry count.

        Returns:
            bool: True if the error was handled and the operation should be retried,
                False if the error is terminal.
        """
        max_retries = 3

        # First check for rate limiting
        if await self._respect_rate_limit(e):
            return True

        # Check for specific error types first (more specific before general)
        if isinstance(e, BadRequest):
            logger.error(f"Bad request when sending message to {chat_id}: {e}")
            return False

        elif isinstance(e, Forbidden):
            logger.error(
                f"Bot was blocked by user {chat_id} or doesn't have permission: {e}"
            )
            return False

        elif isinstance(e, NetworkError) or isinstance(e, TimedOut):
            if retry_count < max_retries:
                wait_time = 2**retry_count  # Exponential backoff
                logger.warning(
                    f"Network error when sending message to {chat_id}. "
                    f"Retrying in {wait_time} seconds. Error: {e}"
                )
                await asyncio.sleep(wait_time)
                return True
            else:
                logger.error(
                    f"Failed to send message to {chat_id} after {max_retries} retries: {e}"
                )
                return False

        else:
            logger.error(f"Unexpected error when sending message to {chat_id}: {e}")
            return False

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = ParseMode.MARKDOWN,
        retry_count: int = 0,
    ) -> bool:
        """Send a text message to a specific chat.

        Args:
            chat_id: The chat ID to send the message to.
            text: The text message to send.
            parse_mode: The parse mode to use for the message.
            retry_count: The current retry count (used internally for retries).

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        try:
            await self.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode
            )
            logger.info(f"Message sent to {chat_id}")
            return True

        except Exception as e:
            should_retry = await self._handle_message_error(e, chat_id, retry_count)
            if should_retry:
                return await self.send_message(
                    chat_id, text, parse_mode, retry_count + 1
                )
            return False

    async def register_command_handler(
        self,
        command: str,
        handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
    ) -> None:
        """Register a command handler for the bot.

        Args:
            command: The command to handle (without the leading slash).
            handler: The async function that will handle the command.
        """
        self._command_handlers[command] = handler
        logger.info(f"Registered handler for command: /{command}")

    async def _handle_unknown_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle unknown commands.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.
        """
        # Extract the command from the message
        command = update.message.text.split()[0] if update.message.text else ""  # type: ignore
        user_id = update.effective_user.id  # type: ignore

        # Get available commands for suggestions
        available_commands = list(self._command_handlers.keys())

        # Create a helpful error message
        error_message = (
            f"❓ Sorry, I don't understand the command `{command}`.\n\n"
            f"Available commands:\n"
        )

        # Add each available command to the message
        for cmd in available_commands:
            error_message += f"• /{cmd}\n"

        error_message += "\nUse /help for more detailed information about each command."

        # Send the error message
        await update.message.reply_text(error_message, parse_mode=ParseMode.MARKDOWN)  # type: ignore

        # Log the unknown command
        logger.warning(f"User {user_id} sent unknown command: {command}")

    async def setup_command_handlers(self) -> None:
        """Set up command handlers for the bot.

        This method should be called after all command handlers have been registered
        and before starting the bot.
        """
        if self.application is not None:
            logger.warning("Command handlers are already set up")
            return

        # Create the application
        self.application = ApplicationBuilder().token(self.token).build()

        # Register all command handlers
        for command, handler in self._command_handlers.items():
            self.application.add_handler(CommandHandler(command, handler))
            logger.info(f"Added handler for command: /{command}")

        # Add handler for unknown commands
        self.application.add_handler(
            MessageHandler(
                filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
                self._handle_unknown_command,
            )
        )
        logger.info("Added handler for unknown commands")

    async def start_polling(self) -> None:
        """Start the bot in polling mode.

        This method should be called after setting up command handlers.
        """
        if self.application is None:
            await self.setup_command_handlers()

        logger.info("Starting bot in polling mode")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        await asyncio.Event().wait()

    async def stop_polling(self) -> None:
        """Stop the bot polling.

        This method should be called when shutting down the application.
        """
        if self.application is None:
            logger.warning("Bot is not running")
            return

        logger.info("Stopping bot")
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()


async def handle_start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /start command.

    This command welcomes the user and provides basic information about the bot.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    user = update.effective_user
    user_service = get_user_service()

    existing = await user_service.get_user_by_telegram_chat_id(user.id)  # type: ignore[arg-type]
    if existing is None:
        existing = await user_service.create_user(
            telegram_chat_id=user.id,  # type: ignore[arg-type]
            username=user.username,  # type: ignore[arg-type]
            first_name=user.first_name,  # type: ignore[arg-type]
            last_name=user.last_name,  # type: ignore[arg-type]
            registered_at=datetime.now(UTC),
        )
    else:
        existing = await user_service.update_user(
            existing.id,
            username=user.username or existing.username,  # type: ignore[arg-type]
            first_name=user.first_name or existing.first_name,  # type: ignore[arg-type]
            last_name=user.last_name or existing.last_name,  # type: ignore[arg-type]
        )

    user_name = user.first_name or user.username or "there"  # type: ignore
    welcome_message = (
        f"👋 Hello, {user_name}!\n\n"
        "Welcome to The Assistant Bot. I can help you stay informed about your "
        "upcoming events, tasks, and provide daily briefings.\n\n"
        "Here are some things I can do:\n"
        "• Send notifications about upcoming trips\n"
        "• Provide morning briefings with your schedule and tasks\n"
        "• Respond to your commands for on-demand information\n\n"
        f"✅ You've been registered with ID: `{user.id}`\n\n"  # type: ignore
        "Use /help to see all available commands or /settings to manage your preferences."
    )

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)  # type: ignore
    logger.info(f"Registered and sent welcome message to user {user.id}")  # type: ignore


async def handle_help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /help command.

    This command provides a list of available commands and their descriptions.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    help_message = (
        "📚 **Available Commands**\n\n"
        "/start - Start the bot and get a welcome message\n"
        "/help - Show this help message\n"
        "/briefing - Get an on-demand briefing of your day\n\n"
        "The bot will also send you automatic notifications for:\n"
        "• Morning briefings with your daily schedule\n"
        "• Reminders about upcoming trips\n"
        "• Important task deadlines\n\n"
        "If you have any issues or questions, please contact your system administrator."
    )

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)  # type: ignore
    logger.info(f"Sent help message to user {update.effective_user.id}")  # type: ignore


async def handle_briefing_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /briefing command.

    This command generates and sends an on-demand briefing to the user.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    user_id = update.effective_user.id  # type: ignore
    # Get chat_id for logging purposes
    chat_id = update.effective_chat.id  # type: ignore
    logger.debug(f"Briefing requested in chat {chat_id}")

    # Send an acknowledgment message
    await update.message.reply_text(  # type: ignore
        "🔄 Generating your briefing... This may take a moment."
    )
    logger.info(f"Received briefing request from user {user_id}")

    try:
        # For now, send a message explaining the briefing
        briefing_message = (
            "🌞 *Your Daily Briefing*\n\n"
            "This command would trigger the generation and delivery of your daily briefing.\n\n"
            "When fully integrated with the workflow system, it will include:\n"
            "• Your calendar events for today and tomorrow\n"
            "• Pending tasks from your Obsidian notes\n"
            "• Important reminders\n\n"
            "The briefing functionality has been implemented and is ready to be "
            "integrated with the workflow system."
        )

        await update.message.reply_text(briefing_message, parse_mode=ParseMode.MARKDOWN)  # type: ignore
        logger.info(f"Sent briefing explanation to user {user_id}")

    except Exception as e:
        error_message = "Sorry, I encountered an error while generating your briefing. Please try again later."
        await update.message.reply_text(error_message)  # type: ignore
        logger.error(f"Error generating briefing for user {user_id}: {e}")


async def handle_settings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /settings command.

    This command shows the user's current settings and allows them to modify preferences.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    user_id = update.effective_user.id  # type: ignore
    user_service = get_user_service()

    user = await user_service.get_user_by_telegram_chat_id(user_id)
    if not user:
        user = await user_service.create_user(
            telegram_chat_id=user_id,
            username=update.effective_user.username,  # type: ignore[arg-type]
            first_name=update.effective_user.first_name,  # type: ignore[arg-type]
            last_name=update.effective_user.last_name,  # type: ignore[arg-type]
            registered_at=datetime.now(UTC),
        )

    # Create settings message
    settings_message = (
        f"⚙️ **Your Settings**\n\n"
        f"**User ID:** `{user.id}`\n"
        f"**Name:** {user.first_name or 'Not set'}\n"
        f"**Username:** @{user.username or 'Not set'}\n"
        f"**Registered:** {user.registered_at or 'Unknown'}\n"
    )

    await update.message.reply_text(settings_message, parse_mode=ParseMode.MARKDOWN)  # type: ignore
    logger.info(f"Sent settings to user {user_id}")


async def create_telegram_client() -> TelegramClient:
    """Create a TelegramClient instance using environment variables.

    Args:
        user_id: The user ID for user-specific operations.

    Returns:
        TelegramClient: A configured TelegramClient instance.

    Raises:
        ValueError: If the required environment variables are not set.
    """
    client = TelegramClient()

    # Validate the credentials
    is_valid = await client.validate_credentials()
    if not is_valid:
        raise ValueError("Failed to validate Telegram bot credentials")

    # Register the default command handlers
    await client.register_command_handler("start", handle_start_command)
    await client.register_command_handler("help", handle_help_command)
    await client.register_command_handler("briefing", handle_briefing_command)
    await client.register_command_handler("settings", handle_settings_command)

    return client
