"""Telegram client for The Assistant."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

from telegram import (
    Bot,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
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

from .constants import (
    SETTINGS_DESCRIPTIONS,
    SETTINGS_LABEL_MAP,
    ConversationState,
    SettingKey,
)

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
    "memories": "List your stored memories (alias for /memory)",
    "memory_delete": "Delete a memory by its id",
    "add_task": "Create a new scheduled task",
    "add_countdown": "Add a countdown event",
    "cancel": "Cancel current settings operation and return to menu",
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
        parse_mode: str = ParseMode.HTML,
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

    async def register_handler(self, handler: ConversationHandler) -> None:
        """Register a generic Telegram handler."""

        self._extra_handlers.append(handler)
        logger.info("Registered additional handler")

    async def set_bot_commands(self) -> None:
        """Set bot commands for autocompletion in Telegram clients.

        This enables the command menu and autocompletion in Telegram clients.
        Commands are taken from the registered command handlers.
        """
        try:
            # Create BotCommand objects from registered commands
            commands = [
                BotCommand(
                    command=cmd, description=COMMAND_REGISTRY.get(cmd, "No description")
                )
                for cmd in self._command_handlers.keys()
                if cmd in COMMAND_REGISTRY  # Only include commands with descriptions
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

        # Create a helpful error message with command descriptions using HTML
        error_message = (
            f"❓ Sorry, I don't understand the command <code>{command}</code>.\n\n"
            "<b>Available commands:</b>\n"
        )

        # Add each available command with its description
        for cmd, description in COMMAND_REGISTRY.items():
            if cmd in self._command_handlers:
                error_message += f"• /{cmd} - {description}\n"

        error_message += (
            "\n💡 <b>Tips:</b>\n"
            "• Use the command menu (/) to see all commands\n"
            "• Type /help for detailed information\n"
            "• Commands support autocompletion"
        )

        # Send the error message with HTML formatting
        await update.message.reply_text(error_message, parse_mode=ParseMode.HTML)

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

        # Register callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(handle_callback_query))
        logger.info("Added callback query handler for inline keyboards")

        # Register message handler for settings input
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_settings_input)
        )
        logger.info("Added message handler for settings input")

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
        f"✅ You've been registered with ID: <code>{user.id}</code>\n\n"
        "Use /help to see all available commands or /settings to manage your preferences."
    )

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
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

    # Build help message from command registry using HTML formatting
    help_message = "📚 <b>Available Commands</b>\n\n"

    # Add each command with its description
    for command, description in COMMAND_REGISTRY.items():
        help_message += f"/{command} - {description}\n"

    help_message += (
        "\n<b>Automatic Features:</b>\n"
        "• Morning briefings with your daily schedule\n"
        "• Reminders about upcoming trips\n"
        "• Important task deadlines\n"
        "• Smart email filtering and notifications\n\n"
        "<b>Tips:</b>\n"
        "• Use the command menu (/) to see all available commands\n"
        "• Commands support autocompletion in most Telegram clients\n"
        "• Use /settings to customize your experience\n\n"
        "If you have any issues or questions, please contact your system administrator."
    )

    await update.message.reply_text(help_message, parse_mode=ParseMode.HTML)
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
    """Handle the /settings command with a menu interface.

    This command shows a menu where users can view current settings or modify them.

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

    # Create menu with inline keyboard
    keyboard = [
        [
            InlineKeyboardButton(
                "📋 Show Current Settings", callback_data="settings_show"
            )
        ],
        [InlineKeyboardButton("✏️ Modify Settings", callback_data="settings_modify")],
        [
            InlineKeyboardButton(
                "🔐 Google Authentication", callback_data="settings_google_auth"
            )
        ],
        [
            InlineKeyboardButton(
                "📧 Email Filters", callback_data="settings_email_filters"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    settings_message = (
        "⚙️ <b>Settings Menu</b>\n\n"
        "Choose an option below to view or modify your settings:"
    )

    await update.message.reply_text(
        settings_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )
    logger.info(f"Sent settings menu to user {user_id}")


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

    choice = update.message.text.strip()  # type: ignore[possibly-unbound-attribute]
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

    value = update.message.text.strip()  # type: ignore[possibly-unbound-attribute]
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

    await user_service.set_setting(user.id, setting_key, value)

    await update.message.reply_text(
        f"{setting_label} updated to: {value}", reply_markup=ReplyKeyboardRemove()
    )

    user_data.pop("setting_key", None)
    user_data.pop("setting_label", None)

    return ConversationHandler.END


async def cancel_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the settings update conversation."""

    if update.message:
        # Clear any awaiting states
        user_data = cast(dict[str, Any], context.user_data)
        user_data.pop("setting_key", None)
        user_data.pop("setting_label", None)
        user_data.pop("awaiting_setting_value", None)
        user_data.pop("awaiting_email_pattern", None)

        # Show settings menu instead of just cancelling
        keyboard = [
            [
                InlineKeyboardButton(
                    "⚙️ Back to Settings Menu", callback_data="back_to_settings"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "❌ Operation cancelled.", reply_markup=reply_markup
        )
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
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
        )
        return

    args = getattr(context, "args", [])
    account = args[0] if args else None

    client = GoogleClient(user.id, account=account)
    if await client.is_authenticated():
        await update.message.reply_text(
            "✅ You are already authenticated with Google.\n\n"
            "<b>Connected Services:</b>\n"
            "• Google Calendar\n"
            "• Gmail\n"
            "• Google Drive (if needed)\n\n"
            "Your Google integration is working properly!",
            parse_mode=ParseMode.HTML,
        )
        return

    settings = get_settings()
    state = create_state_jwt(user.id, settings, account=account)
    auth_url = await client.generate_auth_url(state)

    message = (
        "🔐 <b>Google Authentication Required</b>\n\n"
        f"Please <a href='{auth_url}'>click here to authorize</a> access to your Google account.\n\n"
        "<b>This will enable:</b>\n"
        "• Calendar event notifications\n"
        "• Email monitoring and filtering\n"
        "• Smart briefing generation\n"
        "• Trip and event reminders\n\n"
        "You'll receive a confirmation message once the authentication is completed."
    )
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    logger.info(f"Sent Google auth link to user {chat_user.id}")


async def handle_ignore_email_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Add an email pattern to the ignored list for the user."""

    if not update.message or not update.effective_user:
        logger.warning("Received ignore_email command without message or user")
        return

    args = getattr(context, "args", [])
    if not args:
        # Show usage information
        usage_message = (
            "📧 <b>Email Ignore Patterns</b>\n\n"
            "<b>Usage:</b> <code>/ignore_email &lt;pattern&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/ignore_email noreply@example.com</code> - Ignore specific email\n"
            "• <code>/ignore_email @spam.com</code> - Ignore entire domain\n"
            "• <code>/ignore_email newsletter</code> - Ignore emails containing 'newsletter'\n\n"
            "<b>Other Commands:</b>\n"
            "• /list_ignored - View all ignored patterns\n"
            "• /settings - View your current settings"
        )

        await update.message.reply_text(usage_message, parse_mode=ParseMode.HTML)
        return

    mask = args[0].strip()

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
        )
        return

    ignored = (
        cast(
            list[str] | None,
            await user_service.get_setting(user.id, SettingKey.IGNORE_EMAILS),
        )
        or []
    )

    if mask in ignored:
        await update.message.reply_text(
            f"📧 Pattern <code>{mask}</code> is already in your ignore list.\n\n"
            f"Use /list_ignored to see all ignored patterns.",
            parse_mode=ParseMode.HTML,
        )
        return

    ignored.append(mask)
    await user_service.set_setting(user.id, SettingKey.IGNORE_EMAILS, ignored)

    await update.message.reply_text(
        f"✅ Added <code>{mask}</code> to your email ignore list.\n\n"
        f"Emails matching this pattern will no longer trigger notifications.\n"
        f"Use /list_ignored to see all ignored patterns.",
        parse_mode=ParseMode.HTML,
    )


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
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
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
            "📧 <b>Email Ignore Patterns</b>\n\n"
            "<b>No patterns currently ignored.</b>\n\n"
            "Use <code>/ignore_email &lt;pattern&gt;</code> to add patterns to ignore."
        )
    else:
        message = (
            "📧 <b>Email Ignore Patterns</b>\n\n"
            f"<b>Currently ignoring {len(ignored)} pattern(s):</b>\n"
        )
        for i, pattern in enumerate(ignored, 1):
            # HTML escape the pattern
            escaped_pattern = (
                pattern.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            message += f"{i}. <code>{escaped_pattern}</code>\n"

        message += (
            "\n<b>Commands:</b>\n"
            "• /ignore_email &lt;pattern&gt; - Add new pattern\n"
            "• /settings - View all settings"
        )

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def handle_memory_add_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Add a short personal memory for the user."""
    if not update.message or not update.effective_user:
        return

    text = " ".join(getattr(context, "args", [])).strip()
    if not text:
        await update.message.reply_text("Usage: /memory_add <text>")
        return
    if len(text) > 500:
        await update.message.reply_text("Memory is too long (max 500 characters).")
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
        )
        return

    memories = (
        cast(
            dict[str, dict[str, str]] | None,
            await user_service.get_setting(user.id, SettingKey.MEMORIES),
        )
        or {}
    )

    if len(memories) >= 10:
        await update.message.reply_text(
            "You have reached the 10 memories limit. Delete one with /memory_delete <id>."
        )
        return

    key = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    while key in memories:
        key = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")
    memories[key] = {"user_input": text}
    await user_service.set_setting(user.id, SettingKey.MEMORIES, memories)

    await update.message.reply_text("✅ Memory added.")


async def handle_memory_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show all stored memories for the user."""
    if not update.message or not update.effective_user:
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
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
        await update.message.reply_text(
            "No memories stored. Use /memory_add to add one."
        )
        return

    items = sorted(memories.items())
    message = "🧠 <b>Your memories:</b>\n\n"
    for i, (_, mem) in enumerate(items, 1):
        txt = mem.get("user_input", "")
        # HTML escape user content to avoid parsing issues
        escaped_txt = (
            txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        message += f"{i}. {escaped_txt}\n"
    message += "\nUse /memory_delete &lt;id&gt; to delete a memory."
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


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
        await update.message.reply_text(
            "No memories to delete. Use /memory_add to add one first."
        )
        return ConversationHandler.END

    # Check if user provided an ID directly
    args = getattr(context, "args", [])
    if args and args[0].isdigit():
        mem_id = int(args[0])
        if mem_id < 1 or mem_id > len(memories):
            await update.message.reply_text("Invalid memory id.")
            return ConversationHandler.END

        key = sorted(memories.keys())[mem_id - 1]
        memory_text = memories[key].get("user_input", "")
        del memories[key]
        await user_service.set_setting(user.id, SettingKey.MEMORIES, memories)
        await update.message.reply_text(f"✅ Memory deleted: {memory_text}")
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
        await update.message.reply_text(
            "Memory deletion cancelled.", reply_markup=ReplyKeyboardRemove()
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
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register.",
            reply_markup=ReplyKeyboardRemove(),
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
        await update.message.reply_text(
            "Invalid memory selection.", reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    key = sorted(memories.keys())[mem_id - 1]
    memory_text = memories[key].get("user_input", "")
    del memories[key]
    await user_service.set_setting(user.id, SettingKey.MEMORIES, memories)

    await update.message.reply_text(
        f"✅ Memory deleted: {memory_text}", reply_markup=ReplyKeyboardRemove()
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
) -> None:
    """Create a scheduled task from user instruction."""
    if not update.message or not update.effective_user:
        return

    raw_instruction = " ".join(getattr(context, "args", [])).strip()
    if not raw_instruction:
        await update.message.reply_text("Usage: /add_task <instruction>")
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
        )
        return

    from the_assistant.integrations.llm import TaskParser

    parser = TaskParser()
    schedule, instruction = await parser.parse(raw_instruction)
    if not schedule:
        await update.message.reply_text(
            "❌ Could not parse a schedule. Try something like 'every day at 6pm say hi'."
        )
        return

    await user_service.create_task(
        user.id, raw_instruction, schedule=schedule, instruction=instruction
    )

    await update.message.reply_text("✅ Task added.")


async def handle_add_countdown_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Create a countdown event from user description."""
    if not update.message or not update.effective_user:
        return

    raw_text = " ".join(getattr(context, "args", [])).strip()
    if not raw_text:
        await update.message.reply_text("Usage: /add_countdown <description>")
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
        )
        return

    from the_assistant.integrations.llm import CountdownParser

    parser = CountdownParser()
    event_time, description = await parser.parse(raw_text)
    if event_time is None:
        await update.message.reply_text(
            "❌ Could not parse a date. Try 'my birthday on 2025-05-01'."
        )
        return

    await user_service.create_countdown(
        user.id, description=description, event_time=event_time
    )

    await update.message.reply_text("✅ Countdown added.")


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
        await update.message.reply_text(
            "❌ You need to register first. Please use /start to register."
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
        "🤖 <b>Bot Status</b>\n\n"
        f"<b>User:</b> {user.first_name or 'Unknown'} (ID: {user.id})\n"
        f"<b>Registered:</b> {user.registered_at.strftime('%Y-%m-%d') if user.registered_at else 'Unknown'}\n\n"
        f"<b>Integrations:</b>\n"
        f"• Google Services: {google_status}\n"
        f"• Telegram: ✅ Connected\n\n"
        f"<b>Settings:</b>\n"
        f"• Ignored email patterns: {ignored_count}\n\n"
        f"<b>Available Features:</b>\n"
        f"• Daily briefings\n"
        f"• Trip notifications\n"
        f"• Email filtering\n"
        f"• Calendar integration\n\n"
        f"Use /help to see all available commands."
    )

    await update.message.reply_text(status_message, parse_mode=ParseMode.HTML)


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

    # Register all command handlers from COMMAND_REGISTRY
    # Note: Descriptions are automatically taken from COMMAND_REGISTRY
    await client.register_command_handler("start", handle_start_command)
    await client.register_command_handler("help", handle_help_command)
    await client.register_command_handler("briefing", handle_briefing_command)
    await client.register_command_handler("settings", handle_settings_command)
    await client.register_command_handler("google_auth", handle_google_auth_command)
    await client.register_command_handler("ignore_email", handle_ignore_email_command)
    await client.register_command_handler("list_ignored", handle_list_ignored_command)
    await client.register_command_handler("status", handle_status_command)
    await client.register_command_handler("memory_add", handle_memory_add_command)
    await client.register_command_handler("memory", handle_memory_command)
    await client.register_command_handler(
        "memories", handle_memory_command
    )  # Alias for memory
    await client.register_command_handler("add_task", handle_add_task_command)
    await client.register_command_handler("add_countdown", handle_add_countdown_command)

    # Register conversation entry points as commands for menu visibility
    # These will be handled by conversation handlers but need to be in the command menu
    await client.register_command_handler("update_settings", start_update_settings)
    await client.register_command_handler("memory_delete", start_memory_delete)

    # Settings conversation handler
    settings_conv_handler = ConversationHandler(
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

    await client.register_handler(settings_conv_handler)
    await client.register_handler(memory_delete_conv_handler)

    return client


async def handle_callback_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries from inline keyboards.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()  # Acknowledge the callback query

    if query.data == "settings_show":
        await show_current_settings(update, context)
    elif query.data == "settings_modify":
        await show_modify_settings_menu(update, context)
    elif query.data == "settings_google_auth":
        await handle_google_auth_from_menu(update, context)
    elif query.data == "settings_email_filters":
        await show_email_filters_menu(update, context)
    elif query.data.startswith("modify_"):
        await handle_setting_modification(update, context)
    elif query.data == "email_filters_list":
        await show_ignored_emails_from_menu(update, context)
    elif query.data == "email_filters_add":
        await prompt_add_email_filter(update, context)
    elif query.data == "back_to_settings":
        await show_settings_menu(update, context)


async def show_current_settings(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the user's current settings."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(query.from_user.id)
    if not user:
        await query.edit_message_text(
            "❌ User not found. Please use /start to register."
        )
        return

    # Get current settings values
    settings_values = {}
    for setting_key in SettingKey:
        value = await user_service.get_setting(user.id, setting_key)
        settings_values[setting_key] = value

    # Create comprehensive settings message
    username_display = f"@{user.username}" if user.username else "Not set"
    registered_display = (
        user.registered_at.strftime("%Y-%m-%d %H:%M UTC")
        if user.registered_at
        else "Unknown"
    )

    settings_message = (
        "📋 <b>Current Settings</b>\n\n"
        "<b>User Information:</b>\n"
        f"• User ID: <code>{user.id}</code>\n"
        f"• Name: {user.first_name or 'Not set'}\n"
        f"• Username: {username_display}\n"
        f"• Registered: {registered_display}\n\n"
        "<b>Preferences:</b>\n"
    )

    # Add each setting with its current value
    for setting_key, description in SETTINGS_DESCRIPTIONS.items():
        value = settings_values.get(setting_key)
        if setting_key == SettingKey.IGNORE_EMAILS:
            count = len(value) if isinstance(value, list) else 0
            display_value = f"{count} pattern(s)" if count > 0 else "None"
        else:
            display_value = str(value) if value else "Not set"

        settings_message += f"• {description}: <code>{display_value}</code>\n"

    # Add back button
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        settings_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def show_modify_settings_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the menu for modifying settings."""
    query = update.callback_query
    if not query:
        return

    keyboard = []
    for label, setting_key in SETTINGS_LABEL_MAP.items():
        if setting_key != SettingKey.IGNORE_EMAILS:  # Email filters have their own menu
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"✏️ {label}", callback_data=f"modify_{setting_key.value}"
                    )
                ]
            )

    keyboard.append(
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_settings")]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = "✏️ <b>Modify Settings</b>\n\nSelect a setting to modify:"

    await query.edit_message_text(
        message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def handle_google_auth_from_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle Google authentication from the settings menu."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(query.from_user.id)
    if not user:
        await query.edit_message_text(
            "❌ User not found. Please use /start to register."
        )
        return

    client = GoogleClient(user.id)
    if await client.is_authenticated():
        message = (
            "✅ <b>Google Authentication Status</b>\n\n"
            "You are already authenticated with Google.\n\n"
            "<b>Connected Services:</b>\n"
            "• Google Calendar\n"
            "• Gmail\n"
            "• Google Drive (if needed)\n\n"
            "Your Google integration is working properly!"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_settings")]
        ]
    else:
        settings = get_settings()
        state = create_state_jwt(user.id, settings)
        auth_url = await client.generate_auth_url(state)

        message = (
            "🔐 <b>Google Authentication Required</b>\n\n"
            f"Please <a href='{auth_url}'>click here to authorize</a> access to your Google account.\n\n"
            "<b>This will enable:</b>\n"
            "• Calendar event notifications\n"
            "• Email monitoring and filtering\n"
            "• Smart briefing generation\n"
            "• Trip and event reminders\n\n"
            "You'll receive a confirmation message once the authentication is completed."
        )
        keyboard = [
            [InlineKeyboardButton("🔗 Open Auth Link", url=auth_url)],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_settings")],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def show_email_filters_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the email filters menu."""
    query = update.callback_query
    if not query:
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "📋 List Ignored Patterns", callback_data="email_filters_list"
            )
        ],
        [InlineKeyboardButton("➕ Add New Pattern", callback_data="email_filters_add")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = "📧 <b>Email Filters</b>\n\nManage your email notification filters:"

    await query.edit_message_text(
        message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def show_ignored_emails_from_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show ignored email patterns from the menu."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(query.from_user.id)
    if not user:
        await query.edit_message_text(
            "❌ User not found. Please use /start to register."
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
            "📧 <b>Email Ignore Patterns</b>\n\n"
            "<b>No patterns currently ignored.</b>\n\n"
            "Use the 'Add New Pattern' option to add patterns to ignore."
        )
    else:
        message = (
            "📧 <b>Email Ignore Patterns</b>\n\n"
            f"<b>Currently ignoring {len(ignored)} pattern(s):</b>\n"
        )
        for i, pattern in enumerate(ignored, 1):
            escaped_pattern = (
                pattern.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            message += f"{i}. <code>{escaped_pattern}</code>\n"

    keyboard = [
        [InlineKeyboardButton("➕ Add New Pattern", callback_data="email_filters_add")],
        [
            InlineKeyboardButton(
                "🔙 Back to Email Filters", callback_data="settings_email_filters"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def prompt_add_email_filter(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Prompt user to add an email filter pattern."""
    query = update.callback_query
    if not query:
        return

    message = (
        "📧 <b>Add Email Filter Pattern</b>\n\n"
        "Please send me the email pattern you want to ignore.\n\n"
        "<b>Examples:</b>\n"
        "• <code>noreply@example.com</code> - Ignore specific email\n"
        "• <code>@spam.com</code> - Ignore entire domain\n"
        "• <code>newsletter</code> - Ignore emails containing 'newsletter'\n\n"
        "Send your pattern as a regular message, or use /cancel to abort."
    )

    keyboard = [
        [InlineKeyboardButton("❌ Cancel", callback_data="settings_email_filters")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )

    # Store state for handling the next message
    user_data = cast(dict[str, Any], context.user_data)
    user_data["awaiting_email_pattern"] = True


async def handle_setting_modification(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle modification of a specific setting."""
    query = update.callback_query
    if not query or not query.data:
        return

    setting_key_str = query.data.replace("modify_", "")
    try:
        setting_key = SettingKey(setting_key_str)
    except ValueError:
        await query.edit_message_text("❌ Invalid setting key.")
        return

    # Get the human-readable label for this setting
    label = None
    for human_label, key in SETTINGS_LABEL_MAP.items():
        if key == setting_key:
            label = human_label
            break

    if not label:
        label = setting_key.value.replace("_", " ").title()

    description = SETTINGS_DESCRIPTIONS.get(setting_key, "")

    message = (
        f"✏️ <b>Modify: {label}</b>\n\n"
        f"<b>Description:</b> {description}\n\n"
        "Please send me the new value as a regular message, or use /cancel to abort."
    )

    # Add specific instructions for certain settings
    if setting_key == SettingKey.GREET:
        message += (
            "\n<b>Options:</b>\n"
            "• <code>first_name</code> - Use your first name\n"
            "• <code>username</code> - Use your username\n"
            "• Any custom text you prefer"
        )
    elif setting_key == SettingKey.BRIEFING_TIME:
        message += (
            "\n<b>Format:</b> HH:MM (24-hour format)\n"
            "<b>Example:</b> <code>08:30</code> for 8:30 AM"
        )

    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="back_to_settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )

    # Store state for handling the next message
    user_data = cast(dict[str, Any], context.user_data)
    user_data["awaiting_setting_value"] = setting_key
    user_data["setting_label"] = label


async def show_settings_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Show the main settings menu."""
    query = update.callback_query
    if not query:
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "📋 Show Current Settings", callback_data="settings_show"
            )
        ],
        [InlineKeyboardButton("✏️ Modify Settings", callback_data="settings_modify")],
        [
            InlineKeyboardButton(
                "🔐 Google Authentication", callback_data="settings_google_auth"
            )
        ],
        [
            InlineKeyboardButton(
                "📧 Email Filters", callback_data="settings_email_filters"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    settings_message = (
        "⚙️ <b>Settings Menu</b>\n\n"
        "Choose an option below to view or modify your settings:"
    )

    await query.edit_message_text(
        settings_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def handle_settings_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle user input for settings modification.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    if not update.message or not update.effective_user:
        return

    user_data = cast(dict[str, Any], context.user_data)

    # Check if user is providing a setting value
    if "awaiting_setting_value" in user_data:
        await process_setting_value(update, context)
        return

    # Check if user is providing an email pattern
    if user_data.get("awaiting_email_pattern"):
        await process_email_pattern(update, context)
        return


async def process_setting_value(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Process a new setting value from the user."""
    if not update.message or not update.effective_user:
        return

    user_data = cast(dict[str, Any], context.user_data)
    setting_key = user_data.get("awaiting_setting_value")
    setting_label = user_data.get("setting_label", "Setting")

    if not isinstance(setting_key, SettingKey):
        return

    if not update.message.text:
        await update.message.reply_text(
            "❌ Please provide a valid value or use /cancel to abort."
        )
        return

    value = update.message.text.strip()
    if not value:
        await update.message.reply_text(
            "❌ Please provide a valid value or use /cancel to abort."
        )
        return

    # Validate specific settings
    if setting_key == SettingKey.BRIEFING_TIME:
        import re

        if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", value):
            await update.message.reply_text(
                "❌ Invalid time format. Please use HH:MM format (e.g., 08:30)."
            )
            return

    # Save the setting
    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ User not found. Please use /start to register."
        )
        return

    # Handle special case for greet setting
    if setting_key == SettingKey.GREET and not value:
        value = "first_name"

    await user_service.set_setting(user.id, setting_key, value)

    # Clear the awaiting state
    user_data.pop("awaiting_setting_value", None)
    user_data.pop("setting_label", None)

    # Send confirmation with menu to go back
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_to_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ <b>{setting_label}</b> updated to: <code>{value}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )

    logger.info(f"Updated {setting_key.value} to '{value}' for user {user.id}")


async def process_email_pattern(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Process a new email pattern from the user."""
    if not update.message or not update.effective_user:
        return

    user_data = cast(dict[str, Any], context.user_data)
    if not update.message.text:
        await update.message.reply_text(
            "❌ Please provide a valid email pattern or use /cancel to abort."
        )
        return

    pattern = update.message.text.strip()

    if not pattern:
        await update.message.reply_text(
            "❌ Please provide a valid email pattern or use /cancel to abort."
        )
        return

    user_service = get_user_service()
    user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)
    if not user:
        await update.message.reply_text(
            "❌ User not found. Please use /start to register."
        )
        return

    ignored = (
        cast(
            list[str] | None,
            await user_service.get_setting(user.id, SettingKey.IGNORE_EMAILS),
        )
        or []
    )

    if pattern in ignored:
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 Back to Email Filters", callback_data="settings_email_filters"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📧 Pattern <code>{pattern}</code> is already in your ignore list.",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        user_data.pop("awaiting_email_pattern", None)
        return

    ignored.append(pattern)
    await user_service.set_setting(user.id, SettingKey.IGNORE_EMAILS, ignored)

    # Clear the awaiting state
    user_data.pop("awaiting_email_pattern", None)

    # Send confirmation with menu to go back
    keyboard = [
        [
            InlineKeyboardButton(
                "🔙 Back to Email Filters", callback_data="settings_email_filters"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Added <code>{pattern}</code> to your email ignore list.\n\n"
        f"Emails matching this pattern will no longer trigger notifications.",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
    )

    logger.info(f"Added email pattern '{pattern}' for user {user.id}")


async def handle_cancel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /cancel command for menu-based operations.

    Args:
        update: The update object from Telegram.
        context: The context object from Telegram.
    """
    if not update.message or not update.effective_user:
        return

    user_data = cast(dict[str, Any], context.user_data)

    # Clear any awaiting states
    was_awaiting = user_data.pop("awaiting_setting_value", None) or user_data.pop(
        "awaiting_email_pattern", None
    )
    user_data.pop("setting_label", None)

    if was_awaiting:
        # Show settings menu if user was in the middle of an operation
        keyboard = [
            [InlineKeyboardButton("⚙️ Settings Menu", callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "❌ Operation cancelled.", reply_markup=reply_markup
        )
        logger.info(f"Cancelled settings operation for user {update.effective_user.id}")
    else:
        await update.message.reply_text("Nothing to cancel.")
