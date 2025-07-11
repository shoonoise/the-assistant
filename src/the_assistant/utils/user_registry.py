"""User registry for managing Telegram users and their preferences."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User profile with preferences and settings."""

    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    registered_at: str | None = None
    morning_briefing_enabled: bool = True
    trip_notifications_enabled: bool = True
    preferred_briefing_time: str = "08:00"
    timezone: str = "UTC"


class UserRegistry:
    """Registry for managing user profiles and preferences."""

    def __init__(self, registry_file: str = "user_registry.json"):
        """Initialize the user registry.

        Args:
            registry_file: Path to the JSON file storing user data
        """
        self.registry_file = Path(registry_file)
        self._users: dict[int, UserProfile] = {}
        self._load_users()

    def _load_users(self) -> None:
        """Load users from the registry file."""
        if not self.registry_file.exists():
            logger.info(
                f"Registry file {self.registry_file} doesn't exist, starting with empty registry"
            )
            return

        try:
            with open(self.registry_file) as f:
                data = json.load(f)

            for user_id_str, user_data in data.items():
                user_id = int(user_id_str)
                self._users[user_id] = UserProfile(telegram_id=user_id, **user_data)

            logger.info(f"Loaded {len(self._users)} users from registry")

        except Exception as e:
            logger.error(f"Error loading user registry: {e}")

    def _save_users(self) -> None:
        """Save users to the registry file."""
        try:
            # Convert users to serializable format
            data = {
                str(user_id): asdict(profile)
                for user_id, profile in self._users.items()
            }

            # Ensure directory exists
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(self.registry_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self._users)} users to registry")

        except Exception as e:
            logger.error(f"Error saving user registry: {e}")

    def register_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> UserProfile:
        """Register a new user or update existing user info.

        Args:
            telegram_id: The user's Telegram ID
            username: The user's Telegram username
            first_name: The user's first name
            last_name: The user's last name

        Returns:
            The user's profile
        """
        if telegram_id in self._users:
            # Update existing user
            user = self._users[telegram_id]
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            logger.info(f"Updated existing user {telegram_id}")
        else:
            # Create new user
            user = UserProfile(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                registered_at=datetime.now().isoformat(),
            )
            self._users[telegram_id] = user
            logger.info(f"Registered new user {telegram_id}")

        self._save_users()
        return user

    def get_user(self, telegram_id: int) -> UserProfile | None:
        """Get a user's profile by Telegram ID.

        Args:
            telegram_id: The user's Telegram ID

        Returns:
            The user's profile, or None if not found
        """
        return self._users.get(telegram_id)

    def get_all_users(self) -> list[UserProfile]:
        """Get all registered users.

        Returns:
            List of all user profiles
        """
        return list(self._users.values())

    def get_users_with_morning_briefing(self) -> list[UserProfile]:
        """Get all users who have morning briefing enabled.

        Returns:
            List of users with morning briefing enabled
        """
        return [user for user in self._users.values() if user.morning_briefing_enabled]

    def get_users_with_trip_notifications(self) -> list[UserProfile]:
        """Get all users who have trip notifications enabled.

        Returns:
            List of users with trip notifications enabled
        """
        return [
            user for user in self._users.values() if user.trip_notifications_enabled
        ]

    def update_user_preferences(
        self, telegram_id: int, **preferences
    ) -> UserProfile | None:
        """Update a user's preferences.

        Args:
            telegram_id: The user's Telegram ID
            **preferences: Preference fields to update

        Returns:
            The updated user profile, or None if user not found
        """
        user = self._users.get(telegram_id)
        if not user:
            return None

        # Update allowed preferences
        allowed_fields = {
            "morning_briefing_enabled",
            "trip_notifications_enabled",
            "preferred_briefing_time",
            "timezone",
        }

        for key, value in preferences.items():
            if key in allowed_fields and hasattr(user, key):
                setattr(user, key, value)

        self._save_users()
        logger.info(f"Updated preferences for user {telegram_id}")
        return user

    def is_user_registered(self, telegram_id: int) -> bool:
        """Check if a user is registered.

        Args:
            telegram_id: The user's Telegram ID

        Returns:
            True if the user is registered, False otherwise
        """
        return telegram_id in self._users


# Global registry instance
_registry: UserRegistry | None = None


def get_user_registry() -> UserRegistry:
    """Get the global user registry instance."""
    global _registry
    if _registry is None:
        _registry = UserRegistry()
    assert _registry is not None  # Type checker hint
    return _registry  # type: ignore
