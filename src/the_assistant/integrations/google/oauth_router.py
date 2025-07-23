"""
FastAPI router for Google OAuth2 endpoints.
"""

import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from ...settings import Settings, get_settings
from .client import GoogleAuthError, GoogleClient
from .credential_store import PostgresCredentialStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google", tags=["google"])


def get_credential_store(
    settings: Settings = Depends(get_settings),
) -> PostgresCredentialStore:
    """Dependency to get credential store."""
    return PostgresCredentialStore(settings.database_url, settings.db_encryption_key)


def get_google_client(
    user_id: int = Query(..., description="User ID"),
) -> GoogleClient:
    """Dependency to get Google client for a user."""
    return GoogleClient(user_id=user_id)


def create_state_jwt(user_id: int, settings: Settings) -> str:
    """Create a JWT state token for OAuth2 flow."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=10),  # 10 min expiry
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def parse_state_jwt(state: str, settings: Settings) -> int | None:
    """Parse and validate JWT state token."""
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        logger.warning("State token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid state token")
        return None


@router.get("/auth")
async def begin_google_auth(
    user_id: int = Query(..., description="User ID"),
    client: GoogleClient = Depends(get_google_client),
    settings: Settings = Depends(get_settings),
):
    """
    Start Google OAuth2 flow.

    Returns an authorization URL that the user should visit in their browser.
    """
    try:
        # Check if user is already authenticated
        if await client.is_authenticated():
            return {"message": "User already authenticated", "authenticated": True}

        # Generate authorization URL with state
        redirect_uri = settings.google_oauth_redirect_uri
        state = create_state_jwt(user_id, settings)
        auth_url = await client.generate_auth_url(redirect_uri, state)

        return {
            "auth_url": auth_url,
            "authenticated": False,
            "message": "Visit the auth_url in your browser to authenticate",
        }

    except GoogleAuthError as e:
        logger.error(f"Failed to generate auth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error in auth flow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/oauth2callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token"),
    error: str | None = Query(None, description="OAuth error from Google"),
    settings: Settings = Depends(get_settings),
):
    """
    Handle Google OAuth2 callback.

    This endpoint receives the authorization code from Google after user consent.
    """
    try:
        # Check for OAuth errors
        if error:
            logger.error(f"OAuth error from Google: {error}")
            return RedirectResponse(
                url="/auth-error?error=oauth_error", status_code=302
            )

        # Parse state token
        user_id = parse_state_jwt(state, settings)
        if not user_id:
            logger.error("Invalid or expired state token")
            return RedirectResponse(
                url="/auth-error?error=invalid_state", status_code=302
            )

        # Get client for this user
        client = GoogleClient(user_id=user_id)

        # Exchange code for credentials
        redirect_uri = settings.google_oauth_redirect_uri
        await client.exchange_code(code, redirect_uri)

        logger.info(f"Successfully authenticated user {user_id}")

        # Redirect to success page
        return RedirectResponse(url="/auth-success", status_code=302)

    except GoogleAuthError as e:
        logger.error(f"Failed to exchange code: {e}")
        return RedirectResponse(
            url=f"/auth-error?error=exchange_failed&message={str(e)}", status_code=302
        )
    except Exception as e:
        logger.error(f"Unexpected error in callback: {e}")
        return RedirectResponse(url="/auth-error?error=internal_error", status_code=302)


@router.get("/status")
async def check_auth_status(
    user_id: int = Query(..., description="User ID"),
    client: GoogleClient = Depends(get_google_client),
):
    """Check if user is authenticated with Google."""
    try:
        is_authenticated = await client.is_authenticated()
        return {"user_id": user_id, "authenticated": is_authenticated}
    except Exception as e:
        logger.error(f"Failed to check auth status: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to check authentication status"
        ) from e


@router.delete("/revoke")
async def revoke_google_auth(
    user_id: int = Query(..., description="User ID"),
    credential_store: PostgresCredentialStore = Depends(get_credential_store),
):
    """Revoke Google authentication for a user."""
    try:
        await credential_store.delete(user_id)
        return {"user_id": user_id, "message": "Google authentication revoked"}
    except Exception as e:
        logger.error(f"Failed to revoke auth: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to revoke authentication"
        ) from e
