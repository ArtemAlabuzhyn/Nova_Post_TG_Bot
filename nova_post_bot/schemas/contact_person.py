import pydantic


class ContactPersonInfo(pydantic.BaseModel):
    ref: str = pydantic.Field(validation_alias="Ref")
    first_name: str = pydantic.Field(validation_alias="FirstName")
    last_name: str = pydantic.Field(validation_alias="LastName")
    phone: str = pydantic.Field(validation_alias="Phones")