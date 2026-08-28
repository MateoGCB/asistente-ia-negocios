from sqlalchemy import Column, Integer, String
from database import Base
from sqlalchemy.orm import relationship

class User_db(Base):
    __tablename__ = "users"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    businesses = relationship("Business_db", back_populates="owner")