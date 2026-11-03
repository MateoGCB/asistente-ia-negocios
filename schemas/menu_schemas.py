from decimal import Decimal
from pydantic import BaseModel, Field
from models.menu_models import MenuCategory

class MenuItemCreate(BaseModel):
    name : str
    description : str
    price : Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category : MenuCategory

class MenuItemUpdate(BaseModel):
    name : str | None = None
    description : str | None = None
    price : Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category : MenuCategory | None = None
    available : bool | None = None

class MenuItem(BaseModel):
    id : int
    name : str
    description : str
    price : Decimal
    category : MenuCategory
    available : bool

class MenuCreate(BaseModel):
    name : str
class Menu(BaseModel):
    id : int
    name : str
