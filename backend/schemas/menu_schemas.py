from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from models.menu_models import MenuCategory

# str_strip_whitespace: spaces at the edges are removed BEFORE checking the length,
# so a name of only spaces becomes "" and fails min_length=1

class MenuItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name : str = Field(min_length=1, max_length=100)
    description : str = Field(min_length=1, max_length=500)  # required, as it was
    price : Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category : MenuCategory

class MenuItemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # null is still allowed here and ignored by the service (exclude_none)
    name : str | None = Field(default=None, min_length=1, max_length=100)
    description : str | None = Field(default=None, min_length=1, max_length=500)
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
    model_config = ConfigDict(str_strip_whitespace=True)

    name : str = Field(min_length=1, max_length=100)

class Menu(BaseModel):
    id : int
    name : str
