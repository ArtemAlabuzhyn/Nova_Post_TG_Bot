from nova_post_bot.db.session import SessionLocal
from nova_post_bot.repositories.recipient_address import RecipientAddressRepository
from nova_post_bot.repositories.recipient_audit import RecipientAuditRepository
from nova_post_bot.repositories.user import UserRepository
from nova_post_bot.repositories.recipient import RecipientRepository


class UnitOfWork:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self.session = None

    async def __aenter__(self):
        self.session = self.session_factory()
        self.users = UserRepository(self.session)
        self.recipients = RecipientRepository(self.session)
        self.recipient_audit = RecipientAuditRepository(self.session)
        self.recipient_addresses = RecipientAddressRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()

        await self.session.close()

    async def rollback(self):
        await self.session.rollback()

    async def commit(self):
        await self.session.commit()

