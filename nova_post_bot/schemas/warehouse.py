import pydantic


class WarehouseInfo(pydantic.BaseModel):
    ref: str = pydantic.Field(validation_alias="Ref")
    name: str = pydantic.Field(validation_alias="Description")
    number: str = pydantic.Field(validation_alias="Number")
    city_ref: str = pydantic.Field(validation_alias="CityRef")