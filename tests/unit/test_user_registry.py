"""Tests for user registry."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from the_assistant.utils.user_registry import (
    UserProfile,
    UserRegistry,
    get_user_registry,
)


class TestUserProfile:
    """Test UserProfile dataclass."""

    def test_user_profile_creation(self):
        """Test creating a user profile."""
        profile = UserProfile(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
        )

        assert profile.telegram_id == 123456789
        assert profile.username == "testuser"
        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.morning_briefing_enabled is True
        assert profile.trip_notifications_enabled is True
        assert profile.preferred_briefing_time == "08:00"
        assert profile.timezone == "UTC"

    def test_user_profile_defaults(self):
        """Test user profile with default values."""
        profile = UserProfile(telegram_id=123456789)

        assert profile.telegram_id == 123456789
        assert profile.username is None
        assert profile.first_name is None
        assert profile.last_name is None
        assert profile.registered_at is None
        assert profile.morning_briefing_enabled is True
        assert profile.trip_notifications_enabled is True
        assert profile.preferred_briefing_time == "08:00"
        assert profile.timezone == "UTC"


class TestUserRegistry:
    """Test UserRegistry class."""

    @pytest.fixture
    def temp_registry_file(self):
        """Create a temporary registry file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "123456789": {
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
                "registered_at": "2024-01-01T10:00:00",
                "morning_briefing_enabled": True,
                "trip_notifications_enabled": False,
                "preferred_briefing_time": "09:00",
                "timezone": "Europe/London",
            }
        }

    def test_init_with_nonexistent_file(self, temp_registry_file):
        """Test initialization with non-existent registry file."""
        # Remove the temp file to simulate non-existent file
        Path(temp_registry_file).unlink()

        registry = UserRegistry(temp_registry_file)

        assert len(registry._users) == 0
        assert registry.registry_file == Path(temp_registry_file)

    def test_init_with_existing_file(self, temp_registry_file, sample_user_data):
        """Test initialization with existing registry file."""
        # Write sample data to file
        with open(temp_registry_file, "w") as f:
            json.dump(sample_user_data, f)

        registry = UserRegistry(temp_registry_file)

        assert len(registry._users) == 1
        assert 123456789 in registry._users
        user = registry._users[123456789]
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.preferred_briefing_time == "09:00"
        assert user.trip_notifications_enabled is False

    def test_load_users_invalid_json(self, temp_registry_file):
        """Test loading users with invalid JSON."""
        # Write invalid JSON to file
        with open(temp_registry_file, "w") as f:
            f.write("invalid json")

        registry = UserRegistry(temp_registry_file)

        # Should handle error gracefully and start with empty registry
        assert len(registry._users) == 0

    def test_register_new_user(self, temp_registry_file):
        """Test registering a new user."""
        registry = UserRegistry(temp_registry_file)

        user = registry.register_user(
            telegram_id=123456789,
            username="newuser",
            first_name="New",
            last_name="User",
        )

        assert user.telegram_id == 123456789
        assert user.username == "newuser"
        assert user.first_name == "New"
        assert user.last_name == "User"
        assert user.registered_at is not None
        assert 123456789 in registry._users

    def test_register_existing_user_updates_info(
        self, temp_registry_file, sample_user_data
    ):
        """Test registering an existing user updates their info."""
        # Write sample data to file
        with open(temp_registry_file, "w") as f:
            json.dump(sample_user_data, f)

        registry = UserRegistry(temp_registry_file)

        # Update existing user
        user = registry.register_user(
            telegram_id=123456789, username="updateduser", first_name="Updated"
        )

        assert user.telegram_id == 123456789
        assert user.username == "updateduser"
        assert user.first_name == "Updated"
        assert user.last_name == "User"  # Should keep existing value
        assert (
            user.preferred_briefing_time == "09:00"
        )  # Should keep existing preferences

    def test_get_user_existing(self, temp_registry_file, sample_user_data):
        """Test getting an existing user."""
        with open(temp_registry_file, "w") as f:
            json.dump(sample_user_data, f)

        registry = UserRegistry(temp_registry_file)
        user = registry.get_user(123456789)

        assert user is not None
        assert user.telegram_id == 123456789
        assert user.username == "testuser"

    def test_get_user_nonexistent(self, temp_registry_file):
        """Test getting a non-existent user."""
        registry = UserRegistry(temp_registry_file)
        user = registry.get_user(999999999)

        assert user is None

    def test_get_all_users(self, temp_registry_file, sample_user_data):
        """Test getting all users."""
        with open(temp_registry_file, "w") as f:
            json.dump(sample_user_data, f)

        registry = UserRegistry(temp_registry_file)
        users = registry.get_all_users()

        assert len(users) == 1
        assert users[0].telegram_id == 123456789

    def test_get_users_with_morning_briefing(self, temp_registry_file):
        """Test getting users with morning briefing enabled."""
        registry = UserRegistry(temp_registry_file)

        # Register users with different preferences
        registry.register_user(123456789, username="user1")
        registry.register_user(987654321, username="user2")
        registry.update_user_preferences(987654321, morning_briefing_enabled=False)

        users = registry.get_users_with_morning_briefing()

        assert len(users) == 1
        assert users[0].telegram_id == 123456789

    def test_get_users_with_trip_notifications(self, temp_registry_file):
        """Test getting users with trip notifications enabled."""
        registry = UserRegistry(temp_registry_file)

        # Register users with different preferences
        registry.register_user(123456789, username="user1")
        registry.register_user(987654321, username="user2")
        registry.update_user_preferences(987654321, trip_notifications_enabled=False)

        users = registry.get_users_with_trip_notifications()

        assert len(users) == 1
        assert users[0].telegram_id == 123456789

    def test_update_user_preferences_existing_user(self, temp_registry_file):
        """Test updating preferences for existing user."""
        registry = UserRegistry(temp_registry_file)
        registry.register_user(123456789, username="testuser")

        user = registry.update_user_preferences(
            123456789,
            morning_briefing_enabled=False,
            preferred_briefing_time="10:00",
            timezone="Europe/Paris",
        )

        assert user is not None
        assert user.morning_briefing_enabled is False
        assert user.preferred_briefing_time == "10:00"
        assert user.timezone == "Europe/Paris"

    def test_update_user_preferences_nonexistent_user(self, temp_registry_file):
        """Test updating preferences for non-existent user."""
        registry = UserRegistry(temp_registry_file)

        user = registry.update_user_preferences(
            999999999, morning_briefing_enabled=False
        )

        assert user is None

    def test_update_user_preferences_invalid_field(self, temp_registry_file):
        """Test updating preferences with invalid field."""
        registry = UserRegistry(temp_registry_file)
        registry.register_user(123456789, username="testuser")

        # This should not raise an error, just ignore invalid fields
        user = registry.update_user_preferences(
            123456789, invalid_field="value", morning_briefing_enabled=False
        )

        assert user is not None
        assert user.morning_briefing_enabled is False
        assert not hasattr(user, "invalid_field")

    def test_is_user_registered_true(self, temp_registry_file):
        """Test is_user_registered returns True for registered user."""
        registry = UserRegistry(temp_registry_file)
        registry.register_user(123456789, username="testuser")

        assert registry.is_user_registered(123456789) is True

    def test_is_user_registered_false(self, temp_registry_file):
        """Test is_user_registered returns False for unregistered user."""
        registry = UserRegistry(temp_registry_file)

        assert registry.is_user_registered(999999999) is False

    def test_save_users_creates_directory(self, temp_registry_file):
        """Test that _save_users creates directory if it doesn't exist."""
        # Use a path with non-existent directory
        nested_path = Path(temp_registry_file).parent / "nested" / "registry.json"

        registry = UserRegistry(str(nested_path))
        registry.register_user(123456789, username="testuser")

        # Directory should be created and file should exist
        assert nested_path.exists()
        assert nested_path.parent.exists()

        # Cleanup
        nested_path.unlink()
        nested_path.parent.rmdir()

    @patch("the_assistant.utils.user_registry.json.load")
    def test_load_users_json_error(self, mock_json_load, temp_registry_file):
        """Test handling JSON load error."""
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        # Create the file so it exists
        Path(temp_registry_file).touch()

        registry = UserRegistry(temp_registry_file)

        # Should handle error gracefully
        assert len(registry._users) == 0

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_save_users_permission_error(self, mock_open, temp_registry_file):
        """Test handling permission error when saving."""
        registry = UserRegistry(temp_registry_file)

        # This should not raise an exception, just log the error
        registry.register_user(123456789, username="testuser")

        # The user should still be in memory even if save failed
        assert 123456789 in registry._users


class TestGetUserRegistry:
    """Test the global user registry function."""

    def test_get_user_registry_singleton(self):
        """Test that get_user_registry returns the same instance."""
        registry1 = get_user_registry()
        registry2 = get_user_registry()

        assert registry1 is registry2

    def test_get_user_registry_returns_user_registry(self):
        """Test that get_user_registry returns a UserRegistry instance."""
        registry = get_user_registry()

        assert isinstance(registry, UserRegistry)
