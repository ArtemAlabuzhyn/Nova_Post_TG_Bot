import uuid

from sqlalchemy import select, func

from nova_post_bot.models.recipient import Recipient
from nova_post_bot.repositories.base import BaseRepository


class RecipientRepository(BaseRepository):
    model = Recipient

    async def add_recipient(self, recipient: Recipient) -> Recipient:
        self.session.add(recipient)
        await self.session.flush()
        await self.session.refresh(recipient)
        return recipient

    async def get_by_id(self, recipient_id: uuid.UUID) -> Recipient | None:
        return await self.session.get(Recipient, recipient_id)

    async def list_recipients(self, limit: int = 10, offset: int = 0) -> list[Recipient]:
        result = await self.session.execute(select(Recipient).where(Recipient.is_active.is_(True))
                                            .order_by(Recipient.last_name,
                                                      Recipient.first_name,
                                                      Recipient.id,
                                                      ).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def find_duplicate(self, first_name: str, last_name: str, phone: str) -> Recipient | None:
        result = await self.session.execute(select(Recipient)
                                            .where(func.lower(Recipient.first_name) == func.lower(first_name),
                                                   func.lower(Recipient.last_name) == func.lower(last_name),
                                                   Recipient.phone == phone))

        return result.scalar_one_or_none()
