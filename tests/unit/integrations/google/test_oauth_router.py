import importlib
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


def test_missing_jwt_secret_no_error():
    """Importing oauth_router without JWT_SECRET should not fail."""
    with patch.dict(os.environ, {}, clear=True):
        import the_assistant.integrations.google.oauth_router as oauth_router

        importlib.reload(oauth_router)


@pytest.mark.asyncio
async def test_oauth_callback_sends_notification():
    """OAuth callback notifies the user via Telegram."""

    import the_assistant.integrations.google.oauth_router as oauth_router

    user = SimpleNamespace(id=1, telegram_chat_id=456)
    service = AsyncMock()
    service.get_user_by_id = AsyncMock(return_value=user)

    google_client = AsyncMock()
    telegram_client = AsyncMock()

    settings = SimpleNamespace(
        google_oauth_redirect_uri="http://redir",
        jwt_secret="secret",
    )
    state = oauth_router.create_state_jwt(user.id, settings)

    with (
        patch(
            "the_assistant.integrations.google.oauth_router.get_user_service",
            return_value=service,
        ),
        patch(
            "the_assistant.integrations.google.oauth_router.GoogleClient",
            return_value=google_client,
        ),
        patch(
            "the_assistant.integrations.google.oauth_router.TelegramClient",
            return_value=telegram_client,
        ),
    ):
        await oauth_router.google_oauth_callback(
            code="code",
            state=state,
            error=None,
            settings=settings,
        )

    google_client.exchange_code.assert_awaited_once_with("code")
    telegram_client.send_message.assert_awaited_once_with(
        chat_id=456, text="✅ Google authentication successful!"
    )
