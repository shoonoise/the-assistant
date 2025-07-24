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

from the_assistant.integrations.telegram.telegram_client import (
    TelegramClient,
    handle_briefing_command,
    handle_google_auth_command,
)


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
        # Mock user service to return a user with telegram_chat_id
        mock_user = SimpleNamespace(telegram_chat_id=123)
        with patch("the_assistant.db.get_user_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_by_id.return_value = mock_user
            mock_get_service.return_value = mock_service

            result = await telegram_client.send_message("Test message")

            assert result is True
            mock_service.get_user_by_id.assert_called_once_with(
                1
            )  # user_id from fixture
            telegram_client.bot.send_message.assert_called_once_with(
                chat_id=123, text="Test message", parse_mode=ParseMode.MARKDOWN
            )

    @pytest.mark.asyncio
    async def test_send_message_error_with_retry(self, telegram_client):
        """Test message sending with error and retry."""
        # Mock user service to return a user with telegram_chat_id
        mock_user = SimpleNamespace(telegram_chat_id=123)

        telegram_client.bot.send_message.side_effect = [
            NetworkError("Network error"),
            None,
        ]
        with (
            patch("the_assistant.db.get_user_service") as mock_get_service,
            patch.object(
                telegram_client, "_handle_message_error", AsyncMock(return_value=True)
            ) as mock_handle_error,
        ):
            mock_service = AsyncMock()
            mock_service.get_user_by_id.return_value = mock_user
            mock_get_service.return_value = mock_service

            result = await telegram_client.send_message("Test message")
            assert result is True
            assert mock_handle_error.call_count == 1
            assert telegram_client.bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_error_without_retry(self, telegram_client):
        """Test message sending with error and no retry."""
        # Mock user service to return a user with telegram_chat_id
        mock_user = SimpleNamespace(telegram_chat_id=123)

        telegram_client.bot.send_message.side_effect = BadRequest("Bad request")
        with (
            patch("the_assistant.db.get_user_service") as mock_get_service,
            patch.object(
                telegram_client, "_handle_message_error", AsyncMock(return_value=False)
            ) as mock_handle_error,
        ):
            mock_service = AsyncMock()
            mock_service.get_user_by_id.return_value = mock_user
            mock_get_service.return_value = mock_service

            result = await telegram_client.send_message("Test message")
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

    @pytest.mark.asyncio
    async def test_handle_google_auth_command_send_link(
        self, mock_update, mock_context
    ):
        """Ensure auth link is sent when user is not authenticated."""

        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)

        google_client = AsyncMock()
        google_client.is_authenticated = AsyncMock(return_value=False)
        google_client.generate_auth_url = AsyncMock(return_value="http://auth")

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.telegram.telegram_client.GoogleClient",
                return_value=google_client,
            ),
            patch(
                "the_assistant.integrations.telegram.telegram_client.create_state_jwt",
                return_value="state",
            ),
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_settings",
                return_value=SimpleNamespace(jwt_secret="test-secret"),
            ),
        ):
            await handle_google_auth_command(mock_update, mock_context)

        google_client.generate_auth_url.assert_awaited_once_with("state")
        assert mock_update.message.reply_text.called
        assert "http://auth" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_google_auth_command_already_authenticated(
        self, mock_update, mock_context
    ):
        """A message is shown if the user is already authenticated."""

        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)

        google_client = AsyncMock()
        google_client.is_authenticated = AsyncMock(return_value=True)

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.telegram.telegram_client.GoogleClient",
                return_value=google_client,
            ),
        ):
            await handle_google_auth_command(mock_update, mock_context)

        google_client.is_authenticated.assert_awaited_once()
        assert mock_update.message.reply_text.called
        assert "already" in mock_update.message.reply_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_handle_google_auth_command_unregistered_user(
        self, mock_update, mock_context
    ):
        """An error is raised if the user is not registered."""

        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=None)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            with pytest.raises(ValueError):
                await handle_google_auth_command(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_briefing_command_success(self, mock_update, mock_context):
        """Test successful briefing command execution."""
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)

        # Mock Temporal client
        mock_client = AsyncMock()
        mock_handle = AsyncMock()
        mock_handle.id = "briefing-1-123456789"
        mock_client.start_workflow = AsyncMock(return_value=mock_handle)

        settings = SimpleNamespace(
            temporal_host="localhost:7233",
            temporal_namespace="default",
            temporal_task_queue="the-assistant",
        )

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_settings",
                return_value=settings,
            ),
            patch(
                "temporalio.client.Client.connect",
                AsyncMock(return_value=mock_client),
            ),
            patch("time.time", return_value=123456789),
        ):
            await handle_briefing_command(mock_update, mock_context)

        # Verify user lookup
        user_service.get_user_by_telegram_chat_id.assert_called_once_with(123)

        # Verify workflow was started
        mock_client.start_workflow.assert_called_once()
        args, kwargs = mock_client.start_workflow.call_args
        assert kwargs["id"] == "briefing-1-123456789"
        assert kwargs["task_queue"] == "the-assistant"
        assert args[1] == 1  # user.id

        # Verify messages were sent
        assert mock_update.message.reply_text.call_count == 2
        calls = mock_update.message.reply_text.call_args_list
        assert "Generating your briefing" in calls[0][0][0]
        assert "being generated and will be delivered" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_handle_briefing_command_unregistered_user(
        self, mock_update, mock_context
    ):
        """Test briefing command with unregistered user."""
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=None)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            await handle_briefing_command(mock_update, mock_context)

        # Verify user lookup
        user_service.get_user_by_telegram_chat_id.assert_called_once_with(123)

        # Verify error message was sent
        assert mock_update.message.reply_text.call_count == 2
        calls = mock_update.message.reply_text.call_args_list
        assert "Generating your briefing" in calls[0][0][0]
        assert "need to register first" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_handle_briefing_command_temporal_error(
        self, mock_update, mock_context
    ):
        """Test briefing command with Temporal connection error."""
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)

        settings = SimpleNamespace(
            temporal_host="localhost:7233",
            temporal_namespace="default",
            temporal_task_queue="the-assistant",
        )

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_settings",
                return_value=settings,
            ),
            patch(
                "temporalio.client.Client.connect",
                AsyncMock(side_effect=Exception("Connection failed")),
            ),
        ):
            await handle_briefing_command(mock_update, mock_context)

        # Verify error message was sent
        assert mock_update.message.reply_text.call_count == 2
        calls = mock_update.message.reply_text.call_args_list
        assert "Generating your briefing" in calls[0][0][0]
        assert "encountered an error" in calls[1][0][0]
