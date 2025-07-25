import logging
from datetime import UTC, datetime, timedelta

import jwt

from ...settings import Settings

logger = logging.getLogger(__name__)


def create_state_jwt(
    user_id: int, settings: Settings, account: str | None = None
) -> str:
    """Create a JWT state token for OAuth2 flow."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(UTC) + timedelta(minutes=10),
        "iat": datetime.now(UTC),
    }
    if account:
        payload["account"] = account
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def parse_state_jwt(state: str, settings: Settings) -> tuple[int | None, str | None]:
    """Parse and validate JWT state token."""
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])
        return payload.get("user_id"), payload.get("account")
    except jwt.ExpiredSignatureError:
        logger.warning("State token expired")
        return None, None
    except jwt.InvalidTokenError:
        logger.warning("Invalid state token")
        return None, None
