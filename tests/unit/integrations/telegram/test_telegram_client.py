"""Unit tests for the Telegram client."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Bot, Chat, Message, Update, User
from telegram.constants import ParseMode
from telegram.error import (
    BadRequest,
    Forbidden,
    NetworkError,
    RetryAfter,
    TelegramError,
)

from the_assistant.integrations.telegram.telegram_client import TelegramClient


@pytest.fixture
def mock_bot():
    """Create a mock Telegram Bot."""
    mock = AsyncMock(spec=Bot)
    mock.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
    mock.send_message = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def telegram_client(mock_bot):
    """Create a TelegramClient with a mock bot."""
    with (
        patch(
            "the_assistant.integrations.telegram.telegram_client.Bot",
            return_value=mock_bot,
        ),
        patch(
            "the_assistant.integrations.telegram.telegram_client.get_settings",
            return_value=SimpleNamespace(telegram_token="test_token"),
        ),
    ):
        client = TelegramClient(user_id=1)
        client.bot = mock_bot
        return client


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update object."""
    user = MagicMock(spec=User)
    user.id = 123
    user.first_name = "Test"

    chat = MagicMock(spec=Chat)
    chat.id = 123

    message = MagicMock(spec=Message)
    message.text = "/test"
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message

    return update


@pytest.fixture
def mock_context():
    """Create a mock context for command handlers."""
    return MagicMock()


class TestTelegramClient:
    """Tests for the TelegramClient class."""

    def test_init(self):
        """Test initialization of the TelegramClient."""
        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_settings",
            return_value=SimpleNamespace(telegram_token="test_token"),
        ):
            client = TelegramClient(user_id=1)
            assert client.token == "test_token"

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_settings",
            return_value=SimpleNamespace(telegram_token=""),
        ):
            with pytest.raises(ValueError):
                TelegramClient(user_id=1)

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, telegram_client):
        """Test successful credential validation."""
        result = await telegram_client.validate_credentials()
        assert result is True
        telegram_client.bot.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self, telegram_client):
        """Test failed credential validation."""
        telegram_client.bot.get_me.side_effect = TelegramError("Invalid token")
        result = await telegram_client.validate_credentials()
        assert result is False
        telegram_client.bot.get_me.assert_called_once()

    @pytest.mark.asyncio
    async def test_respect_rate_limit(self, telegram_client):
        """Test rate limit handling."""
        # Test with RetryAfter exception
        e = RetryAfter(3)
        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            result = await telegram_client._respect_rate_limit(e)
            assert result is True
            mock_sleep.assert_called_once_with(3)

        # Test with other exception
        e = Exception("Other error")
        result = await telegram_client._respect_rate_limit(e)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_error_rate_limit(self, telegram_client):
        """Test message error handling with rate limit."""
        e = RetryAfter(3)
        with patch.object(
            telegram_client, "_respect_rate_limit", AsyncMock(return_value=True)
        ) as mock_rate_limit:
            result = await telegram_client._handle_message_error(e, 123)
            assert result is True
            mock_rate_limit.assert_called_once_with(e)

    @pytest.mark.asyncio
    async def test_handle_message_error_network_error(self, telegram_client):
        """Test message error handling with network error."""
        e = NetworkError("Network error")
        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            # Test with retry count < max_retries
            result = await telegram_client._handle_message_error(e, 123, 0)
            assert result is True
            mock_sleep.assert_called_once_with(1)  # 2^0 = 1

            # Test with retry count >= max_retries
            result = await telegram_client._handle_message_error(e, 123, 3)
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_error_bad_request(self, telegram_client):
        """Test message error handling with bad request."""
        e = BadRequest("Bad request")
        with patch.object(
            telegram_client, "_respect_rate_limit", AsyncMock(return_value=False)
        ):
            result = await telegram_client._handle_message_error(e, 123)
            assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_error_forbidden(self, telegram_client):
        """Test message error handling with forbidden error."""
        e = Forbidden("Forbidden")
        result = await telegram_client._handle_message_error(e, 123)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_error_other(self, telegram_client):
        """Test message error handling with other error."""
        e = Exception("Other error")
        result = await telegram_client._handle_message_error(e, 123)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_success(self, telegram_client):
        """Test successful message sending."""
        result = await telegram_client.send_message(123, "Test message")
        assert result is True
        telegram_client.bot.send_message.assert_called_once_with(
            chat_id=123, text="Test message", parse_mode=ParseMode.MARKDOWN
        )

    @pytest.mark.asyncio
    async def test_send_message_error_with_retry(self, telegram_client):
        """Test message sending with error and retry."""
        telegram_client.bot.send_message.side_effect = [
            NetworkError("Network error"),
            None,
        ]
        with patch.object(
            telegram_client, "_handle_message_error", AsyncMock(return_value=True)
        ) as mock_handle_error:
            result = await telegram_client.send_message(123, "Test message")
            assert result is True
            assert mock_handle_error.call_count == 1
            assert telegram_client.bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_error_without_retry(self, telegram_client):
        """Test message sending with error and no retry."""
        telegram_client.bot.send_message.side_effect = BadRequest("Bad request")
        with patch.object(
            telegram_client, "_handle_message_error", AsyncMock(return_value=False)
        ) as mock_handle_error:
            result = await telegram_client.send_message(123, "Test message")
            assert result is False
            assert mock_handle_error.call_count == 1
            assert telegram_client.bot.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_register_command_handler(self, telegram_client):
        """Test command handler registration."""
        handler = AsyncMock()
        await telegram_client.register_command_handler("test", handler)
        assert "test" in telegram_client._command_handlers
        assert telegram_client._command_handlers["test"] == handler

    @pytest.mark.asyncio
    async def test_handle_unknown_command(
        self, telegram_client, mock_update, mock_context
    ):
        """Test handling of unknown commands."""
        telegram_client._command_handlers = {
            "start": AsyncMock(),
            "help": AsyncMock(),
        }
        await telegram_client._handle_unknown_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        assert "Available commands" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_setup_command_handlers(self, telegram_client):
        """Test setting up command handlers."""
        with patch(
            "the_assistant.integrations.telegram.telegram_client.ApplicationBuilder"
        ) as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value.token.return_value.build.return_value = mock_app

            # Register some command handlers
            handler1 = AsyncMock()
            handler2 = AsyncMock()
            await telegram_client.register_command_handler("start", handler1)
            await telegram_client.register_command_handler("help", handler2)

            # Setup command handlers
            await telegram_client.setup_command_handlers()

            # Verify application was created
            mock_builder.assert_called_once()
            mock_builder.return_value.token.assert_called_once_with("test_token")

            # Verify handlers were added
            assert (
                mock_app.add_handler.call_count == 3
            )  # 2 commands + 1 unknown command handler

            # Verify application was stored
            assert telegram_client.application == mock_app

            # Test calling setup again (should not recreate application)
            await telegram_client.setup_command_handlers()
            mock_builder.assert_called_once()  # Still only called once
