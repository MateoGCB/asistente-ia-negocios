from decimal import Decimal
from pydantic import BaseModel
from models.menu_models import MenuCategory

# Public schemas: only what an anonymous customer may see. Never owner or internal ids.

class PublicMenuItem(BaseModel):
    id : int
    name : str
    description : str
    price : Decimal
    category : MenuCategory

class PublicMenu(BaseModel):
    business_name : str
    menu_name : str
    items : list[PublicMenuItem]
