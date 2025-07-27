"""Tests for Temporal activities."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from the_assistant.activities.google_activities import (
    GetCalendarEventsInput,
    GetEmailsInput,
    GetEventsByDateInput,
    GetTodayEventsInput,
    GetUpcomingEventsInput,
    get_calendar_events,
    get_emails,
    get_events_by_date,
    get_google_client,
    get_today_events,
    get_upcoming_events,
)
from the_assistant.activities.messages_activities import (
    DailyBriefingInput,
    build_daily_briefing,
)
from the_assistant.activities.obsidian_activities import (
    ScanVaultNotesInput,
    scan_vault_notes,
)
from the_assistant.activities.weather_activities import (
    GetWeatherForecastInput,
    get_weather_forecast,
)
from the_assistant.models import NoteFilters
from the_assistant.models.google import CalendarEvent, GmailMessage
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

    @patch("the_assistant.activities.google_activities.GoogleClient")
    @patch("the_assistant.activities.google_activities.get_settings")
    def test_get_google_client_success(self, mock_get_settings, mock_google_client):
        """Test successful Google client creation."""
        settings = AsyncMock()
        mock_get_settings.return_value = settings

        client = get_google_client(1)

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

    @patch("the_assistant.activities.google_activities.get_settings")
    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_events_by_date_success(
        self, mock_get_client, mock_get_settings, mock_google_client, sample_events
    ):
        """Test successful events by date retrieval."""
        settings = AsyncMock()
        settings.google_calendar_id = "test-calendar"
        mock_get_settings.return_value = settings
        mock_get_client.return_value = mock_google_client
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

    @patch("the_assistant.activities.obsidian_activities.get_settings")
    @patch("the_assistant.activities.obsidian_activities.ObsidianClient")
    async def test_scan_vault_notes_success(
        self, mock_obsidian_client_class, mock_get_settings, mock_obsidian_client
    ):
        """Test successful vault scanning."""

        settings = AsyncMock()
        settings.obsidian_vault_path = "/path/to/vault"
        mock_get_settings.return_value = settings
        mock_obsidian_client_class.return_value = mock_obsidian_client

        expected_result = []  # NoteList is just list[ObsidianNote]
        mock_obsidian_client.get_notes.return_value = expected_result

        input_data = ScanVaultNotesInput(user_id=1)
        result = await scan_vault_notes(input_data)

        assert result == expected_result
        mock_obsidian_client_class.assert_called_once_with("/path/to/vault", user_id=1)
        mock_obsidian_client.get_notes.assert_called_once_with(None)

    @patch("the_assistant.activities.obsidian_activities.get_settings")
    @patch("the_assistant.activities.obsidian_activities.ObsidianClient")
    async def test_scan_vault_notes_with_filters(
        self, mock_obsidian_client_class, mock_get_settings, mock_obsidian_client
    ):
        """Test vault scanning with filters."""

        settings = AsyncMock()
        settings.obsidian_vault_path = "/path/to/vault"
        mock_get_settings.return_value = settings
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
    @patch("the_assistant.activities.weather_activities.get_user_service")
    @patch("the_assistant.activities.weather_activities.WeatherClient")
    async def test_get_weather_forecast_success(
        self, mock_client_class, mock_get_service
    ):
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

        mock_service = AsyncMock()
        mock_service.get_setting.return_value = "Paris"
        mock_get_service.return_value = mock_service

        input_data = GetWeatherForecastInput(user_id=1)
        result = await get_weather_forecast(input_data)

        assert result == [forecast]
        mock_service.get_setting.assert_awaited_once_with(1, "location")
        mock_client.get_forecast.assert_awaited_once_with("Paris", days=1)

    @pytest.mark.asyncio
    @patch("the_assistant.activities.weather_activities.get_user_service")
    @patch("the_assistant.activities.weather_activities.WeatherClient")
    async def test_get_weather_forecast_no_location(
        self, mock_client_class, mock_get_service
    ):
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_service = AsyncMock()
        mock_service.get_setting.return_value = None
        mock_get_service.return_value = mock_service

        input_data = GetWeatherForecastInput(user_id=1)
        result = await get_weather_forecast(input_data)

        assert result == []
        mock_service.get_setting.assert_awaited_once_with(1, "location")
        mock_client.get_forecast.assert_not_called()


class TestEmailActivities:
    """Test Gmail-related activities."""

    @pytest.fixture
    def mock_google_client(self):
        client = AsyncMock()
        client.is_authenticated.return_value = True
        client.get_emails.return_value = []
        return client

    @pytest.fixture
    def sample_emails(self):
        return [
            GmailMessage(
                id="m1",
                thread_id="t1",
                snippet="hi",
                subject="Hello",
                sender="sender@example.com",
                body="Body",
            )
        ]

    @pytest.mark.asyncio
    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_emails_success(
        self, mock_get_client, mock_google_client, sample_emails
    ):
        mock_get_client.return_value = mock_google_client
        mock_google_client.get_emails.return_value = sample_emails

        input_data = GetEmailsInput(user_id=1, unread_only=True, max_results=5)
        result = await get_emails(input_data)

        assert result == sample_emails
        mock_google_client.is_authenticated.assert_called_once()
        mock_google_client.get_emails.assert_called_once_with(
            query=None,
            unread_only=True,
            sender=None,
            max_results=5,
            include_body=True,
            ignored_senders=None,
        )

    @pytest.mark.asyncio
    @patch("the_assistant.activities.google_activities.get_google_client")
    async def test_get_emails_not_authenticated(
        self, mock_get_client, mock_google_client
    ):
        mock_get_client.return_value = mock_google_client
        mock_google_client.is_authenticated.return_value = False

        input_data = GetEmailsInput(user_id=1)
        with pytest.raises(ValueError, match="User 1 is not authenticated with Google"):
            await get_emails(input_data)


class TestMessagesActivities:
    """Test message building helpers."""

    @pytest.mark.asyncio
    async def test_build_daily_briefing(self):
        today = datetime.now(UTC)
        tomorrow = today + timedelta(days=1)
        event_today = CalendarEvent(
            id="1",
            summary="Today Event",
            start_time=today,
            end_time=today,
        )
        event_tomorrow = CalendarEvent(
            id="2",
            summary="Tomorrow Event",
            start_time=tomorrow,
            end_time=tomorrow,
        )
        forecast = WeatherForecast(
            location="Berlin",
            forecast_date=date.today(),
            weather_code=1,
            temperature_max=25,
            temperature_min=15,
        )
        email = GmailMessage(
            id="m1",
            thread_id="t1",
            snippet="snippet",
            subject="Subject",
            sender="sender@example.com",
            body="Body",
        )

        text = await build_daily_briefing(
            DailyBriefingInput(
                user_id=1,
                today_events=[event_today],
                tomorrow_events=[event_tomorrow],
                weather=forecast,
                emails=[email],
            )
        )

        assert "Today's Events" in text
        assert "Tomorrow's Events" in text
        assert "Weather" in text
        assert "Unread Emails" in text
