"""Tests for keyboard button handler functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Message, Update, User
from telegram.ext import ContextTypes

from the_assistant.integrations.telegram.telegram_client import (
    handle_keyboard_button,
)


class TestKeyboardButtonHandler:
    """Test cases for the keyboard button handler."""

    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        update = MagicMock(spec=Update)
        update.message = MagicMock(spec=Message)
        update.effective_user = MagicMock(spec=User)
        update.effective_user.id = 12345
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = []
        return context

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_briefing(self, mock_update, mock_context):
        """Test handling briefing keyboard button."""
        mock_update.message.text = "📊 Briefing"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_briefing_command"
        ) as mock_briefing:
            mock_briefing.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            mock_briefing.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_add_task(self, mock_update, mock_context):
        """Test handling add task keyboard button."""
        mock_update.message.text = "📅 Schedule Task"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_add_task_command"
        ) as mock_add_task:
            mock_add_task.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            mock_add_task.assert_called_once_with(mock_update, mock_context)
            # Verify args are cleared to trigger dialog mode
            assert mock_context.args == []

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_add_countdown(
        self, mock_update, mock_context
    ):
        """Test handling add countdown keyboard button."""
        mock_update.message.text = "⏰ Add Countdown"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_add_countdown_command"
        ) as mock_add_countdown:
            mock_add_countdown.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            mock_add_countdown.assert_called_once_with(mock_update, mock_context)
            # Verify args are cleared to trigger dialog mode
            assert mock_context.args == []

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_track_habit(self, mock_update, mock_context):
        """Test handling track habit keyboard button."""
        mock_update.message.text = "📈 Track Habit"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_track_habit_command"
        ) as mock_track_habit:
            mock_track_habit.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            mock_track_habit.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_memory(self, mock_update, mock_context):
        """Test handling memory keyboard button."""
        mock_update.message.text = "🧠 Memories"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_memory_command"
        ) as mock_memory:
            mock_memory.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            mock_memory.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_settings(self, mock_update, mock_context):
        """Test handling settings keyboard button."""
        mock_update.message.text = "⚙️ Settings"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.start_update_settings"
        ) as mock_settings:
            mock_settings.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            mock_settings.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_not_keyboard_button(
        self, mock_update, mock_context
    ):
        """Test handling regular text that is not a keyboard button."""
        mock_update.message.text = "regular text message"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_briefing_command"
        ) as mock_briefing:
            await handle_keyboard_button(mock_update, mock_context)

            # Should not call any command handlers for regular text
            mock_briefing.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_no_message(self, mock_context):
        """Test handling when there is no message."""
        update = MagicMock(spec=Update)
        update.message = None

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_briefing_command"
        ) as mock_briefing:
            await handle_keyboard_button(update, mock_context)

            # Should not call any command handlers when no message
            mock_briefing.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_no_text(self, mock_update, mock_context):
        """Test handling when message has no text."""
        mock_update.message.text = None

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_briefing_command"
        ) as mock_briefing:
            await handle_keyboard_button(mock_update, mock_context)

            # Should not call any command handlers when no text
            mock_briefing.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_no_effective_user(
        self, mock_update, mock_context
    ):
        """Test handling when there is no effective user."""
        mock_update.message.text = "📊 Briefing"
        mock_update.effective_user = None

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_briefing_command"
        ) as mock_briefing:
            await handle_keyboard_button(mock_update, mock_context)

            # Should not call any command handlers when no effective user
            mock_briefing.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_unknown_command(
        self, mock_update, mock_context
    ):
        """Test handling unknown keyboard button command."""
        mock_update.message.text = "📊 Briefing"  # This will map to "briefing"
        mock_update.message.reply_text = AsyncMock()

        # Mock the keyboard manager to return an unknown command
        with patch(
            "the_assistant.integrations.telegram.telegram_client.PersistentKeyboardManager"
        ) as mock_keyboard_manager:
            mock_manager = mock_keyboard_manager.return_value
            mock_manager.handle_keyboard_button = AsyncMock(
                return_value="unknown_command"
            )

            await handle_keyboard_button(mock_update, mock_context)

            # Should send error message for unknown command
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "not implemented yet" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_keyboard_button_command_error(
        self, mock_update, mock_context
    ):
        """Test handling error in command execution."""
        mock_update.message.text = "📊 Briefing"
        mock_update.message.reply_text = AsyncMock()

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_briefing_command"
        ) as mock_briefing:
            mock_briefing.side_effect = Exception("Test error")

            await handle_keyboard_button(mock_update, mock_context)

            # Should send error message when command fails
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args
            assert "error processing your request" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_keyboard_button_clears_args_for_dialog_commands(
        self, mock_update, mock_context
    ):
        """Test that keyboard buttons clear args to trigger dialog mode for appropriate commands."""
        # Set some initial args
        mock_context.args = ["some", "args"]

        # Test add_task button
        mock_update.message.text = "📅 Schedule Task"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_add_task_command"
        ) as mock_add_task:
            mock_add_task.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            # Args should be cleared to trigger dialog mode
            assert mock_context.args == []
            mock_add_task.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_keyboard_button_preserves_args_for_direct_commands(
        self, mock_update, mock_context
    ):
        """Test that keyboard buttons preserve args for commands that don't need dialog mode."""
        # Set some initial args
        mock_context.args = ["some", "args"]

        # Test briefing button (doesn't need dialog mode)
        mock_update.message.text = "📊 Briefing"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.handle_briefing_command"
        ) as mock_briefing:
            mock_briefing.return_value = None

            await handle_keyboard_button(mock_update, mock_context)

            # Args should be preserved for briefing command
            assert mock_context.args == ["some", "args"]
            mock_briefing.assert_called_once_with(mock_update, mock_context)
