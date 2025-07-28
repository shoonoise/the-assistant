"""Tests for enhanced command handler infrastructure."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, Message, Update, User
from telegram.ext import ContextTypes

from the_assistant.integrations.telegram.enhanced_command_handlers import (
    AddCountdownHandler,
    AddTaskHandler,
    IgnoreEmailHandler,
    MemoryAddHandler,
)
from the_assistant.integrations.telegram.enhanced_handlers import (
    CommandValidator,
    ErrorHandler,
    FlexibleCommandHandler,
    MessageFormatter,
)


class TestFlexibleCommandHandler:
    """Test the FlexibleCommandHandler base class."""

    class MockHandler(FlexibleCommandHandler):
        """Mock implementation for testing."""

        def __init__(self):
            super().__init__("test_command")
            self.direct_mode_called = False
            self.dialog_mode_called = False

        async def handle_direct_mode(self, update, context, args):
            self.direct_mode_called = True
            self.received_args = args

        async def handle_dialog_mode(self, update, context):
            self.dialog_mode_called = True

    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        user = User(id=123, is_bot=False, first_name="Test")
        chat = Chat(id=456, type="private")
        message = Message(
            message_id=1,
            date=None,
            chat=chat,
            from_user=user,
            text="/test_command arg1 arg2",
        )

        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = user
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_command_with_args_calls_direct_mode(
        self, mock_update, mock_context
    ):
        """Test that commands with arguments call direct mode."""
        handler = self.MockHandler()
        mock_context.args = ["arg1", "arg2"]

        await handler.handle_command(mock_update, mock_context)

        assert handler.direct_mode_called
        assert not handler.dialog_mode_called
        assert handler.received_args == ["arg1", "arg2"]

    @pytest.mark.asyncio
    async def test_handle_command_without_args_calls_dialog_mode(
        self, mock_update, mock_context
    ):
        """Test that commands without arguments call dialog mode."""
        handler = self.MockHandler()
        mock_context.args = []

        await handler.handle_command(mock_update, mock_context)

        assert not handler.direct_mode_called
        assert handler.dialog_mode_called

    @pytest.mark.asyncio
    async def test_handle_command_with_no_message_logs_warning(self, mock_context):
        """Test that commands without message log warning and return."""
        handler = self.MockHandler()
        mock_context.args = []

        update = MagicMock(spec=Update)
        update.message = None
        update.effective_user = None

        with patch(
            "the_assistant.integrations.telegram.enhanced_handlers.logger"
        ) as mock_logger:
            await handler.handle_command(update, mock_context)

            mock_logger.warning.assert_called_once()
            assert not handler.direct_mode_called
            assert not handler.dialog_mode_called

    @pytest.mark.asyncio
    async def test_handle_command_error_handling(self, mock_update, mock_context):
        """Test that errors in command handling are caught and handled."""

        class ErrorHandler(FlexibleCommandHandler):
            def __init__(self):
                super().__init__("error_command")

            async def handle_direct_mode(self, update, context, args):
                raise ValueError("Test error")

            async def handle_dialog_mode(self, update, context):
                raise ValueError("Test error")

        handler = ErrorHandler()
        mock_context.args = ["arg1"]

        with patch(
            "the_assistant.integrations.telegram.enhanced_handlers.ErrorHandler.handle_command_error"
        ) as mock_error_handler:
            await handler.handle_command(mock_update, mock_context)
            mock_error_handler.assert_called_once()


class TestCommandValidator:
    """Test the CommandValidator class."""

    @pytest.mark.asyncio
    async def test_validate_memory_input_valid(self):
        """Test memory input validation with valid input."""
        is_valid, message = await CommandValidator.validate_memory_input(
            "Valid memory text"
        )
        assert is_valid
        assert message == "Memory is valid."

    @pytest.mark.asyncio
    async def test_validate_memory_input_empty(self):
        """Test memory input validation with empty input."""
        is_valid, message = await CommandValidator.validate_memory_input("")
        assert not is_valid
        assert "cannot be empty" in message

    @pytest.mark.asyncio
    async def test_validate_memory_input_too_long(self):
        """Test memory input validation with too long input."""
        long_text = "x" * 501
        is_valid, message = await CommandValidator.validate_memory_input(long_text)
        assert not is_valid
        assert "too long" in message

    @pytest.mark.asyncio
    async def test_validate_task_input_valid(self):
        """Test task input validation with valid input."""
        is_valid, message = await CommandValidator.validate_task_input(
            "Valid task instruction"
        )
        assert is_valid
        assert message == "Task instruction is valid."

    @pytest.mark.asyncio
    async def test_validate_task_input_empty(self):
        """Test task input validation with empty input."""
        is_valid, message = await CommandValidator.validate_task_input("   ")
        assert not is_valid
        assert "cannot be empty" in message

    @pytest.mark.asyncio
    async def test_validate_countdown_input_valid(self):
        """Test countdown input validation with valid input."""
        is_valid, message = await CommandValidator.validate_countdown_input(
            "Valid countdown"
        )
        assert is_valid
        assert message == "Countdown description is valid."

    @pytest.mark.asyncio
    async def test_validate_email_pattern_valid(self):
        """Test email pattern validation with valid input."""
        is_valid, message = await CommandValidator.validate_email_pattern(
            "test@example.com"
        )
        assert is_valid
        assert message == "Email pattern is valid."

    @pytest.mark.asyncio
    async def test_validate_email_pattern_too_short(self):
        """Test email pattern validation with too short input."""
        is_valid, message = await CommandValidator.validate_email_pattern("ab")
        assert not is_valid
        assert "too short" in message


class TestErrorHandler:
    """Test the ErrorHandler class."""

    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = user
        return update

    @pytest.mark.asyncio
    async def test_handle_command_error_generic(self, mock_update):
        """Test generic error handling."""
        error = Exception("Generic error")

        with patch(
            "the_assistant.integrations.telegram.enhanced_handlers.logger"
        ) as mock_logger:
            await ErrorHandler.handle_command_error(mock_update, error, "test_command")

            mock_logger.error.assert_called_once()
            mock_update.message.reply_text.assert_called_once()

            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "error processing the /test_command command" in call_args

    @pytest.mark.asyncio
    async def test_handle_command_error_not_registered(self, mock_update):
        """Test error handling for unregistered user."""
        error = ValueError("User not registered")

        await ErrorHandler.handle_command_error(mock_update, error, "test_command")

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "need to register first" in call_args

    @pytest.mark.asyncio
    async def test_handle_validation_error(self, mock_update):
        """Test validation error handling."""
        await ErrorHandler.handle_validation_error(
            mock_update, "Input is invalid", "test_command"
        )

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Input is invalid" in call_args
        assert "/test_command" in call_args


class TestMessageFormatter:
    """Test the MessageFormatter class."""

    def test_format_help_message(self):
        """Test help message formatting."""
        command_registry = {"start": "Start the bot", "help": "Show help"}

        result = MessageFormatter.format_help_message(command_registry)

        assert "<b>📚 Available Commands</b>" in result
        assert "/start - Start the bot" in result
        assert "/help - Show help" in result
        assert "💡 Tips:" in result

    def test_format_user_content(self):
        """Test user content formatting (should return plain text)."""
        user_input = "User's <b>input</b> with HTML"
        result = MessageFormatter.format_user_content(user_input)

        # Should return plain text without modification
        assert result == user_input

    def test_format_confirmation(self):
        """Test confirmation message formatting."""
        result = MessageFormatter.format_confirmation("Memory added", "Test memory")

        assert result == "✅ Memory added: Test memory"

    def test_format_dialog_prompt(self):
        """Test dialog prompt formatting."""
        result = MessageFormatter.format_dialog_prompt(
            "test_command", "Enter some text", ["example 1", "example 2"]
        )

        assert "<b>/test_command</b>" in result
        assert "Enter some text" in result
        assert "<b>Examples:</b>" in result
        assert "• example 1" in result
        assert "• example 2" in result

    def test_format_dialog_prompt_no_examples(self):
        """Test dialog prompt formatting without examples."""
        result = MessageFormatter.format_dialog_prompt(
            "test_command", "Enter some text"
        )

        assert "<b>/test_command</b>" in result
        assert "Enter some text" in result
        assert "Examples:" not in result


class TestMemoryAddHandler:
    """Test the MemoryAddHandler implementation."""

    @pytest.fixture
    def handler(self):
        """Create a MemoryAddHandler instance."""
        return MemoryAddHandler()

    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = user
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_direct_mode_valid_input(
        self, handler, mock_update, mock_context
    ):
        """Test direct mode with valid memory input."""
        args = ["Valid", "memory", "text"]

        with (
            patch.object(handler, "_get_user_from_update") as mock_get_user,
            patch.object(handler, "_store_memory") as mock_store,
        ):
            mock_user = MagicMock()
            mock_get_user.return_value = mock_user

            await handler.handle_direct_mode(mock_update, mock_context, args)

            mock_get_user.assert_called_once_with(mock_update)
            mock_store.assert_called_once_with(mock_user, "Valid memory text")
            mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_direct_mode_invalid_input(
        self, handler, mock_update, mock_context
    ):
        """Test direct mode with invalid memory input."""
        args = [""]  # Empty input

        await handler.handle_direct_mode(mock_update, mock_context, args)

        # Should send validation error message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "cannot be empty" in call_args

    @pytest.mark.asyncio
    async def test_handle_dialog_mode(self, handler, mock_update, mock_context):
        """Test dialog mode sends descriptive prompt."""
        await handler.handle_dialog_mode(mock_update, mock_context)

        # Should send prompt message
        mock_update.message.reply_text.assert_called_once()

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "memory_add" in call_args
        assert "remember about you" in call_args
        assert "briefings" in call_args


class TestAddTaskHandler:
    """Test the AddTaskHandler implementation."""

    @pytest.fixture
    def handler(self):
        """Create an AddTaskHandler instance."""
        return AddTaskHandler()

    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = user
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_dialog_mode(self, handler, mock_update, mock_context):
        """Test dialog mode sets conversation state and sends prompt."""
        await handler.handle_dialog_mode(mock_update, mock_context)

        assert mock_context.user_data["conversation_state"] == "TASK_INPUT"
        mock_update.message.reply_text.assert_called_once()

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "add_task" in call_args
        assert "schedule information" in call_args


class TestAddCountdownHandler:
    """Test the AddCountdownHandler implementation."""

    @pytest.fixture
    def handler(self):
        """Create an AddCountdownHandler instance."""
        return AddCountdownHandler()

    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = user
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_direct_mode_valid_input(
        self, handler, mock_update, mock_context
    ):
        """Test direct mode with valid countdown input."""
        args = ["my", "birthday", "on", "2025-05-01"]

        with (
            patch.object(handler, "_get_user_from_update") as mock_get_user,
            patch.object(handler, "_process_and_store_countdown") as mock_store,
        ):
            mock_user = MagicMock()
            mock_get_user.return_value = mock_user

            await handler.handle_direct_mode(mock_update, mock_context, args)

            mock_get_user.assert_called_once_with(mock_update)
            mock_store.assert_called_once_with(mock_user, "my birthday on 2025-05-01")
            mock_update.message.reply_text.assert_called_once()

            # Check confirmation message
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅ Countdown added:" in call_args
            assert "my birthday on 2025-05-01" in call_args

    @pytest.mark.asyncio
    async def test_handle_direct_mode_invalid_input(
        self, handler, mock_update, mock_context
    ):
        """Test direct mode with invalid countdown input."""
        args = [""]  # Empty input

        await handler.handle_direct_mode(mock_update, mock_context, args)

        # Should send validation error message
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "❌" in call_args
        assert "cannot be empty" in call_args

    @pytest.mark.asyncio
    async def test_handle_dialog_mode(self, handler, mock_update, mock_context):
        """Test dialog mode sets conversation state and sends descriptive prompt with examples."""
        await handler.handle_dialog_mode(mock_update, mock_context)

        # Check conversation state is set
        assert mock_context.user_data["conversation_state"] == "COUNTDOWN_INPUT"

        # Check prompt message was sent
        mock_update.message.reply_text.assert_called_once()

        call_args = mock_update.message.reply_text.call_args[0][0]
        # Check for descriptive prompt as specified in requirements
        assert "add_countdown" in call_args
        assert "countdown description with date information" in call_args

        # Check for examples as specified in requirements
        assert "Examples:" in call_args
        assert "my birthday on 2025-05-01" in call_args
        assert "vacation starts on 2025-07-15" in call_args
        assert "project deadline on 2025-03-30" in call_args

    @pytest.mark.asyncio
    async def test_handle_direct_mode_processing_error(
        self, handler, mock_update, mock_context
    ):
        """Test direct mode handles processing errors gracefully."""
        args = ["invalid", "countdown", "format"]

        with (
            patch.object(handler, "_get_user_from_update") as mock_get_user,
            patch.object(handler, "_process_and_store_countdown") as mock_store,
        ):
            mock_user = MagicMock()
            mock_get_user.return_value = mock_user
            mock_store.side_effect = ValueError("Could not parse a date")

            # Should raise exception, which will be caught by FlexibleCommandHandler
            with pytest.raises(ValueError, match="Could not parse a date"):
                await handler.handle_direct_mode(mock_update, mock_context, args)

            mock_get_user.assert_called_once_with(mock_update)
            mock_store.assert_called_once_with(mock_user, "invalid countdown format")

    @pytest.mark.asyncio
    async def test_consistent_behavior_between_modes(
        self, handler, mock_update, mock_context
    ):
        """Test that both modes handle the same input consistently."""
        test_input = "vacation starts on 2025-07-15"

        # Test direct mode
        with (
            patch.object(handler, "_get_user_from_update") as mock_get_user,
            patch.object(handler, "_process_and_store_countdown") as mock_store,
        ):
            mock_user = MagicMock()
            mock_get_user.return_value = mock_user

            await handler.handle_direct_mode(
                mock_update, mock_context, test_input.split()
            )

            # Verify the same processing logic is called
            mock_store.assert_called_once_with(mock_user, test_input)

            # Verify confirmation message format
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert "✅ Countdown added:" in call_args
            assert test_input in call_args


class TestIgnoreEmailHandler:
    """Test the IgnoreEmailHandler implementation."""

    @pytest.fixture
    def handler(self):
        """Create an IgnoreEmailHandler instance."""
        return IgnoreEmailHandler()

    @pytest.fixture
    def mock_update(self):
        """Create a mock update object."""
        user = User(id=123, is_bot=False, first_name="Test")
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.message = message
        update.effective_user = user
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock context object."""
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_handle_dialog_mode_shows_usage(
        self, handler, mock_update, mock_context
    ):
        """Test dialog mode shows usage information instead of starting dialog."""
        await handler.handle_dialog_mode(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once()

        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Email Ignore Patterns" in call_args
        assert "Usage:" in call_args
        assert "Examples:" in call_args
