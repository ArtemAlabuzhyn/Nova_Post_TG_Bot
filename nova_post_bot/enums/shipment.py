from enum import StrEnum

class ShipmentStatus(StrEnum):
    PENDING = "pending"
    CREATING = "creating"
    CREATED = "created"
    FAILED = "failed"
    UNKNOWN = "unknown"