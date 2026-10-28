import uuid

from sqlalchemy import ForeignKey, true, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from nova_post_bot.models.base import Base


class RecipientAddress(Base):
    __tablename__ = "recipient_addresses"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('recipients.id',
                                                               ondelete='RESTRICT'),
                                                    nullable=False)
    label: Mapped[str] = mapped_column(nullable=False)
    city_ref: Mapped[str] = mapped_column(nullable=False)
    city_name: Mapped[str] = mapped_column(nullable=False)
    warehouse_ref: Mapped[str] = mapped_column(nullable=False)
    warehouse_name: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())

    __table_args__ = (UniqueConstraint('recipient_id',
                                       'city_ref',
                                       'warehouse_ref',
                                       name='uq_recipient_addresses_recipient_city_warehouse'),)
