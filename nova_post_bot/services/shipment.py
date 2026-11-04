import uuid

from nova_post_bot.core.exceptions import ObjectNotFoundError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.enums.shipment import ShipmentStatus
from nova_post_bot.models.shipment import Shipment
from nova_post_bot.services.recipient import RecipientService
from nova_post_bot.services.recipient_address import RecipientAddressService


class ShipmentService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_by_id(self, shipment_id: uuid.UUID) -> Shipment:
        shipment = await self.uow.shipments.get_by_id(shipment_id=shipment_id)

        if shipment is None:
            raise ObjectNotFoundError(object_id=shipment_id, object_name='Shipment')
        return shipment

    async def prepare_shipment(self, shipment_id: uuid.UUID,
                               recipient_id: uuid.UUID, recipient_address_id: uuid.UUID,
                               created_by_telegram_id: int, created_by_name: str,
                               requested_by_name: str, shipment_type: str,
                               sender_city_ref: str, sender_city_name: str,
                               sender_warehouse_ref: str, sender_warehouse_name: str) ->  Shipment:
        recipient_service = RecipientService(uow=self.uow)
        address_service = RecipientAddressService(uow=self.uow)
        recipient = await recipient_service.get_by_id(recipient_id=recipient_id)
        address = await address_service.get_by_id(address_id=recipient_address_id)
        if not recipient.is_active:
            raise ValueError('Recipient is not active')
        if not address.is_active:
            raise ValueError('Address is not active')
        if recipient_id != address.recipient_id:
            raise ValueError('Recipient and address do not match')

        if shipment_type != "documents":
            raise ValueError("Shipment type must be 'documents'")

        shipment = Shipment(id=shipment_id, recipient_id=recipient_id,
                            recipient_address_id=recipient_address_id,
                            created_by_telegram_id=created_by_telegram_id,
                            created_by_name=created_by_name,
                            requested_by_name=requested_by_name,
                            shipment_type=shipment_type,
                            sender_city_ref=sender_city_ref,
                            sender_city_name=sender_city_name,
                            sender_warehouse_ref=sender_warehouse_ref,
                            sender_warehouse_name=sender_warehouse_name,
                            status=ShipmentStatus.PENDING.value)
        return await self.uow.shipments.add_if_absent(shipment=shipment)

    async def try_start_creation(self, shipment_id: uuid.UUID) -> bool:
        return await self.uow.shipments.try_start_creation(shipment_id=shipment_id)


