"""Telegram client for The Assistant."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

from telegram import (
    Bot,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
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
    ConversationHandler,
    MessageHandler,
    filters,
)
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from the_assistant.db import get_user_service
from the_assistant.integrations.google.client import GoogleClient
from the_assistant.integrations.google.oauth_state import create_state_jwt
from the_assistant.settings import get_settings

from .constants import SETTINGS_LABEL_MAP, ConversationState, SettingKey

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
        self._extra_handlers: list[ConversationHandler] = []

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
        text: str,
        parse_mode: str = ParseMode.MARKDOWN,
        retry_count: int = 0,
    ) -> bool:
        """Send a text message to the user's chat.

        Args:
            text: The text message to send.
            parse_mode: The parse mode to use for the message.
            retry_count: The current retry count (used internally for retries).

        Returns:
            bool: True if the message was sent successfully, False otherwise.

        Raises:
            ValueError: If user_id is not set or user not found in database.
        """
        if self.user_id is None:
            raise ValueError("user_id must be set to send messages")

        user_service = get_user_service()
        user = await user_service.get_user_by_id(self.user_id)

        if not user or not user.telegram_chat_id:
            raise ValueError(
                f"User {self.user_id} not found or has no telegram_chat_id"
            )

        chat_id = user.telegram_chat_id

        try:
            await self.bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode
            )
            logger.info(f"Message sent to user {self.user_id} (chat {chat_id})")
            return True

        except Exception as e:
            should_retry = await self._handle_message_error(e, chat_id, retry_count)
            if should_retry:
                return await self.send_message(text, parse_mode, retry_count + 1)
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

    async def register_handler(self, handler: ConversationHandler) -> None:
        """Register a generic Telegram handler."""

        self._extra_handlers.append(handler)
        logger.info("Registered additional handler")

    async def _handle_unknown_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle unknown commands.

        Args:
            update: The update object from Telegram.
            context: The context object from Telegram.
        """
        if not update.message or not update.effective_user:
            logger.warning("Received unknown command without message or effective_user")
            return

        # Extract the command from the message
        command = update.message.text.split()[0] if update.message.text else ""
        user_id = update.effective_user.id

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

        # Send the error message without markdown to avoid parsing issues
        await update.message.reply_text(error_message)

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

        # Register additional handlers such as conversations BEFORE unknown command handler
        for handler in self._extra_handlers:
            self.application.add_handler(handler)
            logger.info("Added additional handler")

        # Add handler for unknown commands (must be last to catch unhandled commands)
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
    if not update.message or not update.effective_user:
        logger.warning("Received start command without message or effective_user")
        return

    user = update.effective_user
    user_service = get_user_service()

    existing = await user_service.get_user_by_telegram_chat_id(user.id)
    if existing is None:
        existing = await user_service.create_user(
            telegram_chat_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            registered_at=datetime.now(UTC),
        )
    else:
        existing = await user_service.update_user(
            existing.id,
            username=user.username or existing.username,
            first_name=user.first_name or existing.first_name,
            last_name=user.last_name or existing.last_name,
        )

    user_name = user.first_name or user.username or "there"
    welcome_message = (
        f"👋 Hello, {user_name}!\n\n"
        "Welcome to The Assistant Bot. I can help you stay informed about your "
        "upcoming events, tasks, and provide daily briefings.\n\n"
        "Here are some things I can do:\n"
        "• Send notifications about upcoming trips\n"
        "• Provide morning briefings with your schedule and tasks\n"
        "• Respond to your commands for on-demand information\n\n"
        f"✅ You've been registered with ID: `{user.id}`\n\n"
        "Use /help to see all available commands or /settings to manage your preferences."
    )

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Registered and sent welcome message to user {user.id}")


async def handle_help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /help command.

    This command provides a list of available commands and their descriptions.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    if not update.message or not update.effective_user:
        logger.warning("Received help command without message or effective_user")
        return

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

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Sent help message to user {update.effective_user.id}")


async def handle_briefing_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /briefing command.

    This command generates and sends an on-demand briefing to the user.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    if not update.message or not update.effective_user or not update.effective_chat:
        logger.warning(
            "Received briefing command without message, effective_user, or effective_chat"
        )
        return

    telegram_user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    logger.debug(f"Briefing requested in chat {chat_id}")

    # Send an acknowledgment message
    await update.message.reply_text(
        "🔄 Generating your briefing... This may take a moment."
    )
    logger.info(f"Received briefing request from telegram user {telegram_user_id}")

    try:
        # Get the user from the database
        user_service = get_user_service()
        user = await user_service.get_user_by_telegram_chat_id(telegram_user_id)

        if not user:
            await update.message.reply_text(
                "❌ You need to register first. Please use /start to register."
            )
            logger.warning(
                f"Unregistered user {telegram_user_id} tried to use /briefing"
            )
            return

        settings = get_settings()

        # Connect to Temporal with Pydantic V2 converter
        logger.info(f"Connecting to Temporal server at {settings.temporal_host}")
        client = await Client.connect(
            settings.temporal_host,
            data_converter=pydantic_data_converter,
            namespace=settings.temporal_namespace,
        )
        logger.info("Connected to Temporal server")

        # TODO: refactor
        from the_assistant.workflows.daily_briefing import DailyBriefing

        # Start the workflow
        logger.info(f"Starting DailyBriefing workflow for user {user.id}")

        workflow_id = f"briefing-{user.id}-{int(time.time())}"

        handle = await client.start_workflow(
            DailyBriefing.run,
            user.id,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        logger.info(f"Workflow started with ID: {handle.id} for user {user.id}")

        # Send confirmation that the workflow was started
        await update.message.reply_text(
            "✅ Your briefing is being generated and will be delivered shortly!"
        )

        logger.info(f"Successfully started briefing workflow for user {user.id}")

    except Exception as e:
        error_message = "❌ Sorry, I encountered an error while generating your briefing. Please try again later."
        await update.message.reply_text(error_message)
        logger.error(
            f"Error generating briefing for telegram user {telegram_user_id}: {e}"
        )


async def handle_settings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /settings command.

    This command shows the user's current settings and allows them to modify preferences.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    if not update.message or not update.effective_user:
        logger.warning("Received settings command without message or effective_user")
        return

    user_id = update.effective_user.id
    user_service = get_user_service()

    user = await user_service.get_user_by_telegram_chat_id(user_id)
    if not user:
        user = await user_service.create_user(
            telegram_chat_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            last_name=update.effective_user.last_name,
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

    await update.message.reply_text(settings_message, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Sent settings to user {user_id}")


async def start_update_settings(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start the settings update conversation."""

    if not update.message:
        return ConversationHandler.END

    keyboard = [
        ["How to greet", "Briefing time"],
        ["About me", "Location"],
    ]
    await update.message.reply_text(
        "Please choose which setting you want to update:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return ConversationState.SELECT_SETTING


async def select_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's setting choice."""

    if not update.message:
        return ConversationHandler.END

    choice = update.message.text.strip()
    if choice not in SETTINGS_LABEL_MAP:
        await update.message.reply_text(
            "Use the buttons to pick one of the available options."
        )
        return ConversationState.SELECT_SETTING

    user_data = cast(dict[str, Any], context.user_data)
    user_data["setting_key"] = SETTINGS_LABEL_MAP[choice]
    user_data["setting_label"] = choice
    await update.message.reply_text(
        f"Enter the new value for '{choice}':",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationState.ENTER_VALUE


async def save_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the provided setting value."""

    if not update.message or not update.effective_user:
        return ConversationHandler.END

    value = update.message.text.strip()
    user_data = cast(dict[str, Any], context.user_data)
    setting_key = cast(SettingKey | None, user_data.get("setting_key"))
    setting_label = cast(str | None, user_data.get("setting_label")) or setting_key

    if setting_key is None:
        return ConversationHandler.END

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        raise ValueError("User not registered")

    if setting_key is SettingKey.GREET and not value:
        value = "first_name"

    await user_service.set_setting(user.id, setting_key.value, value)

    await update.message.reply_text(
        f"{setting_label} updated to: {value}", reply_markup=ReplyKeyboardRemove()
    )

    user_data.pop("setting_key", None)
    user_data.pop("setting_label", None)

    return ConversationHandler.END


async def cancel_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the settings update conversation."""

    if update.message:
        await update.message.reply_text(
            "Settings update cancelled.", reply_markup=ReplyKeyboardRemove()
        )
    user_data = cast(dict[str, Any], context.user_data)
    user_data.pop("setting_key", None)
    user_data.pop("setting_label", None)
    return ConversationHandler.END


async def handle_google_auth_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /google_auth command.

    Sends the user a Google OAuth authorization link if they are not yet
    authenticated. When the OAuth flow completes the user will receive a
    confirmation message.
    """
    if not update.message:
        logger.warning("Received google_auth command without message")
        return

    chat_user = update.effective_user
    if not chat_user:
        logger.warning("Received google_auth command without effective_user")
        return

    user_service = get_user_service()

    user = await user_service.get_user_by_telegram_chat_id(chat_user.id)
    if not user:
        raise ValueError("User not registered")

    client = GoogleClient(user.id)
    if await client.is_authenticated():
        await update.message.reply_text(
            "✅ You are already authenticated with Google.",
        )
        return

    settings = get_settings()
    state = create_state_jwt(user.id, settings)
    auth_url = await client.generate_auth_url(state)

    message = (
        f"Please [authorize access]({auth_url}) to your Google account. "
        "You'll receive a confirmation once completed."
    )
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Sent Google auth link to user {chat_user.id}")


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
    await client.register_command_handler("google_auth", handle_google_auth_command)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("update_settings", start_update_settings)],
        states={
            ConversationState.SELECT_SETTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_setting)
            ],
            ConversationState.ENTER_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_setting)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_update)],
    )

    await client.register_handler(conv_handler)

    return client
