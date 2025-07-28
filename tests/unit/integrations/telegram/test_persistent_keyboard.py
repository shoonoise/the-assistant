"""Tests for the persistent keyboard management system."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from telegram import ReplyKeyboardMarkup, Update, Message
from telegram.constants import ParseMode

from the_assistant.integrations.telegram.persistent_keyboard import (
    PersistentKeyboardManager,
    KEYBOARD_COMMAND_MAP,
)


class TestPersistentKeyboardManager:
    """Test cases for PersistentKeyboardManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.keyboard_manager = PersistentKeyboardManager()

    def test_create_main_keyboard(self):
        """Test that main keyboard is created with correct layout."""
        keyboard = self.keyboard_manager.create_main_keyboard()

        assert isinstance(keyboard, ReplyKeyboardMarkup)
        assert keyboard.resize_keyboard is True
        assert keyboard.one_time_keyboard is False
        assert (
            keyboard.input_field_placeholder == "Choose an option or type a command..."
        )

        # Check keyboard layout - extract text from KeyboardButton objects
        keyboard_texts = []
        for row in keyboard.keyboard:
            row_texts = []
            for button in row:
                row_texts.append(button.text)
            keyboard_texts.append(row_texts)

        expected_layout = [
            ["📊 Briefing", "📅 Schedule Task"],
            ["⏰ Add Countdown", "📈 Track Habit"],
            ["🧠 Memories", "⚙️ Settings"],
        ]
        assert keyboard_texts == expected_layout

    def test_get_keyboard_buttons(self):
        """Test getting all keyboard button texts."""
        buttons = self.keyboard_manager.get_keyboard_buttons()

        expected_buttons = [
            "📊 Briefing",
            "📅 Schedule Task",
            "⏰ Add Countdown",
            "📈 Track Habit",
            "🧠 Memories",
            "⚙️ Settings",
        ]
        assert buttons == expected_buttons

    def test_get_command_for_button(self):
        """Test getting command for specific button text."""
        assert self.keyboard_manager.get_command_for_button("📊 Briefing") == "briefing"
        assert (
            self.keyboard_manager.get_command_for_button("📅 Schedule Task")
            == "add_task"
        )
        assert (
            self.keyboard_manager.get_command_for_button("⏰ Add Countdown")
            == "add_countdown"
        )
        assert (
            self.keyboard_manager.get_command_for_button("📈 Track Habit")
            == "track_habit"
        )
        assert self.keyboard_manager.get_command_for_button("🧠 Memories") == "memory"
        assert (
            self.keyboard_manager.get_command_for_button("⚙️ Settings")
            == "update_settings"
        )
        assert self.keyboard_manager.get_command_for_button("Unknown Button") is None

    def test_is_keyboard_button(self):
        """Test checking if text is a keyboard button."""
        assert self.keyboard_manager.is_keyboard_button("📊 Briefing") is True
        assert self.keyboard_manager.is_keyboard_button("📅 Schedule Task") is True
        assert (
            self.keyboard_manager.is_keyboard_button("  ⏰ Add Countdown  ") is True
        )  # with whitespace
        assert self.keyboard_manager.is_keyboard_button("Unknown Button") is False
        assert self.keyboard_manager.is_keyboard_button("") is False

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_valid(self):
        """Test handling valid keyboard button press."""
        # Create mock update with message
        update = MagicMock(spec=Update)
        message = MagicMock(spec=Message)
        message.text = "📊 Briefing"
        update.message = message

        context = MagicMock()

        command = await self.keyboard_manager.handle_keyboard_button(update, context)
        assert command == "briefing"

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_invalid(self):
        """Test handling invalid keyboard button press."""
        # Create mock update with message
        update = MagicMock(spec=Update)
        message = MagicMock(spec=Message)
        message.text = "Unknown Button"
        update.message = message

        context = MagicMock()

        command = await self.keyboard_manager.handle_keyboard_button(update, context)
        assert command is None

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_no_message(self):
        """Test handling keyboard button when no message in update."""
        update = MagicMock(spec=Update)
        update.message = None

        context = MagicMock()

        command = await self.keyboard_manager.handle_keyboard_button(update, context)
        assert command is None

    @pytest.mark.asyncio
    async def test_send_with_keyboard_success(self):
        """Test sending message with keyboard successfully."""
        # Create mock update with message
        update = MagicMock(spec=Update)
        message = AsyncMock(spec=Message)
        update.message = message

        await self.keyboard_manager.send_with_keyboard(update, "Test message")

        # Verify reply_text was called with correct parameters
        message.reply_text.assert_called_once()
        call_args = message.reply_text.call_args

        assert call_args[0][0] == "Test message"  # First positional argument
        assert call_args[1]["parse_mode"] == ParseMode.HTML
        assert isinstance(call_args[1]["reply_markup"], ReplyKeyboardMarkup)

    @pytest.mark.asyncio
    async def test_send_with_keyboard_no_message(self):
        """Test sending message with keyboard when no message in update."""
        update = MagicMock(spec=Update)
        update.message = None

        # Should not raise exception
        await self.keyboard_manager.send_with_keyboard(update, "Test message")

    @pytest.mark.asyncio
    async def test_send_keyboard_only_success(self):
        """Test sending keyboard initialization message."""
        # Create mock update with message
        update = MagicMock(spec=Update)
        message = AsyncMock(spec=Message)
        update.message = message

        await self.keyboard_manager.send_keyboard_only(update)

        # Verify reply_text was called
        message.reply_text.assert_called_once()
        call_args = message.reply_text.call_args

        assert "Keyboard ready!" in call_args[0][0]
        assert call_args[1]["parse_mode"] == ParseMode.HTML
        assert isinstance(call_args[1]["reply_markup"], ReplyKeyboardMarkup)


class TestKeyboardCommandMap:
    """Test cases for KEYBOARD_COMMAND_MAP constant."""

    def test_keyboard_command_map_completeness(self):
        """Test that all required buttons are in the command map."""
        required_buttons = [
            "📊 Briefing",
            "📅 Schedule Task",
            "⏰ Add Countdown",
            "📈 Track Habit",
            "🧠 Memories",
            "⚙️ Settings",
        ]

        for button in required_buttons:
            assert button in KEYBOARD_COMMAND_MAP, (
                f"Button '{button}' missing from KEYBOARD_COMMAND_MAP"
            )

    def test_keyboard_command_map_values(self):
        """Test that command map has correct command values."""
        expected_mappings = {
            "📊 Briefing": "briefing",
            "📅 Schedule Task": "add_task",
            "⏰ Add Countdown": "add_countdown",
            "📈 Track Habit": "track_habit",
            "🧠 Memories": "memory",
            "⚙️ Settings": "update_settings",
        }

        for button, expected_command in expected_mappings.items():
            assert KEYBOARD_COMMAND_MAP[button] == expected_command
