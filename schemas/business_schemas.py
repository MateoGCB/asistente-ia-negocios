from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_PICKUP_TIMEOUT_HOURS = 24

# str_strip_whitespace: spaces at the edges are removed BEFORE checking the length,
# so "   " becomes "" and fails min_length=1 (an invisible name is not a name)

class CreateBusiness(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name : str = Field(min_length=1, max_length=100)
    industry : str = Field(min_length=1, max_length=60)
    pickup_timeout_hours : int = Field(default=DEFAULT_PICKUP_TIMEOUT_HOURS, ge=1, le=72)

    @field_validator("pickup_timeout_hours", mode="before")
    @classmethod
    def null_means_default(cls, value):
        # API rule: in an OPTIONAL field with a default, null means "not sent" -> use the default.
        # mode="before" runs before the int check, so the default still goes through ge/le.
        return DEFAULT_PICKUP_TIMEOUT_HOURS if value is None else value

class Business(BaseModel):
    id : int
    name : str
    industry : str
    slug : str
    pickup_timeout_hours : int
    menu_id : int | None = None

class BusinessUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # null is still allowed here and ignored by the service (exclude_none)
    name : str | None = Field(default=None, min_length=1, max_length=100)
    industry : str | None = Field(default=None, min_length=1, max_length=60)
    menu_id : int | None = None
    pickup_timeout_hours : int | None = Field(default=None, ge=1, le=72)
