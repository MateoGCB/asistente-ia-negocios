from pydantic import BaseModel

class CreateBusiness(BaseModel):
    name : str
    industry : str

class Business(BaseModel):
    id : int
    name : str
    industry : str

class BusinessUpdate(BaseModel):
    name : str | None = None
    industry : str | None = None