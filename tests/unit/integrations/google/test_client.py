"""Tests for Google Client."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from the_assistant.integrations.google.client import (
    GoogleAuthError,
    GoogleCalendarError,
    GoogleClient,
    GoogleGmailError,
)
from the_assistant.models.google import CalendarEvent

# Suppress false positive warnings from mocking async operations
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


class TestGoogleClient:
    """Test Google Client."""

    @pytest.fixture
    def mock_credential_store(self):
        """Mock credential store."""
        store = AsyncMock()
        store.get_credentials.return_value = None
        store.save_credentials.return_value = None
        return store

    @pytest.fixture
    def mock_credentials(self):
        """Mock Google credentials."""
        creds = MagicMock(spec=Credentials)
        creds.valid = True
        creds.expired = False
        creds.refresh_token = "refresh_token"
        creds.token = "access_token"
        creds.to_json.return_value = json.dumps(
            {
                "token": "access_token",
                "refresh_token": "refresh_token",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "client_id",
                "client_secret": "client_secret",
                "scopes": ["https://www.googleapis.com/auth/calendar.readonly"],
            }
        )
        return creds

    @pytest.fixture
    def sample_credentials_json(self):
        """Sample credentials JSON content."""
        return {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8080/google/oauth2callback"],
            }
        }

    def test_init_default_scopes(self, mock_credential_store):
        """Test initialization with default scopes."""
        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        assert client.user_id == 1
        assert client.credential_store == mock_credential_store
        assert client.credentials_path == Path("/path/to/creds.json")
        assert client.scopes == GoogleClient.DEFAULT_SCOPES

    def test_init_custom_scopes(self, mock_credential_store):
        """Test initialization with custom scopes."""
        custom_scopes = ["https://www.googleapis.com/auth/calendar"]
        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
            scopes=custom_scopes,
        )

        assert client.scopes == custom_scopes

    @patch("builtins.open", new_callable=mock_open)
    # Note: _load_client_config is not a public method, removing these tests
    # as they test internal implementation details

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_is_authenticated_no_credentials(
        self, mock_get_credentials, mock_credential_store
    ):
        """Test is_authenticated when no credentials exist."""
        mock_get_credentials.return_value = None

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        result = await client.is_authenticated()
        assert result is False

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_is_authenticated_valid_credentials(
        self, mock_get_credentials, mock_credential_store, mock_credentials
    ):
        """Test is_authenticated with valid credentials."""
        mock_get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        result = await client.is_authenticated()
        assert result is True

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_is_authenticated_expired_credentials(
        self, mock_get_credentials, mock_credential_store, mock_credentials
    ):
        """Test is_authenticated with expired credentials."""
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        result = await client.is_authenticated()
        assert result is False

    @patch("builtins.open", new_callable=mock_open)
    @patch("the_assistant.integrations.google.client.InstalledAppFlow")
    async def test_generate_auth_url_success(
        self, mock_flow_class, mock_file, mock_credential_store, sample_credentials_json
    ):
        """Test successful authorization URL generation."""
        mock_file.return_value.read.return_value = json.dumps(sample_credentials_json)
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://auth.url", "state")
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        auth_url = await client.generate_auth_url(
            "http://localhost:8080/callback", "test_state"
        )

        assert auth_url == "https://auth.url"
        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state="test_state",
        )

    async def test_exchange_code_success(self, mock_credential_store, mock_credentials):
        """Test successful code exchange for credentials."""
        mock_flow = MagicMock()
        mock_flow.fetch_token.return_value = None
        mock_flow.credentials = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )
        client._oauth_flow = mock_flow

        await client.exchange_code("auth_code", "http://localhost:8080/callback")

        # exchange_code doesn't return credentials, it stores them
        mock_flow.fetch_token.assert_called_once_with(code="auth_code")
        mock_credential_store.save.assert_called_once_with(1, mock_credentials)

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_calendar_events_success(
        self, mock_build, mock_credential_store, mock_credentials
    ):
        """Test successful calendar events retrieval."""
        # Mock the Google Calendar API response
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {
            "items": [
                {
                    "id": "event1",
                    "summary": "Test Event",
                    "start": {"dateTime": "2024-01-01T10:00:00Z"},
                    "end": {"dateTime": "2024-01-01T11:00:00Z"},
                    "description": "Test description",
                    "location": "Test location",
                }
            ]
        }

        mock_credential_store.get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        events = await client.get_calendar_events()

        assert len(events) == 1
        assert isinstance(events[0], CalendarEvent)
        assert events[0].id == "event1"
        assert events[0].summary == "Test Event"

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_calendar_events_http_error(
        self, mock_build, mock_credential_store, mock_credentials
    ):
        """Test calendar events retrieval with HTTP error."""
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b'{"error": {"message": "Forbidden"}}'
        )

        mock_credential_store.get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        with pytest.raises(GoogleCalendarError, match="Calendar API error"):
            await client.get_calendar_events()

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_get_calendar_events_not_authenticated(
        self, mock_get_credentials, mock_credential_store
    ):
        """Test calendar events retrieval when not authenticated."""
        mock_get_credentials.return_value = None

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        with pytest.raises(GoogleAuthError, match="No valid credentials available"):
            await client.get_calendar_events()

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_upcoming_events(
        self, mock_build, mock_credential_store, mock_credentials
    ):
        """Test get upcoming events."""
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        mock_credential_store.get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        events = await client.get_upcoming_events(days_ahead=7)

        assert events == []
        # Verify the API was called with correct time range
        call_args = mock_events.list.call_args[1]
        assert "timeMin" in call_args
        assert "timeMax" in call_args

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_emails_success(
        self, mock_build, mock_credential_store, mock_credentials
    ):
        """Test successful Gmail messages retrieval."""
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()
        mock_list = MagicMock()
        mock_get = MagicMock()

        mock_build.return_value = mock_service
        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages
        mock_messages.list.return_value = mock_list
        mock_list.execute.return_value = {"messages": [{"id": "m1"}]}
        mock_messages.get.return_value = mock_get
        mock_get.execute.return_value = {
            "id": "m1",
            "threadId": "t1",
            "snippet": "hi",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "user@example.com"},
                    {"name": "Date", "value": "2024-01-01T10:00:00Z"},
                ]
            },
            "labelIds": ["UNREAD"],
        }

        mock_credential_store.get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        emails = await client.get_emails(unread_only=True, sender="sender@example.com")

        assert len(emails) == 1
        assert emails[0].subject == "Test"
        call_args = mock_messages.list.call_args[1]
        assert "q" in call_args
        assert (
            "is:unread" in call_args["q"]
            and "from:sender@example.com" in call_args["q"]
        )

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_emails_http_error(
        self, mock_build, mock_credential_store, mock_credentials
    ):
        """Test Gmail retrieval with HTTP error."""
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages
        mock_messages.list.return_value = mock_list
        mock_list.execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b"{}"
        )

        mock_credential_store.get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        with pytest.raises(GoogleGmailError, match="Gmail API error"):
            await client.get_emails()

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_get_emails_not_authenticated(
        self, mock_get_credentials, mock_credential_store
    ):
        """Test Gmail retrieval when not authenticated."""
        mock_get_credentials.return_value = None

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        with pytest.raises(GoogleAuthError, match="No valid credentials available"):
            await client.get_emails()

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_events_by_date(
        self, mock_build, mock_credential_store, mock_credentials
    ):
        """Test get events by specific date."""
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        mock_credential_store.get_credentials.return_value = mock_credentials

        client = GoogleClient(
            user_id=1,
            credential_store=mock_credential_store,
            credentials_path="/path/to/creds.json",
        )

        target_date = datetime(2024, 1, 1, tzinfo=UTC)
        events = await client.get_events_by_date(target_date)

        assert events == []
        # Verify the API was called with correct date range
        call_args = mock_events.list.call_args[1]
        assert "timeMin" in call_args
        assert "timeMax" in call_args
