import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .integrations.google.oauth_router import router as google_oauth_router
from .settings import get_settings

app = FastAPI(title="The Assistant", version="0.1.0")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(google_oauth_router)

logger = logging.getLogger(__name__)


@app.get("/auth-success")
async def auth_success():
    """OAuth authentication success page."""
    return RedirectResponse(url="/static/auth-success.html", status_code=302)


@app.get("/auth-error")
async def auth_error(error: str | None = None, message: str | None = None):
    """OAuth authentication error page."""
    # Build query parameters for the static page
    params = []
    if error:
        params.append(f"error={error}")
    if message:
        params.append(f"message={message}")

    query_string = "&".join(params)
    redirect_url = (
        f"/static/auth-error.html?{query_string}"
        if query_string
        else "/static/auth-error.html"
    )

    return RedirectResponse(url=redirect_url, status_code=302)


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
