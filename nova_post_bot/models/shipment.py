import uuid
import datetime

from sqlalchemy import BigInteger, ForeignKey, String, DateTime, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from nova_post_bot.enums.shipment import ShipmentStatus
from nova_post_bot.models.base import Base


class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('recipients.id', ondelete='RESTRICT'), nullable=False)
    recipient_address_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(
        'recipient_addresses.id', ondelete='RESTRICT'), nullable=False)
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by_name: Mapped[str] = mapped_column(String, nullable=False)
    requested_by_name: Mapped[str] = mapped_column(String, nullable=False)
    shipment_type: Mapped[str] = mapped_column(String, nullable=False)
    sender_city_ref: Mapped[str] = mapped_column(String, nullable=False)
    sender_city_name: Mapped[str] = mapped_column(String, nullable=False)
    sender_warehouse_ref: Mapped[str] = mapped_column(String, nullable=False)
    sender_warehouse_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                          server_default=func.now())

    document_number: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    document_ref: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)

    status: Mapped[str] = mapped_column(String, nullable=False, default=ShipmentStatus.PENDING.value,
                                        server_default=ShipmentStatus.PENDING.value)

    __table_args__ = (CheckConstraint(
        "status IN ('pending', 'creating', 'created', 'failed', 'unknown')",
        name="ck_shipment_status"
        ),
    )
