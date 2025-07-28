from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from the_assistant.db import get_user_service
from the_assistant.integrations.ticktick.token_store import TickTickTokenStore
from the_assistant.models.ticktick import TickTask, TickToken
from the_assistant.settings import get_settings

logger = logging.getLogger(__name__)


class TickTickClient:
    """Minimal client for the TickTick Open API."""

    BASE_URL = "https://api.ticktick.com/open/v1"
    AUTH_BASE_URL = "https://ticktick.com/oauth/authorize"
    TOKEN_URL = "https://ticktick.com/oauth/token"

    def __init__(self, user_id: int, account: str | None = None) -> None:
        self.user_id = user_id
        self.account = account or "default"
        settings = get_settings()
        self.client_id = settings.ticktick_client_id
        self.client_secret = settings.ticktick_client_secret
        self.redirect_uri = settings.ticktick_oauth_redirect_uri
        self.scopes = settings.ticktick_oauth_scopes
        self._token_store = TickTickTokenStore(
            encryption_key=settings.db_encryption_key,
            account=self.account,
            user_service=get_user_service(),
        )

    async def _get_token(self) -> TickToken:
        token = await self._token_store.get(self.user_id)
        if token is None:
            raise ValueError("TickTick access token not configured")
        if token.is_expired:
            token = await self._refresh_token(token)
        return token

    async def _refresh_token(self, token: TickToken) -> TickToken:
        if not token.refresh_token:
            raise ValueError("Cannot refresh expired token: no refresh_token available.")
        data = {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            payload = resp.json()
        new_token = TickToken.from_token_response(payload)
        # API may not return refresh_token on refresh
        if new_token.refresh_token is None:
            new_token.refresh_token = token.refresh_token
        await self._token_store.save(self.user_id, new_token)
        return new_token

    async def generate_auth_url(self, state: str | None = None) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
        }
        if state:
            params["state"] = state
        return f"{self.AUTH_BASE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> None:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            payload = resp.json()
        token = TickToken.from_token_response(payload)
        await self._token_store.save(self.user_id, token)

    async def _request(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token.access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}{path}", params=params, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def is_authenticated(self) -> bool:
        """Return ``True`` if the user has a valid token."""
        token = await self._token_store.get(self.user_id)
        return token is not None and not token.is_expired

    async def get_tasks_for_date(self, day: date) -> list[TickTask]:
        payload = await self._request(
            "/task",
            {"startDate": day.isoformat(), "endDate": day.isoformat()},
        )
        return [TickTask.from_ticktask(item) for item in payload]

    async def get_tasks_ahead(self, days: int = 7) -> list[TickTask]:
        start = datetime.now(UTC).date()
        end = start + timedelta(days=days - 1)
        payload = await self._request(
            "/task",
            {"startDate": start.isoformat(), "endDate": end.isoformat()},
        )
        return [TickTask.from_ticktask(item) for item in payload]
