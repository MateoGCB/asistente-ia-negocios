from pydantic import BaseModel, Field

class CreateBusiness(BaseModel):
    name : str
    industry : str

class Business(BaseModel):
    id : int
    name : str
    industry : str
    slug : str
    pickup_timeout_hours : int
    menu_id : int | None = None

class BusinessUpdate(BaseModel):
    name : str | None = None
    industry : str | None = None
    menu_id : int | None = None
    pickup_timeout_hours : int | None = Field(default=None, ge=1, le=72)
