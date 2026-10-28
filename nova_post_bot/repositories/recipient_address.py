import uuid

from sqlalchemy import select
from sqlalchemy.util import await_only

from nova_post_bot.models.recipient_address import RecipientAddress
from nova_post_bot.repositories.base import BaseRepository


class RecipientAddressRepository(BaseRepository):

    model = RecipientAddress

    async def add_address(self, address: RecipientAddress) -> RecipientAddress:
        self.session.add(address)
        await self.session.flush()
        return address

    async def list_by_recipient_id(self, recipient_id: uuid.UUID) -> list[RecipientAddress]:
        result = await self.session.execute(select(RecipientAddress)
                                            .where(RecipientAddress.recipient_id == recipient_id,
                                                   RecipientAddress.is_active.is_(True))
                                            .order_by(RecipientAddress.label,
                                                      RecipientAddress.id))
        return list(result.scalars().all())
    async def get_by_location(self, recipient_id: uuid.UUID,
                              city_ref: str,
                              warehouse_ref: str) -> RecipientAddress | None:
        result = await self.session.execute(select(RecipientAddress)
                                            .where(RecipientAddress.recipient_id == recipient_id,
                                                   RecipientAddress.city_ref == city_ref,
                                                   RecipientAddress.warehouse_ref == warehouse_ref))
        return result.scalar_one_or_none()

    async def get_by_id(self, address_id: uuid.UUID) -> RecipientAddress | None:
        return await self.session.get(RecipientAddress, address_id)