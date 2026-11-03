from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from database import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Enum
import enum

class MenuCategory(str, enum.Enum):
    entrada = "entrada"
    plato_principal = "plato_principal"
    postre = "postre"
    bebida = "bebida"
    cafeteria = "cafeteria"

class Menu_db(Base):
    __tablename__ = "menus"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer,primary_key=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User_db", back_populates="menus")
    items = relationship("MenuItem_db", back_populates="menu")
    businesses = relationship("Business_db", back_populates="menu")

class MenuItem_db(Base):
    __tablename__ = "menu_items"
    __table_args__ = {"sqlite_autoincrement": True}
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, ForeignKey("menus.id"))
    name = Column(String)
    description = Column(String)
    price = Column(Numeric(10, 2))
    category = Column(Enum(MenuCategory))
    menu = relationship("Menu_db", back_populates="items")
