"""Enhanced command handler implementations using the flexible infrastructure.

This module contains concrete implementations of command handlers that use
the FlexibleCommandHandler base class to support both inline and dialog modes.
"""

import logging
from datetime import UTC, datetime
from typing import Any, cast

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from the_assistant.db import get_user_service
from the_assistant.integrations.telegram.constants import SettingKey
from the_assistant.integrations.telegram.enhanced_handlers import (
    CommandValidator,
    FlexibleCommandHandler,
    MessageFormatter,
)
from the_assistant.integrations.telegram.persistent_keyboard import (
    PersistentKeyboardManager,
)

logger = logging.getLogger(__name__)


class MemoryAddHandler(FlexibleCommandHandler):
    """Enhanced handler for the memory_add command with dual-mode support."""

    def __init__(self):
        super().__init__("memory_add")

    async def handle_direct_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
    ) -> None:
        """Process memory_add command with provided arguments.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
            args: List of command arguments
        """
        keyboard_manager = PersistentKeyboardManager()
        text = " ".join(args).strip()

        # Validate input
        is_valid, validation_message = await CommandValidator.validate_memory_input(
            text
        )
        if not is_valid:
            await keyboard_manager.send_with_keyboard(
                update,
                f"❌ {validation_message}",
                parse_mode=ParseMode.HTML,
            )
            return

        # Get user
        user = await self._get_user_from_update(update)

        # Store memory
        await self._store_memory(user, text)

        # Send confirmation
        confirmation = MessageFormatter.format_confirmation("Memory added", text)
        await keyboard_manager.send_with_keyboard(
            update, confirmation, parse_mode=ParseMode.HTML
        )

    async def handle_dialog_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Start interactive dialog for memory input.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
        """
        # Send descriptive prompt as specified in requirements
        prompt = MessageFormatter.format_dialog_prompt(
            "memory_add",
            "Write anything you want me to remember about you, it will be used during our interaction, e.g. in the briefings",
            [
                "I prefer morning meetings",
                "I'm vegetarian",
                "I live in New York timezone",
            ],
        )

        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            prompt,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

    async def _store_memory(self, user: Any, text: str) -> None:
        """Store memory for the user.

        Args:
            user: User object from database
            text: Memory text to store
        """
        user_service = get_user_service()

        memories = (
            cast(
                dict[str, dict[str, str]] | None,
                await user_service.get_setting(user.id, SettingKey.MEMORIES),
            )
            or {}
        )

        if len(memories) >= 10:
            raise ValueError(
                "You have reached the 10 memories limit. Delete one with /memory_delete <id>."
            )

        key = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
        while key in memories:
            key = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")

        memories[key] = {"user_input": text}
        await user_service.set_setting(user.id, SettingKey.MEMORIES, memories)


class AddTaskHandler(FlexibleCommandHandler):
    """Enhanced handler for the add_task command with dual-mode support."""

    def __init__(self):
        super().__init__("add_task")

    async def handle_direct_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
    ) -> None:
        """Process add_task command with provided arguments.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
            args: List of command arguments
        """
        keyboard_manager = PersistentKeyboardManager()
        raw_instruction = " ".join(args).strip()

        # Validate input
        is_valid, validation_message = await CommandValidator.validate_task_input(
            raw_instruction
        )
        if not is_valid:
            await keyboard_manager.send_with_keyboard(
                update,
                f"❌ {validation_message}",
                parse_mode=ParseMode.HTML,
            )
            return

        # Get user
        user = await self._get_user_from_update(update)

        # Process and store task
        await self._process_and_store_task(user, raw_instruction)

        # Send confirmation
        confirmation = MessageFormatter.format_confirmation(
            "Task added", raw_instruction
        )
        await keyboard_manager.send_with_keyboard(
            update, confirmation, parse_mode=ParseMode.HTML
        )

    async def handle_dialog_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Start interactive dialog for task input.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
        """
        # Set conversation state for dialog mode
        cast(dict[str, Any], context.user_data)["conversation_state"] = "TASK_INPUT"

        # Send helpful prompt with examples
        prompt = MessageFormatter.format_dialog_prompt(
            "add_task",
            "Enter a task instruction with schedule information:",
            [
                "every day at 6pm say hi",
                "remind me to call mom every Sunday at 2pm",
                "weekly team meeting reminder on Mondays at 9am",
            ],
        )

        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            prompt,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

    async def _process_and_store_task(self, user: Any, raw_instruction: str) -> None:
        """Process and store task for the user.

        Args:
            user: User object from database
            raw_instruction: Raw task instruction
        """
        from the_assistant.integrations.llm import TaskParser

        user_service = get_user_service()
        parser = TaskParser()
        schedule, instruction = await parser.parse(raw_instruction)

        if not schedule:
            raise ValueError(
                "Could not parse a schedule. Try something like 'every day at 6pm say hi'."
            )

        await user_service.create_task(
            user.id, raw_instruction, schedule=schedule, instruction=instruction
        )


class AddCountdownHandler(FlexibleCommandHandler):
    """Enhanced handler for the add_countdown command with dual-mode support."""

    def __init__(self):
        super().__init__("add_countdown")

    async def handle_direct_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
    ) -> None:
        """Process add_countdown command with provided arguments.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
            args: List of command arguments
        """
        keyboard_manager = PersistentKeyboardManager()
        raw_text = " ".join(args).strip()

        # Validate input
        is_valid, validation_message = await CommandValidator.validate_countdown_input(
            raw_text
        )
        if not is_valid:
            await keyboard_manager.send_with_keyboard(
                update,
                f"❌ {validation_message}",
                parse_mode=ParseMode.HTML,
            )
            return

        # Get user
        user = await self._get_user_from_update(update)

        # Process and store countdown
        await self._process_and_store_countdown(user, raw_text)

        # Send confirmation
        confirmation = MessageFormatter.format_confirmation("Countdown added", raw_text)
        await keyboard_manager.send_with_keyboard(
            update, confirmation, parse_mode=ParseMode.HTML
        )

    async def handle_dialog_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Start interactive dialog for countdown input.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
        """
        # Set conversation state for dialog mode
        cast(dict[str, Any], context.user_data)["conversation_state"] = (
            "COUNTDOWN_INPUT"
        )

        # Send descriptive prompt with examples
        prompt = MessageFormatter.format_dialog_prompt(
            "add_countdown",
            "Enter a countdown description with date information:",
            [
                "my birthday on 2025-05-01",
                "vacation starts on 2025-07-15",
                "project deadline on 2025-03-30",
            ],
        )

        keyboard_manager = PersistentKeyboardManager()
        await update.message.reply_text(
            prompt,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_manager.create_main_keyboard(),
        )

    async def _process_and_store_countdown(self, user: Any, raw_text: str) -> None:
        """Process and store countdown for the user.

        Args:
            user: User object from database
            raw_text: Raw countdown description
        """
        from the_assistant.integrations.llm import CountdownParser

        user_service = get_user_service()
        parser = CountdownParser()
        event_time, description = await parser.parse(raw_text)

        if event_time is None:
            raise ValueError("Could not parse a date. Try 'my birthday on 2025-05-01'.")

        await user_service.create_countdown(
            user.id, description=description, event_time=event_time
        )


class IgnoreEmailHandler(FlexibleCommandHandler):
    """Enhanced handler for the ignore_email command with dual-mode support."""

    def __init__(self):
        super().__init__("ignore_email")

    async def handle_direct_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, args: list[str]
    ) -> None:
        """Process ignore_email command with provided arguments.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
            args: List of command arguments
        """
        keyboard_manager = PersistentKeyboardManager()
        pattern = args[0].strip() if args else ""

        # Validate input
        is_valid, validation_message = await CommandValidator.validate_email_pattern(
            pattern
        )
        if not is_valid:
            await keyboard_manager.send_with_keyboard(
                update,
                f"❌ {validation_message}",
                parse_mode=ParseMode.HTML,
            )
            return

        # Get user
        user = await self._get_user_from_update(update)

        # Store email pattern
        await self._store_email_pattern(user, pattern)

        # Send confirmation
        confirmation = (
            f"✅ Added <code>{pattern}</code> to your email ignore list.\n\n"
            "Emails matching this pattern will no longer trigger notifications.\n"
            "Use /list_ignored to see all ignored patterns."
        )
        await keyboard_manager.send_with_keyboard(
            update, confirmation, parse_mode=ParseMode.HTML
        )

    async def handle_dialog_mode(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Show usage information when no arguments provided.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram
        """
        # For ignore_email, we show usage information instead of starting a dialog
        usage_message = (
            "<b>📧 Email Ignore Patterns</b>\n\n"
            "<b>Usage:</b> <code>/ignore_email &lt;pattern&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/ignore_email noreply@example.com</code> - Ignore specific email\n"
            "• <code>/ignore_email @spam.com</code> - Ignore entire domain\n"
            "• <code>/ignore_email newsletter</code> - Ignore emails containing 'newsletter'\n\n"
            "<b>Other Commands:</b>\n"
            "• <code>/list_ignored</code> - View all ignored patterns\n"
            "• <code>/settings</code> - View your current settings"
        )

        keyboard_manager = PersistentKeyboardManager()
        await keyboard_manager.send_with_keyboard(
            update, usage_message, parse_mode=ParseMode.HTML
        )

    async def _store_email_pattern(self, user: Any, pattern: str) -> None:
        """Store email ignore pattern for the user.

        Args:
            user: User object from database
            pattern: Email pattern to ignore
        """
        user_service = get_user_service()

        ignored = (
            cast(
                list[str] | None,
                await user_service.get_setting(user.id, SettingKey.IGNORE_EMAILS),
            )
            or []
        )

        if pattern in ignored:
            raise ValueError(
                f"Pattern `{pattern}` is already in your ignore list.\n\nUse /list_ignored to see all ignored patterns."
            )

        ignored.append(pattern)
        await user_service.set_setting(user.id, SettingKey.IGNORE_EMAILS, ignored)
