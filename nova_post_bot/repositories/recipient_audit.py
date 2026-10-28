from nova_post_bot.models.recipient_audit import RecipientAudit
from nova_post_bot.repositories.base import BaseRepository


class RecipientAuditRepository(BaseRepository):
    model = RecipientAudit

    async def add_audit(self, audit: RecipientAudit) -> RecipientAudit:
        self.session.add(audit)
        await self.session.flush()
        return audit
