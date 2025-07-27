"""Integration test for user accounts functionality."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from the_assistant.db.models import Base
from the_assistant.db.service import UserService


@pytest.fixture
async def session_maker(tmp_path):
    """Create a test database session maker."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_daily_briefing_account_retrieval(session_maker):
    """Test the complete flow of retrieving accounts for daily briefing."""
    user_service = UserService(session_maker)

    # Create a test user
    user = await user_service.create_user(username="test_user")

    # Initially, no accounts should exist
    accounts = await user_service.get_user_accounts(user.id, "google")
    assert accounts == []

    # Add some Google accounts
    await user_service.set_google_credentials(user.id, "cred1", "personal")
    await user_service.set_google_credentials(user.id, "cred2", "work")
    await user_service.set_google_credentials(user.id, "cred3", "default")

    # Now we should get all accounts
    accounts = await user_service.get_user_accounts(user.id, "google")
    assert set(accounts) == {"personal", "work", "default"}

    assert len(accounts) >= 1
    assert "personal" in accounts
    assert "work" in accounts
