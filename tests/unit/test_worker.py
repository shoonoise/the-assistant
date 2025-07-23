"""Tests for the Temporal worker."""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest

from the_assistant.worker import main, run_worker

# Suppress false positive warnings from mocking async operations
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


class TestWorker:
    """Test the Temporal worker."""

    @pytest.fixture
    def mock_temporal_client(self):
        """Mock Temporal client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_worker(self):
        """Mock Temporal worker."""
        worker = AsyncMock()
        worker.run = AsyncMock()
        return worker

    @patch("the_assistant.worker.dotenv.load_dotenv")
    @patch("the_assistant.worker.Client.connect")
    @patch("the_assistant.worker.Worker")
    async def test_run_worker_success(
        self,
        mock_worker_class,
        mock_client_connect,
        mock_load_dotenv,
        mock_temporal_client,
        mock_worker,
    ):
        """Test successful worker startup."""
        mock_load_dotenv.return_value = None
        mock_client_connect.return_value = mock_temporal_client
        mock_worker_class.return_value = mock_worker

        # Mock environment variables
        with patch.dict(
            os.environ,
            {"TEMPORAL_HOST": "test-host:7233", "TEMPORAL_TASK_QUEUE": "test-queue"},
        ):
            # Run worker for a short time then stop
            async def stop_worker():
                await asyncio.sleep(0.1)
                mock_worker.run.side_effect = KeyboardInterrupt()

            task = asyncio.create_task(run_worker())
            stop_task = asyncio.create_task(stop_worker())

            try:
                await asyncio.gather(task, stop_task)
            except KeyboardInterrupt:
                pass  # Expected

        # Verify client connection
        mock_client_connect.assert_called_once()
        call_args = mock_client_connect.call_args
        assert call_args[0][0] == "test-host:7233"

        # Verify worker creation
        mock_worker_class.assert_called_once()
        worker_args = mock_worker_class.call_args
        assert worker_args[0][0] == mock_temporal_client
        assert worker_args[1]["task_queue"] == "test-queue"

        # Check that activities are registered
        activities = worker_args[1]["activities"]
        assert len(activities) > 0

        # Check that workflows are registered
        workflows = worker_args[1]["workflows"]
        assert len(workflows) > 0

    @patch("the_assistant.worker.dotenv.load_dotenv")
    @patch("the_assistant.worker.Client.connect")
    @patch("the_assistant.worker.Worker")
    async def test_run_worker_default_config(
        self,
        mock_worker_class,
        mock_client_connect,
        mock_load_dotenv,
        mock_temporal_client,
        mock_worker,
    ):
        """Test worker startup with default configuration."""
        mock_load_dotenv.return_value = None
        mock_client_connect.return_value = mock_temporal_client
        mock_worker_class.return_value = mock_worker

        # Clear environment variables to test defaults
        with patch.dict(os.environ, {}, clear=True):
            # Run worker for a short time then stop
            async def stop_worker():
                await asyncio.sleep(0.1)
                mock_worker.run.side_effect = KeyboardInterrupt()

            task = asyncio.create_task(run_worker())
            stop_task = asyncio.create_task(stop_worker())

            try:
                await asyncio.gather(task, stop_task)
            except KeyboardInterrupt:
                pass  # Expected

        # Verify default values are used
        mock_client_connect.assert_called_once()
        call_args = mock_client_connect.call_args
        assert call_args[0][0] == "localhost:7233"

        mock_worker_class.assert_called_once()
        worker_args = mock_worker_class.call_args
        assert worker_args[1]["task_queue"] == "the-assistant"

    @patch("the_assistant.worker.dotenv.load_dotenv")
    @patch("the_assistant.worker.Client.connect")
    async def test_run_worker_connection_error(
        self, mock_client_connect, mock_load_dotenv
    ):
        """Test worker startup with connection error."""
        mock_load_dotenv.return_value = None
        mock_client_connect.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await run_worker()

    @patch("the_assistant.worker.dotenv.load_dotenv")
    @patch("the_assistant.worker.Client.connect")
    @patch("the_assistant.worker.Worker")
    async def test_run_worker_keyboard_interrupt(
        self,
        mock_worker_class,
        mock_client_connect,
        mock_load_dotenv,
        mock_temporal_client,
        mock_worker,
    ):
        """Test worker graceful shutdown on keyboard interrupt."""
        mock_load_dotenv.return_value = None
        mock_client_connect.return_value = mock_temporal_client
        mock_worker_class.return_value = mock_worker
        mock_worker.run.side_effect = KeyboardInterrupt()

        # Should not raise exception, just log and exit gracefully
        await run_worker()

        mock_worker.run.assert_called_once()

    @patch("the_assistant.worker.dotenv.load_dotenv")
    @patch("the_assistant.worker.Client.connect")
    @patch("the_assistant.worker.Worker")
    async def test_run_worker_runtime_error(
        self,
        mock_worker_class,
        mock_client_connect,
        mock_load_dotenv,
        mock_temporal_client,
        mock_worker,
    ):
        """Test worker handling of runtime errors."""
        mock_load_dotenv.return_value = None
        mock_client_connect.return_value = mock_temporal_client
        mock_worker_class.return_value = mock_worker
        mock_worker.run.side_effect = RuntimeError("Worker failed")

        with pytest.raises(RuntimeError, match="Worker failed"):
            await run_worker()

    def test_worker_activities_imported(self):
        """Test that all required activities are imported."""
        # Import the worker module to check imports
        import the_assistant.worker as worker_module

        # Check that activities are available
        assert hasattr(worker_module, "get_calendar_events")
        assert hasattr(worker_module, "get_upcoming_events")
        assert hasattr(worker_module, "scan_vault_notes")
        assert hasattr(worker_module, "get_weather_forecast")
        assert hasattr(worker_module, "send_message")
        assert hasattr(worker_module, "build_daily_briefing")

    def test_worker_workflows_imported(self):
        """Test that all required workflows are imported."""
        import the_assistant.worker as worker_module

        # Check that workflows are available
        assert hasattr(worker_module, "DailyBriefing")

    @patch("the_assistant.worker.asyncio.run")
    def test_main_function(self, mock_asyncio_run):
        """Test the main function."""
        main()

        mock_asyncio_run.assert_called_once()

    @patch("the_assistant.worker.logging.basicConfig")
    def test_logging_configuration(self, mock_logging_config):
        """Test that logging is configured correctly."""
        # Re-import to trigger logging setup
        import importlib

        import the_assistant.worker

        importlib.reload(the_assistant.worker)

        mock_logging_config.assert_called()
        call_args = mock_logging_config.call_args
        assert "level" in call_args[1]
        assert "format" in call_args[1]

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"})
    @patch("the_assistant.worker.logging.basicConfig")
    def test_logging_level_from_env(self, mock_logging_config):
        """Test that logging level is read from environment."""
        import importlib

        import the_assistant.worker

        importlib.reload(the_assistant.worker)

        mock_logging_config.assert_called()
        call_args = mock_logging_config.call_args
        # The level should be DEBUG (which is 10)
        import logging

        assert call_args[1]["level"] == logging.DEBUG

    def test_dotenv_loaded_on_import(self):
        """Test that dotenv is loaded when module is imported."""
        with patch("the_assistant.worker.dotenv.load_dotenv") as mock_load_dotenv:
            import importlib

            import the_assistant.worker

            importlib.reload(the_assistant.worker)

            mock_load_dotenv.assert_called_once()
