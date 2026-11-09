import uuid

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from nova_post_bot.enums.shipment import ShipmentStatus
from nova_post_bot.models.shipment import Shipment
from nova_post_bot.repositories.base import BaseRepository


class ShipmentRepository(BaseRepository):
    model = Shipment

    async def add_shipment(self, shipment: Shipment) -> Shipment:
        self.session.add(shipment)
        await self.session.flush()
        await self.session.refresh(shipment)
        return shipment

    async def get_by_id(self, shipment_id: uuid.UUID) -> Shipment | None:
        return await self.session.get(Shipment, shipment_id)

    async def try_start_creation(self, shipment_id: uuid.UUID) -> bool:
        result = await self.session.execute(update(Shipment)
                                   .where(Shipment.id == shipment_id,
                                          Shipment.status == ShipmentStatus.PENDING.value)
                                   .values(status=ShipmentStatus.CREATING.value).returning(Shipment.id))
        return result.scalar_one_or_none() is not None

    async def add_if_absent(self, shipment: Shipment) -> Shipment:
        stmt = insert(Shipment).values(id=shipment.id, recipient_id=shipment.recipient_id,
                                       recipient_address_id=shipment.recipient_address_id,
                                       created_by_telegram_id=shipment.created_by_telegram_id,
                                       created_by_name=shipment.created_by_name,
                                       requested_by_name=shipment.requested_by_name,
                                       shipment_type=shipment.shipment_type,
                                       sender_city_ref=shipment.sender_city_ref,
                                       sender_city_name=shipment.sender_city_name,
                                       sender_warehouse_ref=shipment.sender_warehouse_ref,
                                       sender_warehouse_name=shipment.sender_warehouse_name,
                                       status=shipment.status).on_conflict_do_nothing(index_elements=[Shipment.id])
        await self.session.execute(stmt)
        saved_shipment = await self.get_by_id(shipment.id)
        if saved_shipment is None:
            raise RuntimeError("Shipment wasn't found after insert")

        return saved_shipment
