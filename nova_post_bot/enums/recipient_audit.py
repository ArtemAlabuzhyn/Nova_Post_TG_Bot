from enum import StrEnum

class RecipientAuditAction(StrEnum):
    CREATED = "created"
    RESTORED = "restored"
    DELIVERY_ADDRESS_UPDATED = "delivery_address_updated"
    UPDATED = "updated"
    ARCHIVED = "archived"


class SaveStatus(StrEnum):
    CREATED = "created"
    EXISTING = "existing"
    RESTORED = "restored"
    UPDATED = "updated"
