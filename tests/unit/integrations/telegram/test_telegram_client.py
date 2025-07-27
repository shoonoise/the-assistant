"""Unit tests for the Telegram client."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Bot, Chat, Message, Update, User
from telegram.constants import ParseMode
from telegram.error import NetworkError, TelegramError

from the_assistant.integrations.telegram.constants import SettingKey
from the_assistant.integrations.telegram.telegram_client import (
    TelegramClient,
    handle_add_countdown_command,
    handle_add_task_command,
    handle_briefing_command,
    handle_google_auth_command,
    handle_ignore_email_command,
    handle_memory_add_command,
    handle_memory_command,
    save_setting,
    start_memory_delete,
    start_update_settings,
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
    async def test_send_message_success(self, telegram_client):
        """Test successful message sending."""
        # Mock user service to return a user with telegram_chat_id
        mock_user = SimpleNamespace(telegram_chat_id=123)
        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service"
        ) as mock_get_service:
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
    async def test_send_message_error_propagates(self, telegram_client):
        """Send message raises when the Telegram API fails."""
        mock_user = SimpleNamespace(telegram_chat_id=123)

        telegram_client.bot.send_message.side_effect = NetworkError("Network error")
        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service"
        ) as mock_get_service:
            mock_service = AsyncMock()
            mock_service.get_user_by_id.return_value = mock_user
            mock_get_service.return_value = mock_service

            with pytest.raises(NetworkError):
                await telegram_client.send_message("Test message")
            telegram_client.bot.send_message.assert_called_once()

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
            ) as mock_client,
            patch(
                "the_assistant.integrations.telegram.telegram_client.create_state_jwt",
                return_value="state",
            ) as mock_state,
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_settings",
                return_value=SimpleNamespace(jwt_secret="test-secret"),
            ) as mock_settings,
        ):
            mock_context.args = ["personal"]
            await handle_google_auth_command(mock_update, mock_context)

        mock_client.assert_called_once_with(user.id, account="personal")
        mock_state.assert_called_once_with(
            user.id, mock_settings.return_value, account="personal"
        )

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
            ) as mock_client,
        ):
            mock_context.args = ["work"]
            await handle_google_auth_command(mock_update, mock_context)

        mock_client.assert_called_once_with(user.id, account="work")

        google_client.is_authenticated.assert_awaited_once()
        assert mock_update.message.reply_text.called
        assert "already" in mock_update.message.reply_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_handle_google_auth_command_unregistered_user(
        self, mock_update, mock_context
    ):
        """A helpful message is sent if the user is not registered."""

        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=None)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.args = []
            await handle_google_auth_command(mock_update, mock_context)

            # Verify that a helpful message was sent instead of raising an error
            mock_update.message.reply_text.assert_called_once()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "need to register first" in call_args
            assert "/start" in call_args

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


class TestUpdateSettings:
    """Tests for the settings update conversation."""

    @pytest.mark.asyncio
    async def test_start_update_settings(self, mock_update, mock_context):
        await start_update_settings(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        args, _ = mock_update.message.reply_text.call_args
        assert "choose which setting" in args[0]

    @pytest.mark.asyncio
    async def test_save_setting_trim_and_default(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.user_data = {
                "setting_key": SettingKey.GREET,
                "setting_label": "How to greet",
            }
            mock_update.message.text = "  Hello  "
            await save_setting(mock_update, mock_context)

        user_service.set_setting.assert_awaited_once_with(1, SettingKey.GREET, "Hello")
        assert mock_update.message.reply_text.called

    @pytest.mark.asyncio
    async def test_save_setting_empty_default(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.user_data = {
                "setting_key": SettingKey.GREET,
                "setting_label": "How to greet",
            }
            mock_update.message.text = ""
            await save_setting(mock_update, mock_context)

        user_service.set_setting.assert_awaited_once_with(
            1, SettingKey.GREET, "first_name"
        )

    @pytest.mark.asyncio
    async def test_save_setting_user_not_registered(self, mock_update, mock_context):
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=None)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.user_data = {
                "setting_key": SettingKey.GREET,
                "setting_label": "How to greet",
            }
            mock_update.message.text = "Hi"
            with pytest.raises(ValueError):
                await save_setting(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_ignore_email_command(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.get_setting = AsyncMock(return_value=[])
        user_service.set_setting = AsyncMock()

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.args = ["*@spam.com"]
            await handle_ignore_email_command(mock_update, mock_context)

        user_service.set_setting.assert_awaited_once_with(
            1, SettingKey.IGNORE_EMAILS, ["*@spam.com"]
        )
        assert mock_update.message.reply_text.called

    @pytest.mark.asyncio
    async def test_memory_add_command(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.get_setting = AsyncMock(return_value={})
        user_service.set_setting = AsyncMock()

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.telegram.telegram_client.datetime"
            ) as mock_dt,
        ):
            mock_dt.now.return_value = datetime(2024, 1, 1, tzinfo=UTC)
            mock_dt.UTC = UTC
            mock_context.args = ["remember this"]
            await handle_memory_add_command(mock_update, mock_context)

        assert user_service.set_setting.await_count == 1
        call_args = user_service.set_setting.call_args[0]
        assert call_args[0] == 1
        assert call_args[1] == SettingKey.MEMORIES
        memories = call_args[2]
        assert list(memories.values())[0]["user_input"] == "remember this"

    @pytest.mark.asyncio
    async def test_memory_command_lists(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        mems = {
            "2024-01-02 00:00:00": {"user_input": "b"},
            "2024-01-01 00:00:00": {"user_input": "a"},
        }
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.get_setting = AsyncMock(return_value=mems)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            await handle_memory_command(mock_update, mock_context)

        assert mock_update.message.reply_text.called
        msg = mock_update.message.reply_text.call_args[0][0]
        assert "1." in msg and "2." in msg

    @pytest.mark.asyncio
    async def test_memory_delete_command(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        mems = {
            "2024-01-01 00:00:00": {"user_input": "a"},
            "2024-01-02 00:00:00": {"user_input": "b"},
        }
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.get_setting = AsyncMock(return_value=mems)
        user_service.set_setting = AsyncMock()

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.args = ["1"]
            # Use start_memory_delete instead of handle_memory_delete_command
            # since the latter is now just a stub

            await start_memory_delete(mock_update, mock_context)

        assert user_service.set_setting.await_count == 1
        args = user_service.set_setting.call_args[0]
        assert len(args[2]) == 1

    @pytest.mark.asyncio
    async def test_add_task_command(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.create_task = AsyncMock()

        parser = AsyncMock()
        parser.parse.return_value = ("daily 6pm", "say hi")

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.llm.TaskParser",
                return_value=parser,
            ),
        ):
            mock_context.args = ["every", "day", "at", "6pm", "say", "hi"]
            await handle_add_task_command(mock_update, mock_context)

        parser.parse.assert_awaited_once_with("every day at 6pm say hi")
        user_service.create_task.assert_awaited_once_with(
            user.id,
            "every day at 6pm say hi",
            schedule="daily 6pm",
            instruction="say hi",
        )
        assert mock_update.message.reply_text.called

    @pytest.mark.asyncio
    async def test_add_task_command_unregistered(self, mock_update, mock_context):
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=None)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.args = ["do", "something"]
            await handle_add_task_command(mock_update, mock_context)

        assert mock_update.message.reply_text.called
        assert "register" in mock_update.message.reply_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_add_task_command_parse_failure(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.create_task = AsyncMock()

        parser = AsyncMock()
        parser.parse.return_value = ("", "say hi")

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.llm.TaskParser",
                return_value=parser,
            ),
        ):
            mock_context.args = ["some", "text"]
            await handle_add_task_command(mock_update, mock_context)

        parser.parse.assert_awaited_once_with("some text")
        user_service.create_task.assert_not_called()
        assert mock_update.message.reply_text.called
        assert "parse" in mock_update.message.reply_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_add_countdown_command(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.create_countdown = AsyncMock()

        parser = AsyncMock()
        parser.parse.return_value = (datetime(2025, 1, 1, tzinfo=UTC), "party")

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.llm.CountdownParser",
                return_value=parser,
            ),
        ):
            mock_context.args = ["party", "on", "2025-01-01"]
            await handle_add_countdown_command(mock_update, mock_context)

        parser.parse.assert_awaited_once_with("party on 2025-01-01")
        user_service.create_countdown.assert_awaited_once()
        assert mock_update.message.reply_text.called

    @pytest.mark.asyncio
    async def test_add_countdown_command_unregistered(self, mock_update, mock_context):
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=None)

        with patch(
            "the_assistant.integrations.telegram.telegram_client.get_user_service",
            return_value=user_service,
        ):
            mock_context.args = ["party"]
            await handle_add_countdown_command(mock_update, mock_context)

        assert mock_update.message.reply_text.called
        assert "register" in mock_update.message.reply_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_add_countdown_command_parse_failure(self, mock_update, mock_context):
        user = SimpleNamespace(id=1, telegram_chat_id=123)
        user_service = AsyncMock()
        user_service.get_user_by_telegram_chat_id = AsyncMock(return_value=user)
        user_service.create_countdown = AsyncMock()

        parser = AsyncMock()
        parser.parse.return_value = (None, "party")

        with (
            patch(
                "the_assistant.integrations.telegram.telegram_client.get_user_service",
                return_value=user_service,
            ),
            patch(
                "the_assistant.integrations.llm.CountdownParser",
                return_value=parser,
            ),
        ):
            mock_context.args = ["some", "text"]
            await handle_add_countdown_command(mock_update, mock_context)

        parser.parse.assert_awaited_once_with("some text")
        user_service.create_countdown.assert_not_called()
        assert mock_update.message.reply_text.called
        assert "parse" in mock_update.message.reply_text.call_args[0][0].lower()
