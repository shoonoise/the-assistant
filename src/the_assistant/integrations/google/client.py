"""
Google Client - Headless OAuth2 implementation for containers.

This implementation works with CredentialStore and supports web-based OAuth2 flow
without requiring a browser in the container.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request  # type: ignore[import-untyped]
from google.oauth2.credentials import Credentials  # type: ignore[import-untyped]
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from the_assistant.integrations.google.credential_store import (
    PostgresCredentialStore,
)
from the_assistant.models.google import CalendarEvent, GmailMessage
from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


class GoogleAuthError(Exception):
    """Google authentication failed."""

    pass


class GoogleCalendarError(Exception):
    """Google Calendar operation failed."""

    pass


class GoogleGmailError(Exception):
    """Google Gmail operation failed."""

    pass


class GoogleClient:
    """
    Google API client for headless containers with CredentialStore support.

    Supports web-based OAuth2 flow where users authenticate via browser
    and the container receives the authorization code via webhook.
    """

    def __init__(
        self,
        user_id: int,
    ):
        """
        Initialize the Google client.

        Args:
            user_id: Database user ID
        """
        self.user_id = user_id
        self.settings = get_settings()

        self.credential_store = PostgresCredentialStore(
            database_url=self.settings.database_url,
            encryption_key=self.settings.db_encryption_key,
        )
        self.credentials_path = self.settings.google_credentials_path
        self.scopes = self.settings.google_oauth_scopes

        self._credentials: Credentials | None = None
        self._calendar_service: Any = None
        self._gmail_service: Any = None
        self._oauth_flow: InstalledAppFlow | None = None

    async def generate_auth_url(
        self, redirect_uri: str, state: str | None = None
    ) -> str:
        """
        Generate OAuth2 authorization URL for web-based flow.

        Args:
            redirect_uri: URI where Google will redirect after consent
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL for user to visit
        """
        try:
            # Create and store the flow for later use in exchange_code
            self._oauth_flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path), self.scopes
            )

            # Set the redirect URI
            self._oauth_flow.redirect_uri = redirect_uri

            # Generate authorization URL
            auth_url, _ = self._oauth_flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",  # Force consent screen to get refresh token
                state=state,
            )

            return auth_url

        except Exception as e:
            logger.error(f"Failed to generate auth URL: {e}")
            raise GoogleAuthError(f"Failed to generate auth URL: {e}") from e

    async def exchange_code(self, code: str, redirect_uri: str) -> None:
        """
        Exchange authorization code for credentials and store them.

        Args:
            code: Authorization code from Google
            redirect_uri: Must match the one used in generate_auth_url
        """
        try:
            # Use the same flow instance that was used to generate the auth URL
            if self._oauth_flow is None:
                # Fallback: create new flow if not available
                self._oauth_flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), self.scopes
                )
                self._oauth_flow.redirect_uri = redirect_uri

            # Exchange code for credentials
            self._oauth_flow.fetch_token(code=code)

            # Store credentials
            creds = self._oauth_flow.credentials
            logger.info(f"Credentials after exchange for user {self.user_id}:")
            logger.info(f"  - valid: {creds.valid}")
            logger.info(f"  - expired: {creds.expired}")
            logger.info(f"  - has_token: {bool(creds.token)}")
            logger.info(f"  - has_refresh_token: {bool(creds.refresh_token)}")
            logger.info(f"  - scopes: {creds.scopes}")

            await self.credential_store.save(self.user_id, creds)

            # Update local credentials
            self._credentials = creds

            # Clear the flow instance
            self._oauth_flow = None

            logger.info(f"Successfully exchanged code for user {self.user_id}")

        except Exception as e:
            logger.error(f"Failed to exchange code: {e}")
            raise GoogleAuthError(f"Failed to exchange code: {e}") from e

    async def get_credentials(self) -> Credentials | None:
        """
        Get stored credentials, refreshing if needed.

        Returns:
            Valid credentials or None if not available
        """
        try:
            # Get credentials from store
            credentials = await self.credential_store.get(self.user_id)

            if not credentials:
                return None

            # Check if credentials need refresh
            logger.info(
                f"Credentials status for user {self.user_id}: expired={credentials.expired}, has_refresh_token={bool(credentials.refresh_token)}"
            )

            if credentials.expired and credentials.refresh_token:
                logger.info(
                    f"Attempting to refresh credentials for user {self.user_id}"
                )
                try:
                    credentials.refresh(Request())
                    logger.info(
                        f"Successfully refreshed credentials for user {self.user_id}, new valid status: {credentials.valid}"
                    )
                    # Save refreshed credentials
                    await self.credential_store.save(self.user_id, credentials)
                    logger.info(f"Saved refreshed credentials for user {self.user_id}")
                except Exception as e:
                    logger.error(
                        f"Failed to refresh credentials for user {self.user_id}: {e}"
                    )
                    # Delete invalid credentials
                    await self.credential_store.delete(self.user_id)
                    return None
            elif credentials.expired and not credentials.refresh_token:
                logger.error(
                    f"Credentials expired for user {self.user_id} but no refresh token available"
                )
                await self.credential_store.delete(self.user_id)
                return None

            self._credentials = credentials
            return credentials

        except Exception as e:
            logger.error(f"Failed to get credentials for user {self.user_id}: {e}")
            return None

    async def _get_calendar_service(self) -> Any:
        """Get the Google Calendar API service instance."""
        if self._calendar_service is None:
            if not self._credentials:
                self._credentials = await self.get_credentials()
                if not self._credentials:
                    raise GoogleAuthError("No valid credentials available")

            try:
                self._calendar_service = build(
                    "calendar", "v3", credentials=self._credentials
                )
            except Exception as e:
                raise GoogleCalendarError(
                    f"Failed to create calendar service: {e}"
                ) from e

        return self._calendar_service

    async def _get_gmail_service(self) -> Any:
        """Get the Gmail API service instance."""
        if self._gmail_service is None:
            if not self._credentials:
                self._credentials = await self.get_credentials()
                if not self._credentials:
                    raise GoogleAuthError("No valid credentials available")

            try:
                self._gmail_service = build(
                    "gmail", "v1", credentials=self._credentials
                )
            except Exception as e:
                raise GoogleGmailError(f"Failed to create gmail service: {e}") from e

        return self._gmail_service

    async def get_calendar_events(
        self,
        calendar_id: str = "primary",
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        """
        Retrieve calendar events.

        Args:
            calendar_id: Calendar ID to retrieve events from
            time_min: Minimum time for events (default: now)
            time_max: Maximum time for events
            max_results: Maximum number of events to return

        Returns:
            List of calendar events

        Raises:
            GoogleCalendarError: If calendar operation fails
        """
        # Ensure we have valid credentials
        credentials = await self.get_credentials()
        if not credentials:
            raise GoogleAuthError("No valid credentials available")
        self._credentials = credentials
        try:
            if time_min is None:
                time_min = datetime.now(UTC)

            request_params = {
                "calendarId": calendar_id,
                "timeMin": time_min.isoformat(),
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime",
            }

            if time_max:
                request_params["timeMax"] = time_max.isoformat()

            logger.debug(f"Fetching events from calendar {calendar_id}")

            service = await self._get_calendar_service()
            events_result = service.events().list(**request_params).execute()
            raw_events = events_result.get("items", [])

            # Parse events into simplified format
            events = []
            for raw_event in raw_events:
                try:
                    event = self._parse_calendar_event(raw_event, calendar_id)
                    events.append(event)
                except Exception as e:
                    event_id = raw_event.get("id", "unknown")
                    logger.warning(f"Failed to parse event {event_id}: {e}")
                    continue

            logger.info(f"Retrieved {len(events)} events from calendar {calendar_id}")
            return events

        except HttpError as e:
            error_msg = f"Calendar API error: {e}"
            logger.error(error_msg)
            raise GoogleCalendarError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to retrieve calendar events: {e}"
            logger.error(error_msg)
            raise GoogleCalendarError(error_msg) from e

    async def get_upcoming_events(
        self, days_ahead: int = 30, calendar_id: str = "primary"
    ) -> list[CalendarEvent]:
        """
        Get upcoming events within the specified number of days.

        Args:
            days_ahead: Number of days ahead to search
            calendar_id: Calendar ID to retrieve events from

        Returns:
            List of upcoming calendar events
        """
        time_max = datetime.now(UTC) + timedelta(days=days_ahead)
        return await self.get_calendar_events(
            calendar_id=calendar_id, time_max=time_max, max_results=100
        )

    async def get_events_by_date(
        self, target_date: datetime, calendar_id: str = "primary"
    ) -> list[CalendarEvent]:
        """
        Retrieve events for a specific date.

        Args:
            target_date: Date to retrieve events for
            calendar_id: Calendar ID to retrieve events from

        Returns:
            List of calendar events for the specified date
        """
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return await self.get_calendar_events(
            calendar_id=calendar_id,
            time_min=start_of_day,
            time_max=end_of_day,
            max_results=100,
        )

    def _parse_calendar_event(
        self, raw_event: dict[str, Any], calendar_id: str = "primary"
    ) -> CalendarEvent:
        """Parse raw Google Calendar event into CalendarEvent model."""
        # Extract basic information
        event_id = raw_event.get("id", "")
        summary = raw_event.get("summary", "")
        description = raw_event.get("description", "")
        location = raw_event.get("location", "")

        # Parse start and end times
        start_time = self._parse_event_time(raw_event.get("start", {}))
        end_time = self._parse_event_time(raw_event.get("end", {}))

        # Check if all-day event
        is_all_day = "date" in raw_event.get("start", {})

        # Extract attendees
        attendees = []
        for raw_attendee in raw_event.get("attendees", []):
            attendee = {
                "email": raw_attendee.get("email", ""),
                "display_name": raw_attendee.get("displayName"),
                "response_status": raw_attendee.get("responseStatus", "needsAction"),
                "is_organizer": raw_attendee.get("organizer", False),
            }
            attendees.append(attendee)

        return CalendarEvent(
            id=event_id,
            summary=summary,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            calendar_id=calendar_id,
            attendees=attendees,
            is_all_day=is_all_day,
            raw_data=raw_event,
        )

    def _parse_event_time(self, event_time: dict[str, Any]) -> datetime:
        """Parse event time from Google Calendar format."""
        if not event_time:
            return datetime.now(UTC)

        # Handle datetime format (timed events)
        if "dateTime" in event_time:
            datetime_str = event_time["dateTime"]
            return self._parse_datetime_string(datetime_str)

        # Handle date format (all-day events)
        elif "date" in event_time:
            date_str = event_time["date"]
            return self._parse_date_string(date_str)

        return datetime.now(UTC)

    def _parse_datetime_string(self, datetime_str: str) -> datetime:
        """Parse datetime string with timezone support."""
        try:
            # Handle UTC format (Z suffix)
            if datetime_str.endswith("Z"):
                return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))

            # Handle timezone offset format
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            # Fallback: try parsing without timezone
            try:
                dt = datetime.fromisoformat(datetime_str.split("+")[0].split("-")[0])
                return dt.replace(tzinfo=UTC)
            except ValueError:
                return datetime.now(UTC)

    def _parse_date_string(self, date_str: str) -> datetime:
        """Parse date string for all-day events."""
        try:
            date_obj = datetime.fromisoformat(date_str)
            return date_obj.replace(tzinfo=UTC)
        except ValueError:
            return datetime.now(UTC)

    async def is_authenticated(self) -> bool:
        """Check if the user has valid credentials."""
        credentials = await self.get_credentials()
        logger.info(
            f"is_authenticated for user {self.user_id}: credentials={credentials is not None}, valid={credentials.valid if credentials else False}"
        )
        return credentials is not None and credentials.valid

    async def get_emails(
        self,
        unread_only: bool | None = None,
        sender: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
        max_results: int = 10,
    ) -> list[GmailMessage]:
        """Retrieve emails from the user's Gmail inbox."""

        credentials = await self.get_credentials()
        if not credentials:
            raise GoogleAuthError("No valid credentials available")
        self._credentials = credentials
        query_parts: list[str] = []
        if unread_only is True:
            query_parts.append("is:unread")
        elif unread_only is False:
            query_parts.append("is:read")

        if sender:
            query_parts.append(f"from:{sender}")

        if after:
            query_parts.append(after.strftime("after:%Y/%m/%d"))
        if before:
            query_parts.append(before.strftime("before:%Y/%m/%d"))

        query = " ".join(query_parts)

        try:
            service = await self._get_gmail_service()
            list_kwargs = {"userId": "me", "maxResults": max_results}
            if query:
                list_kwargs["q"] = query
            messages_result = service.users().messages().list(**list_kwargs).execute()
            message_items = messages_result.get("messages", [])

            emails: list[GmailMessage] = []
            for item in message_items:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=item["id"], format="full")
                    .execute()
                )
                try:
                    emails.append(self._parse_gmail_message(msg))
                except Exception as parse_err:  # pragma: no cover - safeguard
                    logger.warning(
                        f"Failed to parse gmail message {item.get('id')}: {parse_err}"
                    )
            return emails
        except HttpError as e:
            error_msg = f"Gmail API error: {e}"
            logger.error(error_msg)
            raise GoogleGmailError(error_msg) from e
        except Exception as e:  # pragma: no cover - unexpected
            error_msg = f"Failed to retrieve gmail messages: {e}"
            logger.error(error_msg)
            raise GoogleGmailError(error_msg) from e

    def _parse_gmail_message(self, raw_message: dict[str, Any]) -> GmailMessage:
        """Parse raw Gmail API message into GmailMessage model."""

        headers = {
            h["name"].lower(): h["value"]
            for h in raw_message.get("payload", {}).get("headers", [])
        }

        subject = headers.get("subject", "")
        sender = headers.get("from", "")
        to = headers.get("to", "")
        date_str = headers.get("date")
        msg_date = None
        if date_str:
            try:
                msg_date = self._parse_datetime_string(date_str)
            except Exception:  # pragma: no cover - fallback
                msg_date = None

        return GmailMessage(
            id=raw_message.get("id", ""),
            thread_id=raw_message.get("threadId", ""),
            snippet=raw_message.get("snippet", ""),
            subject=subject,
            sender=sender,
            to=to,
            date=msg_date,
            raw_data=raw_message,
        )


if __name__ == "__main__":
    client = GoogleClient(user_id=1)
    emails = asyncio.run(client.get_emails())
    print(emails)

    events = asyncio.run(client.get_calendar_events())
    print(events)
