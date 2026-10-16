import pydantic
from decimal import Decimal


class TrackingInfo(pydantic.BaseModel):
    number: str = pydantic.Field(validation_alias="Number")
    status: str = pydantic.Field(validation_alias="Status")
    cargo_description: str | None = pydantic.Field(
        default=None,
        validation_alias="CargoDescriptionString"
    )
    sender_city: str | None = pydantic.Field(
        default=None,
        validation_alias="CitySender"
    )
    sender_warehouse: str | None = pydantic.Field(default=None, validation_alias="WarehouseSender")
    recipient_city: str | None = pydantic.Field(default=None, validation_alias="CityRecipient")
    recipient_warehouse: str | None = pydantic.Field(default=None, validation_alias="WarehouseRecipient")
    recipient_full_name: str | None = pydantic.Field(default=None, validation_alias="RecipientFullName")
    recipient_full_name_ew: str | None = pydantic.Field(default=None, validation_alias="RecipientFullNameEW")
    payer_type: str | None = pydantic.Field(default=None, validation_alias="PayerType")
    payment_method: str | None = pydantic.Field(default=None, validation_alias="PaymentMethod")

    document_cost: Decimal | None = pydantic.Field(default=None, validation_alias="DocumentCost")

    @pydantic.field_validator('document_cost', mode='before')
    @classmethod
    def empty_cost_to_none(cls, value):
        if isinstance(value, str) and value.strip() == "":
            return None
        return value
