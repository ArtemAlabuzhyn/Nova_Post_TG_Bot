import datetime
import uuid

from sqlalchemy import DateTime, func, BigInteger, true, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from nova_post_bot.models.base import Base


class Recipient(Base):
    __tablename__ = 'recipients'
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    phone: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                          server_default=func.now())
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by_name: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True, server_default=true())

    __table_args__ = (Index(
        "uq_recipients_name_phone",
        func.lower(first_name),
        func.lower(last_name),
        phone,
        unique=True,
    ),)