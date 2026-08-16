import pytest

from nova_post_bot.db.session import SessionLocal
from nova_post_bot.models.user import User
from nova_post_bot.repositories.user import UserRepository
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.asyncio(loop_scope="module")

async def test_add_user():
    async with SessionLocal() as session:
        repo = UserRepository(session)
        user = User(telegram_id=123456, username="testuser", first_name="Test")
        added_user = await repo.add_user(user)
        assert added_user.id is not None
        assert added_user.telegram_id == 123456
        assert added_user.username == "testuser"
        assert added_user.first_name == "Test"

async def test_get_by_telegram_id():
    async with SessionLocal() as session:
        repo = UserRepository(session)
        user = User(telegram_id=123456, username="testuser", first_name="Test")
        added_user = await repo.add_user(user)

        wanted_user = await repo.get_by_telegram_id(added_user.telegram_id)
        assert wanted_user is not None
        assert wanted_user.username == "testuser"
        assert wanted_user.first_name == "Test"
        assert wanted_user.telegram_id == 123456

async def test_invalid_add_second_user():
    async with SessionLocal() as session:
        repo = UserRepository(session)

        user1 = User(
            telegram_id=123456,
            username="testuser1",
            first_name="Test",
        )
        await repo.add_user(user1)

        user2 = User(
            telegram_id=123456,
            username="testuser2",
            first_name="Test",
        )

        with pytest.raises(IntegrityError):
            await repo.add_user(user2)

        await session.rollback()


