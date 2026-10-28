import pydantic


class CityInfo(pydantic.BaseModel):
    ref: str = pydantic.Field(validation_alias="Ref")
    name: str = pydantic.Field(validation_alias="Description")
    area_name: str = pydantic.Field(validation_alias="AreaDescription")
    settlement_type: str = pydantic.Field(validation_alias="SettlementTypeDescription")