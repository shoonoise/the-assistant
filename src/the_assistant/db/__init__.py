"""Database package for The Assistant."""

from .database import get_session
from .models import Base, User, UserSetting
from .service import UserService

__all__ = [
    "Base",
    "User",
    "UserSetting",
    "UserService",
    "get_session",
]
