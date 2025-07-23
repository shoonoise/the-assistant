"""Database package for The Assistant."""

from .database import get_session, get_session_maker, get_user_service
from .models import Base, User, UserSetting
from .service import UserService

__all__ = [
    "Base",
    "User",
    "UserSetting",
    "UserService",
    "get_session",
    "get_session_maker",
    "get_user_service",
]
