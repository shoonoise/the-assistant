"""Tests for Temporal activities."""

import os
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from the_assistant.activities.google_activities import (
    GetCalendarEventsInput,
    GetEventsByDateInput,
    GetTodayEventsInput,
    GetUpcomingEventsInput,
    get_calendar_events,
    get_events_by_date,
    get_google_client,
    get_today_events,
    get_upcoming_events,
)
from the_assistant.activities.obsidian_activities import scan_vault_notes
from the_assistant.activities.weather_activities import (
    GetWeatherForecastInput,
    get_weather_forecast,
)
from the_assistant.models.google import CalendarEvent
from the_assistant.models.weather import WeatherForecast


class TestGoogleActivities:
    """Test Google Calendar activities."""

    @pytest.fixture
    def mock_google_client(self):
        """Mock Google client."""
        client = AsyncMock()
        client.is_authenticated.return_value = True
        client.get_calendar_events.return_value = []
        client.get_upcoming_events.return_value = []
        client.get_events_by_date.return_value = []
        return client

    @pytest.fixture
    def sample_events(self):
        """Sample calendar events."""
        return [
            CalendarEvent(
                id="event1",
                summary="Test Event 1",
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC) + timedelta(hours=1),
                description="Test description",
                location="Test location",
            ),
            CalendarEvent(
                id="event2",
                summary="Test Event 2",
                start_time=datetime.now(UTC) + timedelta(hours=2),
                end_time=datetime.now(UTC) + timedelta(hours=3),
                description="Another test",
                location="Another location",
            ),
        ]

    def test_get_google_client_missing_encryption_key(self):
        """Test get_google_client raises error when encryption key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="DB_ENCRYPTION_KEY not configured"):
                get_google_client(1)

    @patch("the_assistant.activities.google_activities.GoogleClient")
    @patch("the_assistant.activities.google_activities.PostgresCredentialStore")
    @patch("the_assistant.activities.google_activities.get_google_credentials_path")
    def test_get_google_client_success(
        self, mock_get_creds_path, mock_credential_store, mock_google_client
    ):
        """Test successful Google client creation."""
        mock_get_creds_path.return_value = "/path/to/creds.json"

        with patch.dict(os.environ, {"DB_ENCRYPTION_KEY": "test-key"}):
            client = get_google_client(1)

        mock_credential_store.assert_called_once()
        mock_google_client.assert_called_once()
        assert client is not None

    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_calendar_events_success(
        self, mock_get_client, mock_google_client, sample_events
    ):
        """Test successful calendar events retrieval."""
        mock_get_client.return_value = mock_google_client
        mock_google_client.get_calendar_events.return_value = sample_events

        input_data = GetCalendarEventsInput(
            user_id=1, calendar_id="primary", max_results=10
        )
        result = await get_calendar_events(input_data)

        assert result == sample_events
        mock_google_client.is_authenticated.assert_called_once()
        mock_google_client.get_calendar_events.assert_called_once_with(
            calendar_id="primary", time_min=None, time_max=None, max_results=10
        )

    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_calendar_events_not_authenticated(
        self, mock_get_client, mock_google_client
    ):
        """Test calendar events retrieval when user is not authenticated."""
        mock_get_client.return_value = mock_google_client
        mock_google_client.is_authenticated.return_value = False

        input_data = GetCalendarEventsInput(user_id=1)
        with pytest.raises(ValueError, match="User 1 is not authenticated with Google"):
            await get_calendar_events(input_data)

    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_upcoming_events_success(
        self, mock_get_client, mock_google_client, sample_events
    ):
        """Test successful upcoming events retrieval."""
        mock_get_client.return_value = mock_google_client
        mock_google_client.get_upcoming_events.return_value = sample_events

        input_data = GetUpcomingEventsInput(
            user_id=1, days_ahead=7, calendar_id="primary"
        )
        result = await get_upcoming_events(input_data)

        assert result == sample_events
        mock_google_client.is_authenticated.assert_called_once()
        mock_google_client.get_upcoming_events.assert_called_once_with(
            days_ahead=7, calendar_id="primary"
        )

    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_upcoming_events_not_authenticated(
        self, mock_get_client, mock_google_client
    ):
        """Test upcoming events retrieval when user is not authenticated."""
        mock_get_client.return_value = mock_google_client
        mock_google_client.is_authenticated.return_value = False

        input_data = GetUpcomingEventsInput(user_id=1)
        with pytest.raises(ValueError, match="User 1 is not authenticated with Google"):
            await get_upcoming_events(input_data)

    @patch("the_assistant.activities.google_activities.get_google_calendar_id")
    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_events_by_date_success(
        self, mock_get_client, mock_get_calendar_id, mock_google_client, sample_events
    ):
        """Test successful events by date retrieval."""
        mock_get_client.return_value = mock_google_client
        mock_get_calendar_id.return_value = "test-calendar"
        mock_google_client.get_events_by_date.return_value = sample_events

        target_date = datetime.now(UTC)
        input_data = GetEventsByDateInput(user_id=1, target_date=target_date)
        result = await get_events_by_date(input_data)

        assert result == sample_events
        mock_google_client.is_authenticated.assert_called_once()
        mock_google_client.get_events_by_date.assert_called_once_with(
            target_date=target_date, calendar_id="test-calendar"
        )

    @patch("the_assistant.activities.google_activities.get_events_by_date")
    async def test_get_today_events(self, mock_get_events_by_date, sample_events):
        """Test get today's events."""
        mock_get_events_by_date.return_value = sample_events

        input_data = GetTodayEventsInput(user_id=1, calendar_id="primary")
        result = await get_today_events(input_data)

        assert result == sample_events
        mock_get_events_by_date.assert_called_once()
        # Check that the input passed to get_events_by_date is correct
        call_args = mock_get_events_by_date.call_args
        input_arg = call_args[0][0]  # First positional argument
        assert input_arg.user_id == 1
        assert input_arg.calendar_id == "primary"
        # The target_date should be today (within a few seconds)
        now = datetime.now(UTC)
        assert abs((input_arg.target_date - now).total_seconds()) < 5


class TestObsidianActivities:
    """Test Obsidian vault activities."""

    @pytest.fixture
    def mock_obsidian_client(self):
        """Mock Obsidian client."""
        client = AsyncMock()
        client.get_notes.return_value = []  # NoteList is just list[ObsidianNote]
        return client

    @patch("the_assistant.activities.obsidian_activities.get_obsidian_vault_path")
    @patch("the_assistant.activities.obsidian_activities.ObsidianClient")
    async def test_scan_vault_notes_success(
        self, mock_obsidian_client_class, mock_get_vault_path, mock_obsidian_client
    ):
        """Test successful vault scanning."""
        from the_assistant.activities.obsidian_activities import ScanVaultNotesInput

        mock_get_vault_path.return_value = "/path/to/vault"
        mock_obsidian_client_class.return_value = mock_obsidian_client

        expected_result = []  # NoteList is just list[ObsidianNote]
        mock_obsidian_client.get_notes.return_value = expected_result

        input_data = ScanVaultNotesInput(user_id=1)
        result = await scan_vault_notes(input_data)

        assert result == expected_result
        mock_obsidian_client_class.assert_called_once_with("/path/to/vault", user_id=1)
        mock_obsidian_client.get_notes.assert_called_once_with(None)

    @patch("the_assistant.activities.obsidian_activities.get_obsidian_vault_path")
    @patch("the_assistant.activities.obsidian_activities.ObsidianClient")
    async def test_scan_vault_notes_with_filters(
        self, mock_obsidian_client_class, mock_get_vault_path, mock_obsidian_client
    ):
        """Test vault scanning with filters."""
        from the_assistant.activities.obsidian_activities import ScanVaultNotesInput
        from the_assistant.models import NoteFilters

        mock_get_vault_path.return_value = "/path/to/vault"
        mock_obsidian_client_class.return_value = mock_obsidian_client

        filters = NoteFilters(tags=["test"], tag_operator="AND")
        expected_result = []  # NoteList is just list[ObsidianNote]
        mock_obsidian_client.get_notes.return_value = expected_result

        input_data = ScanVaultNotesInput(user_id=1, filters=filters)
        result = await scan_vault_notes(input_data)

        assert result == expected_result
        mock_obsidian_client_class.assert_called_once_with("/path/to/vault", user_id=1)
        mock_obsidian_client.get_notes.assert_called_once_with(filters)


class TestWeatherActivities:
    """Test weather forecast activities."""

    @pytest.mark.asyncio
    @patch("the_assistant.activities.weather_activities.WeatherClient")
    async def test_get_weather_forecast_success(self, mock_client_class):
        mock_client = AsyncMock()
        forecast = WeatherForecast(
            location="Paris",
            forecast_date=date(2024, 7, 10),
            weather_code=1,
            temperature_max=25,
            temperature_min=15,
        )
        mock_client.get_forecast.return_value = [forecast]
        mock_client_class.return_value = mock_client

        input_data = GetWeatherForecastInput(location="Paris")
        result = await get_weather_forecast(input_data)

        assert result == [forecast]
        mock_client.get_forecast.assert_called_once_with("Paris", days=1)
