import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .integrations.google.oauth_router import router as google_oauth_router
from .settings import get_settings
from .user_settings import router as settings_router

app = FastAPI(title="The Assistant", version="0.1.0")

# Include routers
app.include_router(google_oauth_router)
app.include_router(settings_router)


# Redirect for Google OAuth callback (temporary fix)
@app.get("/oauth2callback")
async def oauth_redirect(
    state: str | None = None, code: str | None = None, error: str | None = None
):
    """Redirect Google OAuth callback to the correct endpoint."""
    params = []
    if state:
        params.append(f"state={state}")
    if code:
        params.append(f"code={code}")
    if error:
        params.append(f"error={error}")

    query_string = "&".join(params)
    redirect_url = (
        f"/google/oauth2callback?{query_string}"
        if query_string
        else "/google/oauth2callback"
    )

    return RedirectResponse(url=redirect_url, status_code=302)


# OAuth success/error pages
@app.get("/auth-success")
async def auth_success():
    """OAuth authentication success page."""
    return {"message": "Google authentication successful! You can close this window."}


@app.get("/auth-error")
async def auth_error(error: str | None = None, message: str | None = None):
    """OAuth authentication error page."""
    return {
        "message": "Google authentication failed",
        "error": error,
        "details": message,
    }


@app.get("/test-calendar")
async def test_calendar(user_id: int = 1):
    """Test endpoint to verify Google Calendar access works."""
    import logging

    logger = logging.getLogger(__name__)

    from .activities.google_activities import get_google_client

    try:
        logger.info(f"Starting test_calendar for user {user_id}")
        client = get_google_client(user_id)
        logger.info(f"Created client for user {user_id}")

        # Get raw credentials for debugging
        logger.info(f"Getting credentials for user {user_id}")
        credentials = await client.get_credentials()
        logger.info(f"Got credentials for user {user_id}: {credentials is not None}")

        if not credentials:
            logger.warning(f"No credentials found for user {user_id}")
            return {
                "error": f"No credentials found for user {user_id}",
                "authenticated": False,
                "debug": "No credentials in database",
            }

        # Check authentication
        logger.info(f"Checking authentication for user {user_id}")
        is_authenticated = await client.is_authenticated()
        logger.info(f"Authentication result for user {user_id}: {is_authenticated}")

        debug_info = {
            "has_credentials": credentials is not None,
            "credentials_valid": credentials.valid if credentials else False,
            "credentials_expired": credentials.expired if credentials else None,
            "has_refresh_token": bool(credentials.refresh_token)
            if credentials
            else False,
        }

        if not is_authenticated:
            logger.warning(f"User {user_id} is not authenticated")
            return {
                "error": f"User {user_id} is not authenticated with Google",
                "authenticated": False,
                "debug": debug_info,
            }

        # Fetch some events
        logger.info(f"Fetching events for user {user_id}")
        events = await client.get_upcoming_events(days_ahead=7)
        logger.info(f"Got {len(events)} events for user {user_id}")

        return {
            "authenticated": True,
            "user_id": user_id,
            "events_count": len(events),
            "debug": debug_info,
            "events": [
                {
                    "id": event.id,
                    "summary": event.summary,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat(),
                    "location": event.location,
                }
                for event in events[:5]  # Show first 5 events
            ],
        }

    except Exception as e:
        logger.error(f"Error in test_calendar for user {user_id}: {e}")
        return {"error": str(e), "authenticated": False}


logger = logging.getLogger(__name__)


def main():
    """Main entry point for the web server."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting The Assistant Web Server")
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
