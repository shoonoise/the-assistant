"""Enhanced command handler infrastructure for Telegram bot.

This module provides flexible command handlers that support both inline arguments
and dialog-based input, along with validation and error handling capabilities.
"""

import html
import logging
from abc import ABC, abstractmethod
from typing import Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from the_assistant.integrations.telegram.persistent_keyboard import (
    PersistentKeyboardManager,
)
from the_assistant.integrations.telegram.telegram_client import get_user_service

logger = logging.getLogger(__name__)


class FlexibleCommandHandler(ABC):
    """Base class for commands supporting both inline and dialog modes.

    This handler provides a dual-mode approach:
    - Direct Mode: Commands with inline arguments are processed immediately
    - Dialog Mode: Commands without arguments trigger interactive prompts
    """

    def __init__(self, command_name: str):
        """Initialize the flexible command handler.

        Args:
            command_name: The name of the command (without leading slash)
        """
        self.command_name = command_name

    async def handle_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle command with flexible argument support.

        This is the main entry point that determines whether to use direct
        or dialog mode based on the presence of arguments.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
        """
        if not update.message or not update.effective_user:
            logger.warning(
                f"Received {self.command_name} command without message or effective_user"
            )
            return

        try:
            # Get command arguments
            args = getattr(context, "args", [])

            if args:
                # Direct mode: process command with provided arguments
                await self.handle_direct_mode(update, context, args)
            else:
                # Dialog mode: start interactive dialog for argument collection
                await self.handle_dialog_mode(update, context)

        except Exception as e:
            await ErrorHandler.handle_command_error(update, e, self.command_name)

    @abstractmethod
    async def handle_direct_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
    ) -> None:
        """Process command with provided arguments.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
            args: List of command arguments
        """
        pass

    @abstractmethod
    async def handle_dialog_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Start interactive dialog for argument collection.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
        """
        pass

    async def _get_user_from_update(self, update: Update) -> Any:
        """Get user from database based on update.

        Args:
            update: The update object from Telegram

        Returns:
            User object from database or None if not found

        Raises:
            ValueError: If user is not registered
        """
        if not update.effective_user:
            raise ValueError("No effective user in update")

        user_service = get_user_service()
        user = await user_service.get_user_by_telegram_chat_id(update.effective_user.id)

        if not user:
            raise ValueError("User not registered. Please use /start to register.")

        return user


class CommandValidator:
    """Validates command arguments and provides helpful feedback."""

    @staticmethod
    async def validate_memory_input(text: str) -> tuple[bool, str]:
        """Validate memory input and return success status with message.

        Args:
            text: The memory text to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if not text.strip():
            return False, "Memory cannot be empty. Please provide some text."

        if len(text) > 500:
            return False, "Memory is too long (max 500 characters)."

        return True, "Memory is valid."

    @staticmethod
    async def validate_task_input(text: str) -> tuple[bool, str]:
        """Validate task instruction input.

        Args:
            text: The task instruction to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if not text.strip():
            return False, "Task instruction cannot be empty."

        if len(text) > 1000:
            return False, "Task instruction is too long (max 1000 characters)."

        return True, "Task instruction is valid."

    @staticmethod
    async def validate_countdown_input(text: str) -> tuple[bool, str]:
        """Validate countdown description input.

        Args:
            text: The countdown description to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if not text.strip():
            return False, "Countdown description cannot be empty."

        if len(text) > 500:
            return False, "Countdown description is too long (max 500 characters)."

        return True, "Countdown description is valid."

    @staticmethod
    async def validate_email_pattern(pattern: str) -> tuple[bool, str]:
        """Validate email ignore pattern.

        Args:
            pattern: The email pattern to validate

        Returns:
            Tuple of (is_valid, message)
        """
        if not pattern.strip():
            return False, "Email pattern cannot be empty."

        if len(pattern) > 100:
            return False, "Email pattern is too long (max 100 characters)."

        # Basic validation - pattern should contain some meaningful characters
        if len(pattern.strip()) < 3:
            return False, "Email pattern is too short (min 3 characters)."

        return True, "Email pattern is valid."


class ErrorHandler:
    """Handles errors gracefully with user-friendly messages."""

    @staticmethod
    async def handle_command_error(
        update: Update, error: Exception, command: str
    ) -> None:
        """Handle command execution errors.

        Args:
            update: The update object from Telegram
            error: The exception that occurred
            command: The command name that failed
        """
        logger.error(f"Error in /{command} command: {error}", exc_info=True)

        # Determine error message based on error type
        if isinstance(error, ValueError):
            if "not registered" in str(error):
                error_message = (
                    "❌ You need to register first. Please use /start to register."
                )
            else:
                error_message = f"❌ {error}"
        else:
            error_message = (
                f"❌ Sorry, there was an error processing the /{command} command.\n\n"
                "Please try again or contact support if the problem persists."
            )

        try:
            keyboard_manager = PersistentKeyboardManager()
            await update.message.reply_text(
                error_message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard_manager.create_main_keyboard(),
            )
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")

    @staticmethod
    async def handle_validation_error(
        update: Update, validation_message: str, command: str
    ) -> None:
        """Handle validation errors with helpful feedback.

        Args:
            update: The update object from Telegram
            validation_message: The validation error message
            command: The command name that failed validation
        """
        error_message = (
            f"❌ {validation_message}\n\nPlease try the /{command} command again."
        )

        try:
            keyboard_manager = PersistentKeyboardManager()
            await update.message.reply_text(
                error_message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard_manager.create_main_keyboard(),
            )
        except Exception as send_error:
            logger.error(f"Failed to send validation error message: {send_error}")


class MessageFormatter:
    """Centralized message formatting to avoid parsing issues."""

    @staticmethod
    def format_help_message(command_registry: dict[str, str]) -> str:
        """Format help message using HTML for reliable rendering.

        Args:
            command_registry: Dictionary of commands and their descriptions

        Returns:
            Formatted help message
        """
        commands = []
        for command, description in command_registry.items():
            commands.append(f"/{command} - {html.escape(description)}")

        return (
            "<b>📚 Available Commands</b>\n\n"
            + "\n".join(commands)
            + "\n\n<b>💡 Tips:</b>\n"
            "• Use the keyboard buttons below for quick access\n"
            "• Commands support both inline arguments and dialogs\n"
            "• Type /settings to customize your experience"
        )

    @staticmethod
    def format_user_content(text: str) -> str:
        """Format user-generated content safely.

        Args:
            text: User-generated text content

        Returns:
            Safely formatted text (plain text to avoid parsing issues)
        """
        # Use plain text to avoid parsing issues with user input
        return text

    @staticmethod
    def format_confirmation(action: str, content: str) -> str:
        """Format confirmation messages consistently.

        Args:
            action: The action that was performed
            content: The content that was processed

        Returns:
            Formatted confirmation message
        """
        return f"✅ {action}: {html.escape(content)}"

    @staticmethod
    def format_dialog_prompt(
        command: str, description: str, examples: list[str] | None = None
    ) -> str:
        """Format dialog mode prompts consistently.

        Args:
            command: The command name
            description: Description of what to enter
            examples: Optional list of examples

        Returns:
            Formatted dialog prompt
        """
        message = f"<b>/{command}</b>\n\n{html.escape(description)}"

        if examples:
            message += "\n\n<b>Examples:</b>\n"
            for example in examples:
                message += f"• {html.escape(example)}\n"

        return message
