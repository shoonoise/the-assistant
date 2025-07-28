"""FastAPI router for TickTick OAuth2 endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from ...db import get_user_service
from ...settings import Settings, get_settings
from ..google.oauth_state import create_state_jwt, parse_state_jwt
from ..telegram.telegram_client import TelegramClient
from .ticktick_client import TickTickClient
from .token_store import TickTickTokenStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ticktick", tags=["ticktick"])


def get_token_store(
    settings: Settings = Depends(get_settings),
    account: str | None = Query(None, description="TickTick account identifier"),
) -> TickTickTokenStore:
    return TickTickTokenStore(
        encryption_key=settings.db_encryption_key,
        account=account,
    )


def get_ticktick_client(
    user_id: int = Query(..., description="User ID"),
    account: str | None = Query(None, description="TickTick account identifier"),
) -> TickTickClient:
    return TickTickClient(user_id=user_id, account=account)


@router.get("/auth")
async def begin_ticktick_auth(
    user_id: int = Query(..., description="User ID"),
    account: str | None = Query(None, description="TickTick account identifier"),
    client: TickTickClient = Depends(get_ticktick_client),
    settings: Settings = Depends(get_settings),
):
    try:
        if await client.is_authenticated():
            return {"message": "User already authenticated", "authenticated": True}
        state = create_state_jwt(user_id, settings, account=account)
        auth_url = await client.generate_auth_url(state)
        return {"auth_url": auth_url, "authenticated": False}
    except (ValueError, HTTPError) as e:
        logger.error(f"Failed to start auth flow: {e}")
        raise HTTPException(status_code=500, detail="Failed to start auth flow") from e


@router.get("/oauth2callback")
async def ticktick_oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State token"),
    error: str | None = Query(None, description="OAuth error"),
    settings: Settings = Depends(get_settings),
):
    if error:
        return RedirectResponse(url="/auth-error?error=oauth_error", status_code=302)
    user_id, account = parse_state_jwt(state, settings)
    if not user_id:
        return RedirectResponse(url="/auth-error?error=invalid_state", status_code=302)
    client = TickTickClient(user_id=user_id, account=account)
    try:
        await client.exchange_code(code)
        user_service = get_user_service()
        user = await user_service.get_user_by_id(user_id)
        if user and user.telegram_chat_id:
            try:
                tg_client = TelegramClient(user_id=user_id)
                await tg_client.send_message(
                    text="✅ TickTick authentication successful!"
                )
            except Exception as notify_err:  # pragma: no cover - log only
                logger.error(
                    f"Failed to send Telegram notification for user {user_id}: {notify_err}"
                )
        return RedirectResponse(url="/auth-success", status_code=302)
    except Exception as e:
        logger.error(f"Failed to exchange code: {e}")
        return RedirectResponse(
            url="/auth-error?error=exchange_failed", status_code=302
        )


@router.get("/status")
async def check_auth_status(
    user_id: int = Query(..., description="User ID"),
    account: str | None = Query(None, description="TickTick account identifier"),
    client: TickTickClient = Depends(get_ticktick_client),
):
    try:
        return {"authenticated": await client.is_authenticated(), "user_id": user_id}
    except (ValueError, HTTPError) as e:
        logger.error(f"Failed to check auth status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to check auth status"
        ) from e


@router.delete("/revoke")
async def revoke_auth(
    user_id: int = Query(..., description="User ID"),
    account: str | None = Query(None, description="TickTick account identifier"),
    store: TickTickTokenStore = Depends(get_token_store),
):
    try:
        await store.delete(user_id)
        return {"message": "TickTick authentication revoked", "user_id": user_id}
    except Exception as e:
        logger.error(f"Failed to revoke auth due to {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke auth") from e
