"""Telegram client for The Assistant."""

import asyncio
import html
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

from telegram import (
    Bot,
    BotCommand,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    BaseHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import escape_markdown
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from the_assistant.db import get_user_service
from the_assistant.integrations.google.client import GoogleClient
from the_assistant.integrations.google.oauth_state import create_state_jwt
from the_assistant.settings import get_settings

from .constants import (
    SETTINGS_LABEL_LOOKUP,
    ConversationState,
    SettingKey,
)
from .enhanced_handlers import MessageFormatter
from .persistent_keyboard import PersistentKeyboardManager
from .settings_interface import SettingsInterfaceManager

logger = logging.getLogger(__name__)


# Command registry with descriptions for help and autocompletion
COMMAND_REGISTRY: dict[str, str] = {
    "start": "Start the bot and get a welcome message",
    "help": "Show available commands and their descriptions",
    "briefing": "Get an on-demand briefing of your day",
    "settings": "View your current settings",
    "update_settings": "Update your preferences and settings",
    "google_auth": "Authenticate with Google services",
    "ignore_email": "Add an email pattern to ignore list",
    "list_ignored": "Show all ignored email patterns",
    "status": "Check bot status and integrations",
    "memory_add": "Remember a fact about you",
    "memory": "List your stored memories",
    "memory_delete": "Delete a memory by its id",
    "add_task": "Create a new scheduled task",
    "add_countdown": "Add a countdown event",
    "track_habit": "Track daily habits and routines (coming soon)",
}


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

    async def send_message(
        self,
        text: str,
        parse_mode: str = ParseMode.MARKDOWN,
    ) -> bool:
        """Send a text message to the user's chat.

        Args:
            text: The text message to send.
            parse_mode: The parse mode to use for the message.

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
            logger.error(f"Failed to send message to {chat_id}: {e}")
            raise

    async def register_command_handler(
        self,
        command: str,
        handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
        description: str | None = None,
    ) -> None:
        """Register a command handler for the bot.

        Args:
            command: The command to handle (without the leading slash).
            handler: The async function that will handle the command.
            description: Optional description for the command. If not provided,
                        will use the description from COMMAND_REGISTRY.
        """
        self._command_handlers[command] = handler

        # Update command registry with custom description if provided
        if description:
            COMMAND_REGISTRY[command] = description

        logger.info(f"Registered handler for command: /{command}")

    async def register_handler(self, handler: BaseHandler) -> None:
        """Register a generic Telegram handler."""

        self._extra_handlers.append(handler)
        logger.info("Registered additional handler")

    async def set_bot_commands(self) -> None:
        """Set bot commands for autocompletion in Telegram clients.

        This enables the command menu and autocompletion in Telegram clients.
        Commands are taken from the registered command handlers.
        """
        try:
            # Create BotCommand objects from all known commands
            commands = [
                BotCommand(
                    command=cmd,
                    description=COMMAND_REGISTRY.get(cmd, "No description"),
                )
                for cmd in COMMAND_REGISTRY.keys()
            ]

            # Set the commands with Telegram
            await self.bot.set_my_commands(commands)
            logger.info(f"Set {len(commands)} bot commands for autocompletion")

        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")

    async def update_command_description(self, command: str, description: str) -> None:
        """Update the description for a specific command.

        Args:
            command: The command name (without leading slash).
            description: The new description for the command.
        """
        COMMAND_REGISTRY[command] = description
        logger.info(f"Updated description for command /{command}")

        # Refresh bot commands if application is already set up
        if self.application is not None:
            await self.set_bot_commands()

    async def _handle_unknown_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle unknown commands with helpful suggestions.

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

        # Create a helpful error message with command descriptions
        error_message = (
            f"❓ Sorry, I don't understand the command <code>{html.escape(command)}</code>.\n\n"
            "<b>Available commands:</b>\n"
        )

        # Add each available command with its description
        for cmd, description in COMMAND_REGISTRY.items():
            if cmd in self._command_handlers:
                error_message += f"• /{cmd} - {html.escape(description)}\n"

        error_message += (
            "\n💡 <b>Tips:</b>\n"
            "• Use the command menu (/) to see all commands\n"
            "• Type /help for detailed information\n"
            "• Commands support autocompletion"
        )

        # Send the error message with HTML formatting
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            error_message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

        # Log the unknown command
        logger.warning(f"User {user_id} sent unknown command: {command}")

    async def setup_command_handlers(self) -> None:
        """Set up command handlers for the bot.

        This method should be called after all command handlers have been registered
        and before starting the bot. It also sets up bot commands for autocompletion.
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

        # Add keyboard button handler (must be before unknown command handler)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
                handle_keyboard_button,
            )
        )
        logger.info("Added handler for keyboard buttons")

        # Add handler for unknown commands (must be last to catch unhandled commands)
        self.application.add_handler(
            MessageHandler(
                filters.COMMAND & ~filters.UpdateType.EDITED_MESSAGE,
                self._handle_unknown_command,
            )
        )
        logger.info("Added handler for unknown commands")

        # Set bot commands for autocompletion
        await self.set_bot_commands()

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
        "Use /help to see all available commands or /settings to manage your preferences.\n\n"
        "💡 Use the keyboard buttons below for quick access to main features!"
    )

    # Initialize keyboard manager and send message with persistent keyboard
    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )
    logger.info(f"Registered and sent welcome message to user {user.id}")


async def handle_help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /help command.

    This command provides a comprehensive list of available commands and their descriptions.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    if not update.message or not update.effective_user:
        logger.warning("Received help command without message or effective_user")
        return

    # Use MessageFormatter to create properly formatted help message
    help_message = MessageFormatter.format_help_message(COMMAND_REGISTRY)

    # Add additional information about automatic features
    help_message += (
        "\n\n<b>🤖 Automatic Features:</b>\n"
        "• Morning briefings with your daily schedule\n"
        "• Reminders about upcoming trips\n"
        "• Important task deadlines\n"
        "• Smart email filtering and notifications\n\n"
        "<b>ℹ️ Additional Info:</b>\n"
        "• Use the command menu (/) to see all available commands\n"
        "• Commands support autocompletion in most Telegram clients\n\n"
        "If you have any issues or questions, please contact your system administrator."
    )

    # Send help message with persistent keyboard
    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        help_message,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )
    logger.info(f"Sent comprehensive help message to user {update.effective_user.id}")


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
    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        "🔄 Generating your briefing... This may take a moment.",
        reply_markup=keyboard_manager.create_main_keyboard(),
    )
    logger.info(f"Received briefing request from telegram user {telegram_user_id}")

    try:
        # Get the user from the database
        user_service = get_user_service()
        user = await user_service.get_user_by_telegram_chat_id(telegram_user_id)

        if not user:
            keyboard_manager = PersistentKeyboardManager()
            await update.message.reply_text(
                "❌ You need to register first. Please use /start to register.",
                reply_markup=keyboard_manager.create_main_keyboard(),
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

        # Send confirmation that the workflow was started with persistent keyboard
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "✅ Your briefing is being generated and will be delivered shortly!",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

        logger.info(f"Successfully started briefing workflow for user {user.id}")

    except Exception as e:
        error_message = "❌ Sorry, I encountered an error while generating your briefing. Please try again later."
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            error_message, reply_markup=keyboard_manager.create_main_keyboard()
        )
        logger.error(
            f"Error generating briefing for telegram user {telegram_user_id}: {e}"
        )


async def handle_settings_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /settings command.

    This command shows the user's current settings and provides guidance on customization.

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

    # Create comprehensive settings message with proper escaping
    username_display = f"@{user.username}" if user.username else "Not set"
    registered_display = (
        user.registered_at.strftime("%Y-%m-%d %H:%M UTC")
        if user.registered_at
        else "Unknown"
    )

    # Fetch all user settings
    all_settings = await user_service.get_all_settings(user.id)

    current_settings = ""
    for key in [
        SettingKey.GREET,
        SettingKey.BRIEFING_TIME,
        SettingKey.ABOUT_ME,
        SettingKey.LOCATION,
        SettingKey.IGNORE_EMAILS,
    ]:
        label = SETTINGS_LABEL_LOOKUP[key]
        value = all_settings.get(key.value)
        if isinstance(value, list):
            display = ", ".join(value) if value else "Not set"
        else:
            display = str(value) if value else "Not set"
        display = escape_markdown(display, version=2)
        current_settings += f"• {label}: {display}\n"

    settings_message = (
        "⚙️ **Your Settings**\n\n"
        "**User Information:**\n"
        f"• User ID: `{user.id}`\n"
        f"• Name: {user.first_name or 'Not set'}\n"
        f"• Username: {username_display}\n"
        f"• Registered: {registered_display}\n\n"
        "**Current Preferences:**\n"
        f"{current_settings}\n"
        "**Available Settings Commands:**\n"
        "• /update\\_settings - Modify your preferences\n"
        "• /google\\_auth - Connect Google services\n"
        "• /ignore\\_email - Manage email filters\n\n"
        "**Current Features:**\n"
        "• Daily briefings\n"
        "• Trip notifications\n"
        "• Email filtering\n"
        "• Calendar integration\n\n"
        "Use /help to see all available commands\\."
    )

    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        settings_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )
    logger.info(f"Sent comprehensive settings to user {user_id}")


async def start_update_settings(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display inline keyboard for selecting a setting to update."""

    if not update.message:
        return ConversationHandler.END

    keyboard_manager = SettingsInterfaceManager()
    await update.message.reply_text(
        "Please choose which setting you want to update:",
        reply_markup=keyboard_manager.create_settings_keyboard(),
    )
    return ConversationHandler.END


async def handle_setting_value_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle user input for a setting value after inline selection."""

    if not update.message or update.message.text is None or not update.effective_user:
        return

    pending_key = cast(
        str | None, cast(dict[str, Any], context.user_data).get("pending_setting")
    )
    if not pending_key:
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        cast(dict[str, Any], context.user_data).pop("pending_setting", None)
        return

    value = update.message.text.strip()

    key_enum = SettingKey(pending_key)
    if key_enum is SettingKey.GREET and not value:
        value = "first_name"

    await user_service.set_setting(user.id, key_enum, value)

    label = SETTINGS_LABEL_LOOKUP.get(key_enum, pending_key)
    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        f"{label} updated to: {value}",
        reply_markup=keyboard_manager.create_main_keyboard(),
    )

    cast(dict[str, Any], context.user_data).pop("pending_setting", None)


async def cancel_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generic cancel handler for conversations."""

    if update.message:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "Operation cancelled.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

    cast(dict[str, Any], context.user_data).pop("pending_setting", None)
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
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return

    args = getattr(context, "args", [])
    account = args[0] if args else None

    client = GoogleClient(user.id, account=account)
    if await client.is_authenticated():
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "✅ You are already authenticated with Google.\n\n"
            "**Connected Services:**\n"
            "• Google Calendar\n"
            "• Gmail\n"
            "• Google Drive (if needed)\n\n"
            "Your Google integration is working properly!",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return

    settings = get_settings()
    state = create_state_jwt(user.id, settings, account=account)
    auth_url = await client.generate_auth_url(state)

    message = (
        "🔐 **Google Authentication Required**\n\n"
        f"Please [click here to authorize]({auth_url}) access to your Google account.\n\n"
        "**This will enable:**\n"
        "• Calendar event notifications\n"
        "• Email monitoring and filtering\n"
        "• Smart briefing generation\n"
        "• Trip and event reminders\n\n"
        "You'll receive a confirmation message once the authentication is completed."
    )
    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )
    logger.info(f"Sent Google auth link to user {chat_user.id}")


async def handle_ignore_email_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Add an email pattern to the ignored list for the user."""

    from the_assistant.integrations.telegram.enhanced_command_handlers import (
        IgnoreEmailHandler,
    )

    handler = IgnoreEmailHandler()
    await handler.handle_command(update, context)


async def handle_list_ignored_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show all ignored email patterns for the user."""

    if not update.message or not update.effective_user:
        logger.warning("Received list_ignored command without message or user")
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return

    ignored = (
        cast(
            list[str] | None,
            await user_service.get_setting(user.id, SettingKey.IGNORE_EMAILS),
        )
        or []
    )

    if not ignored:
        message = (
            "📧 **Email Ignore Patterns**\n\n"
            "**No patterns currently ignored\\.**\n\n"
            "Use `/ignore\\_email <pattern>` to add patterns to ignore\\."
        )
    else:
        message = (
            "📧 **Email Ignore Patterns**\n\n"
            f"**Currently ignoring {len(ignored)} pattern\\(s\\):**\n"
        )
        for i, pattern in enumerate(ignored, 1):
            escaped_pattern = escape_markdown(pattern, version=2)
            message += f"{i}\\. `{escaped_pattern}`\n"

        message += (
            "\n**Commands:**\n"
            "• `/ignore\\_email <pattern>` \\- Add new pattern\n"
            "• `/settings` \\- View all settings"
        )

    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )


async def handle_memory_add_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Add a short personal memory for the user with dual-mode support."""
    from the_assistant.integrations.telegram.enhanced_command_handlers import (
        MemoryAddHandler,
    )

    if not update.message or not update.effective_user:
        return ConversationHandler.END

    try:
        # Get command arguments
        args = getattr(context, "args", [])

        handler = MemoryAddHandler()

        if args:
            # Direct mode: process command with provided arguments
            await handler.handle_direct_mode(update, context, args)
            return ConversationHandler.END
        else:
            # Dialog mode: start interactive dialog for argument collection
            await handler.handle_dialog_mode(update, context)
            return ConversationState.MEMORY_INPUT

    except Exception as e:
        from the_assistant.integrations.telegram.enhanced_handlers import ErrorHandler

        await ErrorHandler.handle_command_error(update, e, "memory_add")
        return ConversationHandler.END


async def handle_memory_input_dialog(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle memory input in dialog mode."""
    from the_assistant.integrations.telegram.enhanced_command_handlers import (
        MemoryAddHandler,
    )
    from the_assistant.integrations.telegram.enhanced_handlers import (
        CommandValidator,
        ErrorHandler,
        MessageFormatter,
    )

    if not update.message or not update.effective_user or not update.message.text:
        return ConversationHandler.END

    text = update.message.text.strip()

    try:
        # Validate input
        is_valid, validation_message = await CommandValidator.validate_memory_input(
            text
        )
        if not is_valid:
            keyboard_manager = PersistentKeyboardManager()
            await update.message.reply_text(
                f"❌ {validation_message}\n\nPlease try again:",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard_manager.create_main_keyboard(),
            )
            return ConversationState.MEMORY_INPUT  # Stay in dialog mode

        # Get user
        user_service = get_user_service()
        user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
        if not user:
            keyboard_manager = PersistentKeyboardManager()
            await update.message.reply_text(
                "❌ You need to register first. Please use /start to register.",
                reply_markup=keyboard_manager.create_main_keyboard(),
            )
            return ConversationHandler.END

        # Store memory using the handler's method
        handler = MemoryAddHandler()
        await handler._store_memory(user, text)

        # Send confirmation
        confirmation = MessageFormatter.format_confirmation("Memory added", text)
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            confirmation,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

        # Clear conversation state
        cast(dict[str, Any], context.user_data).pop("conversation_state", None)
        return ConversationHandler.END

    except ValueError as e:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            f"❌ {str(e)}",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return ConversationHandler.END
    except Exception as e:
        await ErrorHandler.handle_command_error(update, e, "memory_add")
        return ConversationHandler.END


async def handle_memory_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show all stored memories for the user."""
    if not update.message or not update.effective_user:
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return

    memories = (
        cast(
            dict[str, dict[str, str]] | None,
            await user_service.get_setting(user.id, SettingKey.MEMORIES),
        )
        or {}
    )

    if not memories:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "No memories stored. Use /memory_add to add one.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return

    items = sorted(memories.items())
    message = "🧠 **Your memories:**\n\n"
    for i, (_, mem) in enumerate(items, 1):
        txt = mem.get("user_input", "")
        # Use plain text instead of markdown for user content to avoid parsing issues
        message += f"{i}. {txt}\n"
    message += "\nUse /memory_delete <id> to delete a memory."
    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        message,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )


async def start_memory_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start the memory deletion conversation or handle direct deletion."""
    if not update.message or not update.effective_user:
        return ConversationHandler.END

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
        )
        return ConversationHandler.END

    memories = (
        cast(
            dict[str, dict[str, str]] | None,
            await user_service.get_setting(user.id, SettingKey.MEMORIES),
        )
        or {}
    )

    if not memories:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "No memories to delete. Use /memory_add to add one first.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return ConversationHandler.END

    # Check if user provided an ID directly
    args = getattr(context, "args", [])
    if args and args[0].isdigit():
        mem_id = int(args[0])
        if mem_id < 1 or mem_id > len(memories):
            keyboard_manager = PersistentKeyboardManager()
            await update.message.reply_text(
                "Invalid memory id.",
                reply_markup=keyboard_manager.create_main_keyboard(),
            )
            return ConversationHandler.END

        key = sorted(memories.keys())[mem_id - 1]
        memory_text = memories[key].get("user_input", "")
        del memories[key]
        await user_service.set_setting(user.id, SettingKey.MEMORIES, memories)
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            f"✅ Memory deleted: {memory_text}",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return ConversationHandler.END

    # Show keyboard with memory options
    items = sorted(memories.items())
    keyboard = []
    for i, (_, mem) in enumerate(items, 1):
        txt = mem.get("user_input", "")
        # Truncate long memories for keyboard display
        display_text = txt[:40] + "..." if len(txt) > 40 else txt
        keyboard.append([f"{i}. {display_text}"])

    keyboard.append(["Cancel"])

    await update.message.reply_text(
        "🗑️ Select a memory to delete:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return ConversationState.SELECT_MEMORY_TO_DELETE


async def select_memory_to_delete(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the user's memory selection for deletion."""
    if not update.message or not update.effective_user or not update.message.text:
        return ConversationHandler.END

    choice = update.message.text.strip()
    if choice == "Cancel":
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "Memory deletion cancelled.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return ConversationHandler.END

    # Extract the memory ID from the choice (format: "1. memory text...")
    try:
        mem_id = int(choice.split(".")[0])
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Please select a memory from the options provided."
        )
        return ConversationState.SELECT_MEMORY_TO_DELETE

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return ConversationHandler.END

    memories = (
        cast(
            dict[str, dict[str, str]] | None,
            await user_service.get_setting(user.id, SettingKey.MEMORIES),
        )
        or {}
    )

    if mem_id < 1 or mem_id > len(memories):
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "Invalid memory selection.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return ConversationHandler.END

    key = sorted(memories.keys())[mem_id - 1]
    memory_text = memories[key].get("user_input", "")
    del memories[key]
    await user_service.set_setting(user.id, SettingKey.MEMORIES, memories)

    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        f"✅ Memory deleted: {memory_text}",
        reply_markup=keyboard_manager.create_main_keyboard(),
    )
    return ConversationHandler.END


async def handle_memory_delete_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Legacy handler for direct memory deletion (kept for backward compatibility)."""
    # This will be handled by the conversation handler now
    pass


async def handle_add_task_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int | None:
    """Create a scheduled task from user instruction with dual-mode support."""
    from the_assistant.integrations.telegram.enhanced_command_handlers import (
        AddTaskHandler,
    )

    handler = AddTaskHandler()
    await handler.handle_command(update, context)

    # Return conversation state if dialog mode was triggered
    args = getattr(context, "args", [])
    if not args:
        return ConversationState.TASK_INPUT

    return None


async def handle_task_input_dialog(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle task input in dialog mode."""
    if not update.message or not update.effective_user:
        return ConversationHandler.END

    raw_instruction = update.message.text.strip()

    try:
        from the_assistant.integrations.telegram.enhanced_command_handlers import (
            AddTaskHandler,
        )

        # Create a mock context with args for direct mode processing
        mock_context = context
        mock_context.args = raw_instruction.split()

        handler = AddTaskHandler()
        await handler.handle_direct_mode(update, mock_context, raw_instruction.split())

        # Send message with persistent keyboard
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "✅ Task processing completed!",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

    except Exception as e:
        logger.error(f"Error processing task in dialog mode: {e}")
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            f"❌ Error: {str(e)}", reply_markup=keyboard_manager.create_main_keyboard()
        )

    return ConversationHandler.END


async def handle_countdown_input_dialog(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle countdown input in dialog mode."""
    if not update.message or not update.effective_user:
        return ConversationHandler.END

    raw_description = update.message.text.strip()

    try:
        from the_assistant.integrations.telegram.enhanced_command_handlers import (
            AddCountdownHandler,
        )

        # Create a mock context with args for direct mode processing
        mock_context = context
        mock_context.args = raw_description.split()

        handler = AddCountdownHandler()
        await handler.handle_direct_mode(update, mock_context, raw_description.split())

        # Send message with persistent keyboard
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "✅ Countdown processing completed!",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

    except Exception as e:
        logger.error(f"Error processing countdown in dialog mode: {e}")
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            f"❌ Error: {str(e)}", reply_markup=keyboard_manager.create_main_keyboard()
        )

    return ConversationHandler.END


async def handle_keyboard_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle persistent keyboard button presses.

    This function maps keyboard button presses to their corresponding commands
    and executes them with the same behavior as typing the command.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    if not update.message or update.message.text is None or not update.effective_user:
        return

    keyboard_manager = PersistentKeyboardManager()
    command = await keyboard_manager.handle_keyboard_button(update, context)

    if not command:
        # Not a keyboard button, ignore
        return

    logger.info(f"Processing keyboard button command: {command}")

    try:
        # Map keyboard button to corresponding command handler
        if command == "briefing":
            await handle_briefing_command(update, context)
        elif command == "add_task":
            # Clear args to trigger dialog mode for keyboard buttons
            context.args = []
            await handle_add_task_command(update, context)
        elif command == "add_countdown":
            # Clear args to trigger dialog mode for keyboard buttons
            context.args = []
            await handle_add_countdown_command(update, context)
        elif command == "track_habit":
            await handle_track_habit_command(update, context)
        elif command == "memory":
            await handle_memory_command(update, context)
        elif command == "update_settings":
            await start_update_settings(update, context)
        else:
            logger.warning(f"Unknown keyboard command: {command}")
            await update.message.reply_text(
                f"❌ Sorry, the command '{command}' is not implemented yet.",
                reply_markup=keyboard_manager.create_main_keyboard(),
            )
            return

    except Exception as e:
        logger.error(f"Error handling keyboard button command '{command}': {e}")
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "❌ Sorry, there was an error processing your request. Please try again.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )


async def handle_add_countdown_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int | None:
    """Create a countdown event from user description with dual-mode support."""
    from the_assistant.integrations.telegram.enhanced_command_handlers import (
        AddCountdownHandler,
    )

    handler = AddCountdownHandler()
    await handler.handle_command(update, context)

    # Return conversation state if dialog mode was triggered
    args = getattr(context, "args", [])
    if not args:
        return ConversationState.COUNTDOWN_INPUT

    return None


async def handle_status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show bot status and integration health."""

    if not update.message or not update.effective_user:
        logger.warning("Received status command without message or user")
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register.",
            reply_markup=keyboard_manager.create_main_keyboard(),
        )
        return

    # Check Google authentication status
    google_status = "❌ Not connected"
    try:
        google_client = GoogleClient(user.id)
        if await google_client.is_authenticated():
            google_status = "✅ Connected"
    except Exception as e:
        google_status = f"⚠️ Error: {str(e)[:50]}..."

    # Get ignored email count
    raw_ignored = await user_service.get_setting(user.id, SettingKey.IGNORE_EMAILS)
    ignored_count = len(raw_ignored) if isinstance(raw_ignored, list) else 0

    status_message = (
        "🤖 **Bot Status**\n\n"
        f"**User:** {user.first_name or 'Unknown'} \\(ID: {user.id}\\)\n"
        f"**Registered:** {user.registered_at.strftime('%Y-%m-%d') if user.registered_at else 'Unknown'}\n\n"
        f"**Integrations:**\n"
        f"• Google Services: {google_status}\n"
        f"• Telegram: ✅ Connected\n\n"
        f"**Settings:**\n"
        f"• Ignored email patterns: {ignored_count}\n\n"
        f"**Available Features:**\n"
        f"• Daily briefings\n"
        f"• Trip notifications\n"
        f"• Email filtering\n"
        f"• Calendar integration\n\n"
        f"Use `/help` to see all available commands\\."
    )

    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        status_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )


async def handle_track_habit_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /track_habit command with placeholder functionality.

    This is a placeholder implementation for future habit tracking features.

    Args:
        update: The update object from Telegram
        context: The context object from Telegram
    """
    if not update.message or not update.effective_user:
        logger.warning("Received track_habit command without message or effective_user")
        return

    placeholder_message = (
        "📈 <b>Track Habit</b>\n\n"
        "🚧 This feature is coming soon!\n\n"
        "In the future, you'll be able to:\n"
        "• Track daily habits and routines\n"
        "• Set habit goals and reminders\n"
        "• View progress and statistics\n"
        "• Get motivational insights\n\n"
        "Stay tuned for updates! 🎯"
    )

    # Send placeholder message with persistent keyboard
    keyboard_manager = PersistentKeyboardManager()
    await update.message.reply_text(
        placeholder_message,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_manager.create_main_keyboard(),
    )
    logger.info(
        f"Sent track_habit placeholder message to user {update.effective_user.id}"
    )


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
    # Note: Descriptions are automatically taken from COMMAND_REGISTRY
    await client.register_command_handler("start", handle_start_command)
    await client.register_command_handler("help", handle_help_command)
    await client.register_command_handler("briefing", handle_briefing_command)
    await client.register_command_handler("settings", handle_settings_command)
    await client.register_command_handler("update_settings", start_update_settings)
    await client.register_command_handler("google_auth", handle_google_auth_command)
    await client.register_command_handler("ignore_email", handle_ignore_email_command)
    await client.register_command_handler("list_ignored", handle_list_ignored_command)
    await client.register_command_handler("status", handle_status_command)
    await client.register_command_handler("memory", handle_memory_command)
    await client.register_command_handler("memories", handle_memory_command)
    await client.register_command_handler("memory_add", handle_memory_add_command)
    await client.register_command_handler("add_task", handle_add_task_command)
    await client.register_command_handler("add_countdown", handle_add_countdown_command)
    await client.register_command_handler("track_habit", handle_track_habit_command)
    # Inline settings handlers
    settings_callback_handler = CallbackQueryHandler(
        SettingsInterfaceManager().handle_setting_callback, pattern="^setting:"
    )
    setting_value_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_setting_value_input
    )

    # Memory deletion conversation handler
    memory_delete_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("memory_delete", start_memory_delete)],
        states={
            ConversationState.SELECT_MEMORY_TO_DELETE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_memory_to_delete)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_update)],
    )

    # Memory input dialog handler
    memory_input_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("memory_add", handle_memory_add_command)],
        states={
            ConversationState.MEMORY_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_memory_input_dialog
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_update)],
        per_message=False,
        per_chat=True,
        per_user=True,
    )

    # Task input dialog handler
    task_input_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_task", handle_add_task_command)],
        states={
            ConversationState.TASK_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_task_input_dialog
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_update)],
        per_message=False,
        per_chat=True,
        per_user=True,
    )

    # Countdown input dialog handler
    countdown_input_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add_countdown", handle_add_countdown_command)],
        states={
            ConversationState.COUNTDOWN_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_countdown_input_dialog
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_update)],
        per_message=False,
        per_chat=True,
        per_user=True,
    )

    await client.register_handler(settings_callback_handler)
    await client.register_handler(setting_value_handler)
    await client.register_handler(memory_delete_conv_handler)
    await client.register_handler(memory_input_conv_handler)
    await client.register_handler(task_input_conv_handler)
    await client.register_handler(countdown_input_conv_handler)

    return client
