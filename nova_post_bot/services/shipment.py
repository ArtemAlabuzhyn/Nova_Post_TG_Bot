import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from nova_post_bot.clients.nova_post import NovaPostClient
from nova_post_bot.core.config import settings
from nova_post_bot.core.exceptions import ObjectNotFoundError
from nova_post_bot.db.uow import UnitOfWork
from nova_post_bot.enums.shipment import ShipmentStatus
from nova_post_bot.models.recipient_address import RecipientAddress
from nova_post_bot.models.shipment import Shipment
from nova_post_bot.schemas.shipment import CreatedShipmentInfo
from nova_post_bot.services.recipient import RecipientService, normalize_phone
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
                               sender_warehouse_ref: str, sender_warehouse_name: str) -> Shipment:
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

    def build_document_properties(self, shipment: Shipment,
                                  address: RecipientAddress,
                                  recipient_ref: str,
                                  recipient_contact_ref: str,
                                  recipient_phone: str) -> dict[str, str]:
        payer_type = "Sender"
        payment_method = "NonCash"
        cargo_type = "Documents"
        service_type = "WarehouseWarehouse"
        weight = "0.5"
        seats_amount = "1"
        description = "Документи"
        cost = "200"

        return {
            "PayerType": payer_type,
            "PaymentMethod": payment_method,
            "CargoType": cargo_type,
            "ServiceType": service_type,
            "Weight": weight,
            "SeatsAmount": seats_amount,
            "Description": description,
            "Cost": cost,
            "CitySender": shipment.sender_city_ref,
            "SenderAddress": shipment.sender_warehouse_ref,
            "CityRecipient": address.city_ref,
            "RecipientAddress": address.warehouse_ref,
            "DateTime": datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%d.%m.%Y"),
            "Sender": settings.nova_post_sender_ref,
            "ContactSender": settings.nova_post_sender_contact_ref,
            "SendersPhone": settings.nova_post_sender_phone,
            "Recipient": recipient_ref,
            "ContactRecipient": recipient_contact_ref,
            "RecipientsPhone": recipient_phone
        }

    def find_recipient_contact_ref(self,
                                   contacts: list[dict],
                                   recipient_phone: str,
                                   first_name: str,
                                   last_name: str) -> str | None:
        matching_refs: set[str] = set()
        recipient_phone = recipient_phone.strip().removeprefix("+")
        for contact in contacts:
            phone = contact.get("Phones")
            ref = contact.get("Ref")
            if not phone or not ref:
                continue
            if phone.strip().removeprefix("+") == recipient_phone:
                contact_first_name = (contact.get("FirstName") or "").strip().casefold()
                contact_last_name = (contact.get("LastName") or "").strip().casefold()
                if (
                        contact_first_name != first_name.strip().casefold()
                        or contact_last_name != last_name.strip().casefold()):
                    continue
                matching_refs.add(ref)
        if not matching_refs:
            return None
        elif len(matching_refs) > 1:
            raise ValueError("Multiple Nova Post contacts match the recipient phone")
        return next(iter(matching_refs))

    async def get_recipient_contact_ref(self, client: NovaPostClient,
                                        recipient_ref: str,
                                        recipient_phone: str,
                                        first_name: str,
                                        last_name: str) -> str | None:
        all_contacts = []
        page = 1
        while True:
            contacts = await client.get_counterparty_contact_persons(counterparty_ref=recipient_ref, page=page)
            if not contacts:
                break
            all_contacts.extend(contacts)
            page += 1

        return self.find_recipient_contact_ref(contacts=all_contacts, recipient_phone=recipient_phone,
                                               first_name=first_name, last_name=last_name)

    async def get_private_person_recipient_ref(self, client: NovaPostClient) -> str:
        matching_refs: set[str] = set()
        page = 1

        while True:
            counterparties = await client.get_recipient_counterparties(page=page)
            if not counterparties:
                break
            for counterparty in counterparties:
                if counterparty.get("CounterpartyType") == "PrivatePerson":
                    counterparty_ref = counterparty.get("Ref")
                    if counterparty_ref:
                        matching_refs.add(counterparty_ref)
            page += 1
        if not matching_refs:
            raise ValueError("Private person recipient counterparty was not found")
        if len(matching_refs) > 1:
            raise ValueError("Multiple private person recipient counterparties were found")
        return next(iter(matching_refs))

    async def resolve_recipient_refs(self, client: NovaPostClient,
                                     recipient_phone: str, first_name: str,
                                     last_name: str) -> tuple[str, str]:
        recipient_ref = await self.get_private_person_recipient_ref(client=client)
        contact_ref = await self.get_recipient_contact_ref(client=client,
                                                           recipient_ref=recipient_ref,
                                                           recipient_phone=recipient_phone,
                                                           first_name=first_name,
                                                           last_name=last_name)
        if contact_ref is None:
            created_contact = await client.create_contact_person(counterparty_ref=recipient_ref, first_name=first_name,
                                                                 last_name=last_name, phone=recipient_phone)
            contact_ref = created_contact.ref
        return recipient_ref, contact_ref

    async def mark_created(self,
                           shipment_id: uuid.UUID,
                           created_info: CreatedShipmentInfo) -> Shipment:
        shipment = await self.get_by_id(shipment_id=shipment_id)
        if shipment.status != ShipmentStatus.CREATING.value:
            raise ValueError("Shipment is not in creating status")

        shipment.document_ref = created_info.document_ref
        shipment.document_number = created_info.document_number
        shipment.status = ShipmentStatus.CREATED.value

        return shipment

    async def mark_creation_error(self,
                                  shipment_id: uuid.UUID, status: ShipmentStatus) -> Shipment:
        if status not in (ShipmentStatus.UNKNOWN, ShipmentStatus.FAILED):
            raise ValueError("Status must be FAILED or UNKNOWN")
        shipment = await self.get_by_id(shipment_id=shipment_id)

        if shipment.status != ShipmentStatus.CREATING.value:
            raise ValueError("Shipment is not in creating status")
        shipment.status = status.value
        return shipment

