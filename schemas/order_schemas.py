from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator
import enum
from models.order_models import OrderStatus, CancelReason
from utils.datetime_utils import to_utc

# ----- Input (public, anonymous customer)

PHONE_MIN_DIGITS = 6
PHONE_MAX_DIGITS = 15

class OrderItemCreate(BaseModel):
    menu_item_id : int
    quantity : int = Field(ge=1, le=50)

class OrderCreate(BaseModel):
    # Strip spaces so "   " cannot pass as a 2-character name
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_name : str = Field(min_length=2, max_length=100)
    customer_phone : str = Field(min_length=6, max_length=20, pattern=r"^\+?[0-9 \-]+$")
    notes : str | None = Field(default=None, max_length=300)
    items : list[OrderItemCreate] = Field(min_length=1, max_length=30)

    @field_validator("customer_phone")
    @classmethod
    def require_real_digits(cls, phone: str) -> str:
        # The pattern allows "------"; a phone also needs at least 6 actual digits,
        # and at most 15 (the international maximum, E.164)
        digits = sum(char.isdigit() for char in phone)
        if digits < PHONE_MIN_DIGITS:
            raise ValueError(f"Phone must contain at least {PHONE_MIN_DIGITS} digits")
        if digits > PHONE_MAX_DIGITS:
            raise ValueError(f"Phone must contain at most {PHONE_MAX_DIGITS} digits")
        # Separators may not be repeated ("  " or "--"); a mixed " - " like "351 - 1234567" is allowed.
        # Accepted limitation: two short numbers in the same field ("110000 110001") cannot be told
        # apart from ONE number written with spaces, so they pass as long as they total 6-15 digits.
        if "  " in phone or "--" in phone:
            raise ValueError("Phone cannot contain two consecutive spaces or hyphens")
        return phone

    @field_validator("notes")
    @classmethod
    def empty_notes_to_none(cls, notes: str | None) -> str | None:
        # Already stripped by str_strip_whitespace: "" means empty or only spaces
        return notes or None

    @field_validator("items")
    @classmethod
    def reject_repeated_items(cls, items: list[OrderItemCreate]) -> list[OrderItemCreate]:
        ids = [item.menu_item_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each menu_item_id can appear only once; use quantity instead")
        return items

# ----- Output (public): no internal ids, no owner data

class PublicOrderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Read from the snapshot column item_name, shown to the customer as "name"
    name : str = Field(validation_alias="item_name")
    unit_price : Decimal
    quantity : int

class PublicOrder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number : int
    status : OrderStatus
    total : Decimal
    customer_name : str
    created_at : datetime
    items : list[PublicOrderItem]

    @field_validator("created_at")
    @classmethod
    def created_at_as_utc(cls, value: datetime) -> datetime:
        # SQLite returns it naive; send it explicitly marked as UTC
        return to_utc(value)

# ----- Owner side (JWT)

class OrderView(str, enum.Enum):
    active = "active"
    history = "history"

class OrderStatusUpdate(BaseModel):
    status : OrderStatus

class OwnerOrder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id : int
    number : int
    customer_name : str
    customer_phone : str
    notes : str | None = None
    items : list[PublicOrderItem]
    total : Decimal
    status : OrderStatus
    created_at : datetime
    ready_at : datetime | None = None
    cancel_reason : CancelReason | None = None

    @field_validator("created_at", "ready_at")
    @classmethod
    def dates_as_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else to_utc(value)

class OrderPage(BaseModel):
    items : list[OwnerOrder]
    page : int | None = None       # None in view=active (not paginated)
    page_size : int | None = None
    total : int
