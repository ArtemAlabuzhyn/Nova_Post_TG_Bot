from decimal import Decimal

import pydantic


class CreatedShipmentInfo(pydantic.BaseModel):
    document_ref: str = pydantic.Field(validation_alias="Ref")
    document_number: str = pydantic.Field(validation_alias="IntDocNumber")
    delivery_cost: Decimal = pydantic.Field(validation_alias="CostOnSite")