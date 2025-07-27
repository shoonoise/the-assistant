"""Tests for user activities."""

from unittest.mock import AsyncMock, patch

import pytest

from the_assistant.activities.user_activities import (
    GetUserAccountsInput,
    get_user_accounts,
)


@pytest.mark.asyncio
async def test_get_user_accounts():
    """Test getting user accounts."""
    # Mock the user service
    mock_user_service = AsyncMock()
    mock_user_service.get_user_accounts.return_value = ["personal", "work"]

    with patch(
        "the_assistant.activities.user_activities.get_user_service"
    ) as mock_get_service:
        mock_get_service.return_value = mock_user_service

        input_data = GetUserAccountsInput(user_id=123, provider="google")
        result = await get_user_accounts(input_data)

        assert result == ["personal", "work"]
        mock_user_service.get_user_accounts.assert_called_once_with(123, "google")


@pytest.mark.asyncio
async def test_get_user_accounts_empty():
    """Test getting user accounts when none exist."""
    # Mock the user service
    mock_user_service = AsyncMock()
    mock_user_service.get_user_accounts.return_value = []

    with patch(
        "the_assistant.activities.user_activities.get_user_service"
    ) as mock_get_service:
        mock_get_service.return_value = mock_user_service

        input_data = GetUserAccountsInput(user_id=123, provider="google")
        result = await get_user_accounts(input_data)

        assert result == []
        mock_user_service.get_user_accounts.assert_called_once_with(123, "google")
