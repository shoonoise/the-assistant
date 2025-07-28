import logging
from typing import Any, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from .constants import SETTINGS_LABEL_LOOKUP, SettingKey

logger = logging.getLogger(__name__)


class SettingsInterfaceManager:
    """Manages inline keyboard-based settings interface."""

    def __init__(self) -> None:
        self._keyboard = [
            [InlineKeyboardButton("👋 How to greet", callback_data="setting:greet")],
            [
                InlineKeyboardButton(
                    "⏰ Briefing time", callback_data="setting:briefing_time"
                )
            ],
            [InlineKeyboardButton("👤 About me", callback_data="setting:about_me")],
            [InlineKeyboardButton("📍 Location", callback_data="setting:location")],
            [InlineKeyboardButton("❌ Cancel", callback_data="setting:cancel")],
        ]

    def create_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Create inline keyboard for settings selection."""
        return InlineKeyboardMarkup(self._keyboard)

    async def handle_setting_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard button presses for settings."""
        query = update.callback_query
        if query is None or query.data is None:
            return

        await query.answer()
        _, key = query.data.split(":", 1)

        if key == "cancel":
            await query.edit_message_text("Settings cancelled.")
            cast(dict[str, Any], context.user_data).pop("pending_setting", None)
            return

        cast(dict[str, Any], context.user_data)["pending_setting"] = key
        label = SETTINGS_LABEL_LOOKUP.get(SettingKey(key), key)
        await query.edit_message_text(f"Enter new value for {label}:")
