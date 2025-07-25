"""Tests for Google Client."""

import base64
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


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock application settings."""
    settings = MagicMock()
    settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
    settings.db_encryption_key = "test_key"
    settings.google_credentials_path = Path("/path/to/creds.json")
    settings.google_oauth_scopes = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    monkeypatch.setattr(
        "the_assistant.integrations.google.client.get_settings", lambda: settings
    )
    return settings


@pytest.fixture
def mock_credential_store_class(monkeypatch):
    """Mock PostgresCredentialStore class."""
    mock_store_class = MagicMock()
    mock_store_instance = AsyncMock()
    mock_store_class.return_value = mock_store_instance
    monkeypatch.setattr(
        "the_assistant.integrations.google.client.PostgresCredentialStore",
        mock_store_class,
    )
    return mock_store_class, mock_store_instance


@pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
class TestGoogleClient:
    """Test Google Client."""

    @pytest.fixture(autouse=True)
    def setup(self, mock_settings, mock_credential_store_class):
        """Auto-setup for all tests in this class."""
        self.mock_settings = mock_settings
        self.mock_store_class, self.mock_store_instance = mock_credential_store_class

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
        creds.refresh.return_value = None
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

    def test_init(self):
        """Test initialization of GoogleClient."""
        client = GoogleClient(user_id=1)

        assert client.user_id == 1
        assert client.settings == self.mock_settings
        self.mock_store_class.assert_called_once_with(
            encryption_key=self.mock_settings.db_encryption_key,
            account=None,
        )
        assert client.credential_store == self.mock_store_instance
        assert client.credentials_path == self.mock_settings.google_credentials_path
        assert client.scopes == self.mock_settings.google_oauth_scopes

    def test_init_with_account(self):
        """GoogleClient forwards account to credential store."""
        client = GoogleClient(user_id=1, account="personal")

        self.mock_store_class.assert_called_with(
            encryption_key=self.mock_settings.db_encryption_key,
            account="personal",
        )
        assert client.account == "personal"

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_is_authenticated_no_credentials(self, mock_get_credentials):
        """Test is_authenticated when no credentials exist."""
        mock_get_credentials.return_value = None

        client = GoogleClient(user_id=1)

        result = await client.is_authenticated()
        assert result is False

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_is_authenticated_valid_credentials(
        self, mock_get_credentials, mock_credentials
    ):
        """Test is_authenticated with valid credentials."""
        mock_get_credentials.return_value = mock_credentials

        client = GoogleClient(user_id=1)

        result = await client.is_authenticated()
        assert result is True

    @patch("the_assistant.integrations.google.client.GoogleClient.get_credentials")
    async def test_is_authenticated_expired_credentials(
        self, mock_get_credentials, mock_credentials
    ):
        """Test is_authenticated with expired credentials."""
        mock_credentials.valid = False
        mock_credentials.expired = True
        mock_get_credentials.return_value = mock_credentials

        client = GoogleClient(user_id=1)

        result = await client.is_authenticated()
        assert result is False

    @patch("builtins.open", new_callable=mock_open)
    @patch("the_assistant.integrations.google.client.InstalledAppFlow")
    async def test_generate_auth_url_success(
        self, mock_flow_class, mock_file, sample_credentials_json
    ):
        """Test successful authorization URL generation."""
        mock_file.return_value.read.return_value = json.dumps(sample_credentials_json)
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://auth.url", "state")
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        client = GoogleClient(user_id=1)

        auth_url = await client.generate_auth_url("test_state")

        assert auth_url == "https://auth.url"
        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state="test_state",
        )
        mock_flow_class.from_client_secrets_file.assert_called_with(
            str(self.mock_settings.google_credentials_path),
            self.mock_settings.google_oauth_scopes,
        )

    @patch("the_assistant.integrations.google.client.InstalledAppFlow")
    async def test_exchange_code_success(self, mock_flow_class, mock_credentials):
        """Test successful code exchange for credentials."""
        mock_flow = MagicMock()
        mock_flow.fetch_token.return_value = None
        mock_flow.credentials = mock_credentials
        mock_flow_class.from_client_secrets_file.return_value = mock_flow

        client = GoogleClient(user_id=1)
        # client._oauth_flow should be set by generate_auth_url
        # We manually set it here for isolated testing
        client._oauth_flow = mock_flow

        await client.exchange_code("auth_code")

        mock_flow.fetch_token.assert_called_once_with(code="auth_code")
        self.mock_store_instance.save.assert_called_once_with(1, mock_credentials)

    @patch("the_assistant.integrations.google.client.Request")
    async def test_get_credentials_success_no_refresh(
        self, mock_request, mock_credentials
    ):
        """Test get_credentials with valid, non-expired credentials."""
        self.mock_store_instance.get.return_value = mock_credentials
        mock_credentials.expired = False

        client = GoogleClient(user_id=1)
        credentials = await client.get_credentials()

        assert credentials == mock_credentials
        self.mock_store_instance.get.assert_called_once_with(1)
        mock_credentials.refresh.assert_not_called()
        self.mock_store_instance.save.assert_not_called()

    @patch("the_assistant.integrations.google.client.Request")
    async def test_get_credentials_success_with_refresh(
        self, mock_request, mock_credentials
    ):
        """Test get_credentials with expired credentials that are refreshed."""
        self.mock_store_instance.get.return_value = mock_credentials
        mock_credentials.expired = True
        mock_credentials.refresh_token = "some-refresh-token"

        client = GoogleClient(user_id=1)
        credentials = await client.get_credentials()

        assert credentials == mock_credentials
        self.mock_store_instance.get.assert_called_once_with(1)
        mock_credentials.refresh.assert_called_once_with(mock_request())
        self.mock_store_instance.save.assert_called_once_with(1, mock_credentials)

    async def test_get_credentials_not_found(self):
        """Test get_credentials when no credentials are in the store."""
        self.mock_store_instance.get.return_value = None

        client = GoogleClient(user_id=1)
        credentials = await client.get_credentials()

        assert credentials is None
        self.mock_store_instance.get.assert_called_once_with(1)

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_calendar_events_success(self, mock_build, mock_credentials):
        """Test successful calendar events retrieval."""
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

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            events = await client.get_calendar_events()

            assert len(events) == 1
            assert isinstance(events[0], CalendarEvent)
            assert events[0].id == "event1"
            assert events[0].summary == "Test Event"
            mock_build.assert_called_once_with(
                "calendar", "v3", credentials=mock_credentials
            )

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_calendar_events_http_error(self, mock_build, mock_credentials):
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

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            with pytest.raises(GoogleCalendarError, match="Calendar API error"):
                await client.get_calendar_events()

    async def test_get_calendar_events_not_authenticated(self):
        """Test calendar events retrieval when not authenticated."""
        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = None

            with pytest.raises(GoogleAuthError, match="No valid credentials available"):
                await client.get_calendar_events()

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_upcoming_events(self, mock_build, mock_credentials):
        """Test get upcoming events."""
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            events = await client.get_upcoming_events(days_ahead=7)

            assert events == []
            # Verify the API was called with correct time range
            call_args = mock_events.list.call_args[1]
            assert "timeMin" in call_args
            assert "timeMax" in call_args

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_emails_success(self, mock_build, mock_credentials):
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

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            emails = await client.get_emails(
                unread_only=True,
                sender="sender@example.com",
                ignored_senders=None,
            )

            assert len(emails) == 1
            assert emails[0].subject == "Test"
            call_args = mock_messages.list.call_args[1]
            assert "q" in call_args
            assert (
                "is:unread" in call_args["q"]
                and "from:sender@example.com" in call_args["q"]
            )
            mock_build.assert_called_once_with(
                "gmail", "v1", credentials=mock_credentials
            )

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_emails_ignored(self, mock_build, mock_credentials):
        """Emails from ignored senders are filtered out."""
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
                    {"name": "From", "value": "spam@news.com"},
                ]
            },
        }

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            emails = await client.get_emails(ignored_senders=["*@news.com"])

            assert emails == []

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_emails_http_error(self, mock_build, mock_credentials):
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

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            with pytest.raises(GoogleGmailError, match="Gmail API error"):
                await client.get_emails(ignored_senders=None)

    async def test_get_emails_not_authenticated(self):
        """Test Gmail retrieval when not authenticated."""
        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = None

            with pytest.raises(GoogleAuthError, match="No valid credentials available"):
                await client.get_emails(ignored_senders=None)

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_events_by_date(self, mock_build, mock_credentials):
        """Test get events by specific date."""
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            target_date = datetime(2024, 1, 1, tzinfo=UTC)
            events = await client.get_events_by_date(target_date)

            assert events == []
            # Verify the API was called with correct date range
            call_args = mock_events.list.call_args[1]
            assert "timeMin" in call_args
            assert "timeMax" in call_args

    @patch("the_assistant.integrations.google.client.build")
    async def test_get_important_emails(self, mock_build, mock_credentials):
        """Test retrieval of important emails."""
        mock_service = MagicMock()
        mock_users = MagicMock()
        mock_messages = MagicMock()
        mock_list = MagicMock()
        mock_get = MagicMock()

        mock_build.return_value = mock_service
        mock_service.users.return_value = mock_users
        mock_users.messages.return_value = mock_messages
        mock_messages.list.return_value = mock_list
        mock_list.execute.return_value = {
            "messages": [{"id": "m1"}],
            "resultSizeEstimate": 1,
        }
        mock_messages.get.return_value = mock_get
        mock_get.execute.return_value = {
            "id": "m1",
            "threadId": "t1",
            "snippet": "hi",
            "payload": {"headers": []},
        }

        client = GoogleClient(user_id=1)
        with patch.object(
            client, "get_credentials", new_callable=AsyncMock
        ) as mock_get_credentials:
            mock_get_credentials.return_value = mock_credentials
            emails, total = await client.get_important_emails(
                max_results=5, ignored_senders=None
            )

            assert total == 1
            assert len(emails) == 1
            call_args = mock_messages.list.call_args[1]
            assert "is:important" in call_args["q"]


def test_extract_message_body_html_conversion():
    """HTML bodies are converted to plain text and trimmed."""
    client = GoogleClient.__new__(GoogleClient)
    html = "<p>Hello<br>world</p>"
    data = base64.urlsafe_b64encode(html.encode()).decode()
    payload = {"parts": [{"mimeType": "text/html", "body": {"data": data}}]}

    result = client._extract_message_body(payload)
    assert "Hello" in result
    assert "world" in result
    assert "<" not in result


@pytest.mark.parametrize(
    "mask,sender",
    [
        ("*sender@domain.com", "foo_sender@domain.com"),
        ("sender@domain.*", "sender@domain.org"),
        ("full_name@fulldomain.com", "Full Name <full_name@fulldomain.com>"),
    ],
)
def test_sender_matches_various_patterns(mask: str, sender: str) -> None:
    """_sender_matches handles different glob patterns."""
    client = GoogleClient.__new__(GoogleClient)

    assert client._sender_matches(sender, [mask])
