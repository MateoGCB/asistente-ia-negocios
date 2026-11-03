from sqlalchemy import Column, Integer, String, ForeignKey, CheckConstraint
from database import Base
from sqlalchemy.orm import relationship
from models.custom_types import UTCDateTime

class Business_db(Base):
    __tablename__ = "business"
    __table_args__ = (
        # Second barrier: the schema validates 1-72 too, but the DB must never accept other values
        CheckConstraint("pickup_timeout_hours BETWEEN 1 AND 72", name="ck_business_pickup_timeout_range"),
        {"sqlite_autoincrement": True},
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    pickup_timeout_hours = Column(Integer, nullable=False, default=24)
    # Next visible order number of this branch, consumed atomically by create_order (never sent to clients)
    next_order_number = Column(Integer, nullable=False, default=1)
    # Soft delete (INTERIM solution): not NULL = archived. The row stays, so its orders are kept
    # and its slug remains taken forever (the UNIQUE constraint still protects it)
    deleted_at = Column(UTCDateTime)
    owner_id = Column(Integer, ForeignKey("users.id"))
    menu_id = Column(Integer, ForeignKey("menus.id"))
    owner = relationship("User_db", back_populates="businesses")
    menu = relationship("Menu_db", back_populates="businesses")
    orders = relationship("Order_db", back_populates="business")
