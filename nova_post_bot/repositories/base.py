from sqlalchemy.ext.asyncio import AsyncSession

from nova_post_bot.models.base import Base


class BaseRepository:
    model: type[Base]

    def __init__(self, session: AsyncSession):
        self.session = session