"""Tests for Telegram activities."""

from unittest.mock import AsyncMock, patch

import pytest

from the_assistant.activities.telegram_activities import (
    SendFormattedMessageInput,
    SendMessageInput,
    send_formatted_message,
    send_message,
)


class TestTelegramActivities:
    """Test Telegram messaging activities."""

    @pytest.fixture
    def mock_telegram_client(self):
        """Mock Telegram client."""
        client = AsyncMock()
        client.send_message.return_value = True
        client.validate_credentials.return_value = True
        return client

    @patch("the_assistant.activities.telegram_activities.get_telegram_token")
    @patch("the_assistant.activities.telegram_activities.TelegramClient")
    async def test_send_message_success(
        self, mock_telegram_client_class, mock_get_token, mock_telegram_client
    ):
        """Test successful message sending."""
        mock_get_token.return_value = "test_token"
        mock_telegram_client_class.return_value = mock_telegram_client

        input_data = SendMessageInput(
            user_id=1, chat_id=123456789, text="Test message", parse_mode="Markdown"
        )

        result = await send_message(input_data)

        assert result is True
        mock_telegram_client_class.assert_called_once_with("test_token", user_id=1)
        mock_telegram_client.send_message.assert_called_once_with(
            chat_id=123456789, text="Test message", parse_mode="Markdown"
        )

    @patch("the_assistant.activities.telegram_activities.get_telegram_token")
    @patch("the_assistant.activities.telegram_activities.TelegramClient")
    async def test_send_message_default_parse_mode(
        self, mock_telegram_client_class, mock_get_token, mock_telegram_client
    ):
        """Test message sending with default parse mode."""
        mock_get_token.return_value = "test_token"
        mock_telegram_client_class.return_value = mock_telegram_client

        input_data = SendMessageInput(user_id=1, chat_id=123456789, text="Test message")

        result = await send_message(input_data)

        assert result is True
        mock_telegram_client.send_message.assert_called_once_with(
            chat_id=123456789, text="Test message", parse_mode="Markdown"
        )

    @patch("the_assistant.activities.telegram_activities.send_message")
    async def test_send_formatted_message_markdown(self, mock_send_message):
        """Test sending formatted message with Markdown."""
        mock_send_message.return_value = True

        input_data = SendFormattedMessageInput(
            user_id=1,
            chat_id=123456789,
            title="Test Title",
            content="Test content",
            parse_mode="Markdown",
        )

        result = await send_formatted_message(input_data)

        assert result is True
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args
        assert call_args[0][0].user_id == 1
        assert call_args[0][0].chat_id == 123456789
        assert call_args[0][0].text == "**Test Title**\n\nTest content"
        assert call_args[0][0].parse_mode == "Markdown"

    @patch("the_assistant.activities.telegram_activities.send_message")
    async def test_send_formatted_message_html(self, mock_send_message):
        """Test sending formatted message with HTML."""
        mock_send_message.return_value = True

        input_data = SendFormattedMessageInput(
            user_id=1,
            chat_id=123456789,
            title="Test Title",
            content="Test content",
            parse_mode="HTML",
        )

        result = await send_formatted_message(input_data)

        assert result is True
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args
        assert call_args[0][0].user_id == 1
        assert call_args[0][0].chat_id == 123456789
        assert call_args[0][0].text == "<b>Test Title</b>\n\nTest content"
        assert call_args[0][0].parse_mode == "HTML"

    @patch("the_assistant.activities.telegram_activities.send_message")
    async def test_send_formatted_message_plain_text(self, mock_send_message):
        """Test sending formatted message with plain text."""
        mock_send_message.return_value = True

        input_data = SendFormattedMessageInput(
            user_id=1,
            chat_id=123456789,
            title="Test Title",
            content="Test content",
            parse_mode="None",
        )

        result = await send_formatted_message(input_data)

        assert result is True
        mock_send_message.assert_called_once()
        call_args = mock_send_message.call_args
        assert call_args[0][0].user_id == 1
        assert call_args[0][0].chat_id == 123456789
        assert call_args[0][0].text == "Test Title\n\nTest content"
        assert call_args[0][0].parse_mode == "None"
