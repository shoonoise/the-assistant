"""User-related activities for Temporal workflows."""

from dataclasses import dataclass

from temporalio import activity

from the_assistant.db import get_user_service


@dataclass
class GetUserAccountsInput:
    """Input for getting user accounts."""

    user_id: int
    provider: str


@activity.defn
async def get_user_accounts(input_data: GetUserAccountsInput) -> list[str]:
    """Get all account names for a user and provider."""
    user_service = get_user_service()
    return await user_service.get_user_accounts(input_data.user_id, input_data.provider)
