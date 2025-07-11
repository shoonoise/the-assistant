"""
FastAPI router for Google OAuth2 endpoints.
"""

import logging
import os
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from .client import GoogleAuthError, GoogleClient
from .credential_store import PostgresCredentialStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google", tags=["google"])

# JWT secret for state token signing
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable not set")


def get_credential_store() -> PostgresCredentialStore:
    """Dependency to get credential store."""
    database_url = os.getenv(
        "DATABASE_URL", "postgresql://temporal:temporal@postgresql:5432/the_assistant"
    )
    encryption_key = os.getenv("DB_ENCRYPTION_KEY")
    if not encryption_key:
        raise HTTPException(status_code=500, detail="DB_ENCRYPTION_KEY not configured")

    return PostgresCredentialStore(database_url, encryption_key)


def get_google_client(
    user_id: int = Query(..., description="User ID"),
    credential_store: PostgresCredentialStore = Depends(get_credential_store),
) -> GoogleClient:
    """Dependency to get Google client for a user."""
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "secrets/google.json")
    scopes = (
        os.getenv("GOOGLE_OAUTH_SCOPES", "").split(",")
        if os.getenv("GOOGLE_OAUTH_SCOPES")
        else None
    )

    return GoogleClient(
        user_id=user_id,
        credential_store=credential_store,
        credentials_path=credentials_path,
        scopes=scopes,
    )


def create_state_jwt(user_id: int) -> str:
    """Create a JWT state token for OAuth2 flow."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=10),  # 10 min expiry
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def parse_state_jwt(state: str) -> int | None:
    """Parse and validate JWT state token."""
    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
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
        redirect_uri = os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/google/oauth2callback"
        )
        state = create_state_jwt(user_id)
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
        user_id = parse_state_jwt(state)
        if not user_id:
            logger.error("Invalid or expired state token")
            return RedirectResponse(
                url="/auth-error?error=invalid_state", status_code=302
            )

        # Get client for this user
        credential_store = get_credential_store()
        client = GoogleClient(
            user_id=user_id,
            credential_store=credential_store,
            credentials_path=os.getenv(
                "GOOGLE_CREDENTIALS_PATH", "/secrets/google.json"
            ),
        )

        # Exchange code for credentials
        redirect_uri = os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/oauth2callback"
        )
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
