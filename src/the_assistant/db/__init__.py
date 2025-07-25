"""Database package for The Assistant."""

from .database import (
    DatabaseManager,
    get_database_manager,
    get_session,
    get_session_maker,
    get_user_service,
)
from .models import Base, ThirdPartyAccount, User, UserSetting
from .service import UserService

__all__ = [
    "Base",
    "DatabaseManager",
    "User",
    "UserSetting",
    "ThirdPartyAccount",
    "UserService",
    "get_database_manager",
    "get_session",
    "get_session_maker",
    "get_user_service",
]
