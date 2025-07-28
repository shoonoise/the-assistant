"""Persistent keyboard management system for Telegram bot.

This module provides the PersistentKeyboardManager class that creates and manages
the persistent reply keyboard with essential commands for quick access.
"""

import logging

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


# Keyboard button to command mapping dictionary
KEYBOARD_COMMAND_MAP: dict[str, str] = {
    "📊 Briefing": "briefing",
    "📅 Schedule Task": "add_task",
    "⏰ Add Countdown": "add_countdown",
    "📈 Track Habit": "track_habit",
    "🧠 Memories": "memory",
    "⚙️ Settings": "update_settings",
}


class PersistentKeyboardManager:
    """Manages the persistent reply keyboard for quick access to essential commands.

    This class provides methods to create and manage the persistent keyboard that
    appears at the bottom of the chat for quick access to main features.
    """

    def __init__(self):
        """Initialize the persistent keyboard manager."""
        self._keyboard_layout = [
            ["📊 Briefing", "📅 Schedule Task"],
            ["⏰ Add Countdown", "📈 Track Habit"],
            ["🧠 Memories", "⚙️ Settings"],
        ]

    def create_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Create the main persistent keyboard with essential commands.

        Returns:
            ReplyKeyboardMarkup: The configured persistent keyboard
        """
        return ReplyKeyboardMarkup(
            self._keyboard_layout,
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Choose an option or type a command...",
        )

    async def send_with_keyboard(
        self, update: Update, text: str, parse_mode: str = ParseMode.HTML
    ) -> None:
        """Send message with persistent keyboard attached.

        Args:
            update: The update object from Telegram
            text: The message text to send
            parse_mode: The parse mode to use for the message
        """
        if not update.message:
            logger.warning("Cannot send message with keyboard: no message in update")
            return

        try:
            await update.message.reply_text(
                text, reply_markup=self.create_main_keyboard(), parse_mode=parse_mode
            )
            logger.debug("Sent message with persistent keyboard")
        except Exception as e:
            logger.error(f"Failed to send message with keyboard: {e}")
            # Fallback: send message without keyboard
            try:
                await update.message.reply_text(text, parse_mode=parse_mode)
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback message: {fallback_error}")

    async def handle_keyboard_button(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> str | None:
        """Handle keyboard button presses and return the corresponding command.

        Args:
            update: The update object from Telegram
            context: The context object from Telegram

        Returns:
            The command name corresponding to the button, or None if not a keyboard button
        """
        if not update.message or not update.message.text:
            return None

        button_text = update.message.text.strip()
        command = KEYBOARD_COMMAND_MAP.get(button_text)

        if command:
            logger.info(
                f"Keyboard button '{button_text}' pressed, mapping to command: {command}"
            )
            return command

        return None

    def get_keyboard_buttons(self) -> list[str]:
        """Get list of all keyboard button texts.

        Returns:
            List of button texts in the keyboard
        """
        buttons = []
        for row in self._keyboard_layout:
            buttons.extend(row)
        return buttons

    def get_command_for_button(self, button_text: str) -> str | None:
        """Get the command name for a specific button text.

        Args:
            button_text: The text of the keyboard button

        Returns:
            The corresponding command name, or None if not found
        """
        return KEYBOARD_COMMAND_MAP.get(button_text)

    def is_keyboard_button(self, text: str) -> bool:
        """Check if the given text is a keyboard button.

        Args:
            text: The text to check

        Returns:
            True if the text is a keyboard button, False otherwise
        """
        return text.strip() in KEYBOARD_COMMAND_MAP

    async def send_keyboard_only(self, update: Update) -> None:
        """Send just the keyboard without any message text.

        This is useful for initializing the keyboard or refreshing it.

        Args:
            update: The update object from Telegram
        """
        if not update.message:
            logger.warning("Cannot send keyboard: no message in update")
            return

        try:
            await update.message.reply_text(
                "🎛️ Keyboard ready! Use the buttons below or type commands directly.",
                reply_markup=self.create_main_keyboard(),
                parse_mode=ParseMode.HTML,
            )
            logger.debug("Sent keyboard initialization message")
        except Exception as e:
            logger.error(f"Failed to send keyboard initialization: {e}")


_keyboard_manager: PersistentKeyboardManager | None = None


def get_keyboard_manager() -> PersistentKeyboardManager:
    """Return a shared instance of the persistent keyboard manager."""
    global _keyboard_manager
    if _keyboard_manager is None:
        _keyboard_manager = PersistentKeyboardManager()
    return _keyboard_manager


async def reply_with_keyboard(
    update: Update, text: str, parse_mode: str = ParseMode.HTML
) -> None:
    """Convenience helper to send a message with the persistent keyboard."""
    await get_keyboard_manager().send_with_keyboard(update, text, parse_mode)
