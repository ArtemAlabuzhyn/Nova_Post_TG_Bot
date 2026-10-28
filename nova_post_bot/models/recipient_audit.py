import datetime
import uuid

from sqlalchemy import ForeignKey

from sqlalchemy import DateTime, func, BigInteger
from nova_post_bot.models.base import Base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column


class RecipientAudit(Base):
    __tablename__ = 'recipient_audit'
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('recipients.id',
                                                               ondelete='RESTRICT'),
                                                               nullable=False)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actor_name: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                          server_default=func.now())

    action: Mapped[str] = mapped_column(nullable=False)
    recipient_address_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('recipient_addresses.id',
                                                                             ondelete='RESTRICT'),
                                                                  nullable=True)
    old_values: Mapped[dict| None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict| None] = mapped_column(JSONB, nullable=True)