from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base
from sqlalchemy.orm import relationship


class Business_db(Base):
    __tablename__ = "business"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True)
    name = Column(String)
    industry = Column(String)   
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User_db", back_populates="businesses")
