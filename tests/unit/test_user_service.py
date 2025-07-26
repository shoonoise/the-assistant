import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from the_assistant.db.models import Base
from the_assistant.db.service import UserService
from the_assistant.integrations.telegram.constants import SettingKey


@pytest.fixture
async def session_maker(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield maker
    await engine.dispose()


@pytest.fixture
def user_service(session_maker):
    return UserService(session_maker)


@pytest.mark.asyncio
async def test_create_and_get_user(user_service):
    user = await user_service.create_user(username="alice", first_name="Alice")
    assert user.id is not None

    fetched = await user_service.get_user_by_id(user.id)
    assert fetched is not None
    assert fetched.username == "alice"
    assert fetched.first_name == "Alice"


@pytest.mark.asyncio
async def test_update_user(user_service):
    user = await user_service.create_user(username="bob", first_name="B")
    updated = await user_service.update_user(user.id, first_name="Bob")
    assert updated is not None
    assert updated.first_name == "Bob"

    fetched = await user_service.get_user_by_id(user.id)
    assert fetched.first_name == "Bob"


@pytest.mark.asyncio
async def test_setting_management(user_service):
    user = await user_service.create_user(username="c")

    await user_service.set_setting(user.id, SettingKey.ABOUT_ME, "Hi")
    await user_service.set_setting(user.id, SettingKey.LOCATION, "Paris")

    assert await user_service.get_setting(user.id, SettingKey.ABOUT_ME) == "Hi"

    all_settings = await user_service.get_all_settings(user.id)
    assert all_settings == {"about_me": "Hi", "location": "Paris"}

    await user_service.unset_setting(user.id, SettingKey.ABOUT_ME)
    assert await user_service.get_setting(user.id, SettingKey.ABOUT_ME) is None


@pytest.mark.asyncio
async def test_google_credentials_multiple_accounts(user_service):
    user = await user_service.create_user(username="multi")

    await user_service.set_google_credentials(
        user.id, "cred-personal", account="personal"
    )
    await user_service.set_google_credentials(user.id, "cred-work", account="work")

    assert (
        await user_service.get_google_credentials(user.id, account="personal")
        == "cred-personal"
    )
    assert (
        await user_service.get_google_credentials(user.id, account="work")
        == "cred-work"
    )
    # Legacy column should remain empty
    assert await user_service.get_google_credentials(user.id) is None

    # Ensure two third-party account records exist
    async with user_service._session_maker() as session:
        from the_assistant.db.models import ThirdPartyAccount

        result = await session.execute(
            select(ThirdPartyAccount).where(ThirdPartyAccount.user_id == user.id)
        )
        accounts = result.scalars().all()
        assert {a.account for a in accounts} == {"personal", "work"}
