# schemas/user_schemas.py
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class User(BaseModel):
    id: int
    name: str
    email: str

class UserLogin(BaseModel):
    email: str
    password: str

