import uuid

from nova_post_bot.models.user import User
from nova_post_bot.repositories.base import BaseRepository
from sqlalchemy import select


class UserRepository(BaseRepository):
    model = User

    async def add_user(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        model_id = getattr(self.model, "telegram_id")
        result = await self.session.execute(select(self.model).where(model_id == telegram_id))
        return result.scalar_one_or_none()

