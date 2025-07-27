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
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationBuilder,
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

from .constants import SETTINGS_LABEL_MAP, ConversationState, SettingKey

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

        # Create a helpful error message with command descriptions
        error_message = (
            f"❓ Sorry, I don't understand the command `{command}`.\n\n"
            "**Available commands:**\n"
        )

        # Add each available command with its description
        for cmd, description in COMMAND_REGISTRY.items():
            if cmd in self._command_handlers:
                error_message += f"• /{cmd} - {description}\n"

        error_message += (
            "\n💡 **Tips:**\n"
            "• Use the command menu (/) to see all commands\n"
            "• Type /help for detailed information\n"
            "• Commands support autocompletion"
        )

        # Send the error message with markdown formatting
        await update.message.reply_text(error_message, parse_mode=ParseMode.MARKDOWN)

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
        "Use /help to see all available commands or /settings to manage your preferences."
    )

    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
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

    # Build help message from command registry
    help_message = "📚 **Available Commands**\n\n"

    # Add each command with its description
    for command, description in COMMAND_REGISTRY.items():
        help_message += f"/{command} - {description}\n"

    help_message += (
        "\n**Automatic Features:**\n"
        "• Morning briefings with your daily schedule\n"
        "• Reminders about upcoming trips\n"
        "• Important task deadlines\n"
        "• Smart email filtering and notifications\n\n"
        "**Tips:**\n"
        "• Use the command menu (/) to see all available commands\n"
        "• Commands support autocompletion in most Telegram clients\n"
        "• Use /settings to customize your experience\n\n"
        "If you have any issues or questions, please contact your system administrator."
    )

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)
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

    settings_message = (
        "⚙️ **Your Settings**\n\n"
        "**User Information:**\n"
        f"• User ID: `{user.id}`\n"
        f"• Name: {user.first_name or 'Not set'}\n"
        f"• Username: {username_display}\n"
        f"• Registered: {registered_display}\n\n"
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

    await update.message.reply_text(settings_message, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Sent comprehensive settings to user {user_id}")


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
            "**Connected Services:**\n"
            "• Google Calendar\n"
            "• Gmail\n"
            "• Google Drive (if needed)\n\n"
            "Your Google integration is working properly!"
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
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
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
            "📧 **Email Ignore Patterns**\n\n"
            "**Usage:** `/ignore\\_email <pattern>`\n\n"
            "**Examples:**\n"
            "• `/ignore\\_email noreply@example\\.com` \\- Ignore specific email\n"
            "• `/ignore\\_email @spam\\.com` \\- Ignore entire domain\n"
            "• `/ignore\\_email newsletter` \\- Ignore emails containing 'newsletter'\n\n"
            "**Other Commands:**\n"
            "• `/list\\_ignored` \\- View all ignored patterns\n"
            "• `/settings` \\- View your current settings"
        )

        await update.message.reply_text(usage_message, parse_mode=ParseMode.MARKDOWN)
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
            f"📧 Pattern `{mask}` is already in your ignore list\\.\n\n"
            f"Use `/list\\_ignored` to see all ignored patterns\\."
        )
        return

    ignored.append(mask)
    await user_service.set_setting(user.id, SettingKey.IGNORE_EMAILS, ignored)

    await update.message.reply_text(
        f"✅ Added `{mask}` to your email ignore list\\.\n\n"
        f"Emails matching this pattern will no longer trigger notifications\\.\n"
        f"Use `/list\\_ignored` to see all ignored patterns\\."
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

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


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
    message = "🧠 **Your memories:**\n\n"
    for i, (_, mem) in enumerate(items, 1):
        txt = mem.get("user_input", "")
        # Use plain text instead of markdown for user content to avoid parsing issues
        message += f"{i}. {txt}\n"
    message += "\nUse /memory_delete <id> to delete a memory."
    await update.message.reply_text(message)


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

    await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)


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
    await client.register_command_handler("google_auth", handle_google_auth_command)
    await client.register_command_handler("ignore_email", handle_ignore_email_command)
    await client.register_command_handler("list_ignored", handle_list_ignored_command)
    await client.register_command_handler("status", handle_status_command)
    await client.register_command_handler("memory_add", handle_memory_add_command)
    await client.register_command_handler("memory", handle_memory_command)
    await client.register_command_handler("memories", handle_memory_command)
    await client.register_command_handler("add_task", handle_add_task_command)
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
