import enum
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy import Enum
from sqlalchemy.orm import relationship
from database import Base
from models.custom_types import UTCDateTime
from utils.datetime_utils import utc_now

class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    delivered = "delivered"
    cancelled = "cancelled"

class CancelReason(str, enum.Enum):
    owner = "owner"
    not_picked_up = "not_picked_up"

class Order_db(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # The visible number is unique per branch, not globally
        UniqueConstraint("business_id", "number", name="uq_orders_business_number"),
        {"sqlite_autoincrement": True},
    )

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("business.id"), nullable=False)
    number = Column(Integer, nullable=False)
    customer_name = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    notes = Column(String)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.pending)
    total = Column(Numeric(10, 2), nullable=False)
    # UTCDateTime: converts to UTC on write and returns aware UTC on read (SQLite has no timezones)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)
    ready_at = Column(UTCDateTime)
    cancel_reason = Column(Enum(CancelReason))
    business = relationship("Business_db", back_populates="orders")
    items = relationship("OrderItem_db", back_populates="order")

class OrderItem_db(Base):
    __tablename__ = "order_items"
    __table_args__ = {"sqlite_autoincrement": True}

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    # Snapshots: later changes to the menu item must not alter past orders
    item_name = Column(String, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    order = relationship("Order_db", back_populates="items")
    menu_item = relationship("MenuItem_db", back_populates="order_items")
