import enum
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from models.business_models import Business_db
from models.menu_models import MenuItem_db
from models.order_models import Order_db, OrderItem_db, OrderStatus, CancelReason
from models.user_models import User_db
from schemas.order_schemas import OrderCreate, OrderView
from services.public_services import search_business_by_slug
from services.business_services import search_by_id
from utils.datetime_utils import utc_now, to_utc

ORDER_NUMBER_CONSTRAINT = "orders.business_id, orders.number"
MAX_ORDER_TOTAL = Decimal("10000000")

class CreateOrderError(str, enum.Enum):
    business_not_found = "business_not_found"
    items_unavailable = "items_unavailable"
    total_too_high = "total_too_high"
    number_conflict = "number_conflict"

def next_order_number(business_id: int, db: Session) -> int | None:
    # ONE atomic statement: increment the branch counter and get the new value back.
    # UPDATE business SET next_order_number = next_order_number + 1
    #   WHERE id = ? AND deleted_at IS NULL RETURNING next_order_number
    # It takes SQLite's write lock until commit/rollback, so concurrent orders WAIT here instead of colliding.
    # It runs inside the order's transaction: a rollback also undoes the increment (no gaps).
    # "deleted_at IS NULL": if the business was archived after we looked it up, 0 rows -> None.
    new_value = db.execute(
        update(Business_db)
        .where(Business_db.id == business_id, Business_db.deleted_at.is_(None))
        .values(next_order_number=Business_db.next_order_number + 1)
        .returning(Business_db.next_order_number)
    ).scalar_one_or_none()
    return None if new_value is None else new_value - 1

def create_order(slug: str, order_data: OrderCreate, db: Session) -> Order_db | CreateOrderError:
    # 1) Validate EVERYTHING before writing anything
    business = search_business_by_slug(slug, db)
    if business is None or business.menu_id is None:
        return CreateOrderError.business_not_found

    requested = {item.menu_item_id: item.quantity for item in order_data.items}
    # One query with the three conditions together: exists, belongs to THIS branch's menu, is available.
    # It cannot tell which condition failed, so the error never reveals ids of other businesses.
    menu_items = (
        db.query(MenuItem_db)
        .filter(
            MenuItem_db.id.in_(requested.keys()),
            MenuItem_db.menu_id == business.menu_id,
            MenuItem_db.available.is_(True),
        )
        .all()
    )
    if len(menu_items) != len(requested):
        return CreateOrderError.items_unavailable

    # 2) Snapshot name and price from the DB (the client never sends prices) and compute the total
    lines = [
        {"menu_item_id": item.id, "item_name": item.name, "unit_price": item.price, "quantity": requested[item.id]}
        for item in sorted(menu_items, key=lambda menu_item: menu_item.id)
    ]
    total = sum((line["unit_price"] * line["quantity"] for line in lines), Decimal("0"))
    if total > MAX_ORDER_TOTAL:
        return CreateOrderError.total_too_high
    business_id = business.id

    # 3) Consume the number (only now, after validating) and save order + items with ONE commit
    number = next_order_number(business_id, db)
    if number is None:
        # Archived between the lookup and now: behave exactly like an unknown slug, create nothing
        db.rollback()
        return CreateOrderError.business_not_found
    order = Order_db(
        business_id=business_id,
        number=number,
        customer_name=order_data.customer_name,
        customer_phone=order_data.customer_phone,
        notes=order_data.notes,
        total=total,
        items=[OrderItem_db(**line) for line in lines],
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()  # discards the order, its items AND the counter increment
        if ORDER_NUMBER_CONSTRAINT not in str(error.orig):
            raise  # a different integrity problem: do not hide it
        # With the atomic counter this is not a race: it means inconsistent data (e.g. an order
        # inserted by hand). Retrying would hide it, so we report it instead.
        return CreateOrderError.number_conflict
    db.refresh(order)
    return order

# ===================== Owner side =====================

ACTIVE_STATUSES = (OrderStatus.pending, OrderStatus.confirmed, OrderStatus.preparing, OrderStatus.ready)
CLOSED_STATUSES = (OrderStatus.delivered, OrderStatus.cancelled)

# Single source of truth for the state machine: current status -> statuses it may move to.
# Skipping steps, going back, leaving a final status and "same status" are all just "not in the set".
ALLOWED_TRANSITIONS = {
    OrderStatus.pending: {OrderStatus.confirmed, OrderStatus.cancelled},
    OrderStatus.confirmed: {OrderStatus.preparing, OrderStatus.cancelled},
    OrderStatus.preparing: {OrderStatus.ready, OrderStatus.cancelled},
    OrderStatus.ready: {OrderStatus.delivered, OrderStatus.cancelled},
    OrderStatus.delivered: set(),
    OrderStatus.cancelled: set(),
}

class ChangeStatusResult(str, enum.Enum):
    changed = "changed"
    not_found = "not_found"
    invalid_transition = "invalid_transition"
    concurrent_change = "concurrent_change"

def conditional_status_update(order_id: int, expected_status: OrderStatus, values: dict, db: Session) -> bool:
    # Atomic "compare and set": UPDATE orders SET ... WHERE id = ? AND status = <the status we read>.
    # If someone else changed the order after we read it, the WHERE matches 0 rows and nothing is overwritten.
    updated_rows = (
        db.query(Order_db)
        .filter(Order_db.id == order_id, Order_db.status == expected_status)
        .update(values, synchronize_session=False)
    )
    return updated_rows == 1

def find_ready_orders(business_id: int, db: Session) -> list[Order_db]:
    return db.query(Order_db).filter(Order_db.business_id == business_id, Order_db.status == OrderStatus.ready).all()

def expire_overdue_orders(business: Business_db, db: Session) -> int:
    # Evaluated ON READ (no scheduler): ready orders not picked up within the branch's CURRENT timeout
    # become cancelled / not_picked_up. Called before listing, viewing or changing the status of an order.
    deadline = utc_now() - timedelta(hours=business.pickup_timeout_hours)
    attempted = expired = 0
    for order in find_ready_orders(business.id, db):
        if order.ready_at is None:
            continue  # defensive: a ready order should always have ready_at
        if to_utc(order.ready_at) < to_utc(deadline):
            attempted += 1
            # Same atomic compare-and-set as manual changes: if the owner changed this order in the
            # meantime (e.g. delivered), status is no longer 'ready' and nothing is overwritten
            values = {Order_db.status: OrderStatus.cancelled, Order_db.cancel_reason: CancelReason.not_picked_up}
            if conditional_status_update(order.id, OrderStatus.ready, values, db):
                expired += 1
    if attempted:
        db.commit()  # also expires the session's cached objects, so the following reads see the new status
    return expired

def list_orders(business_id: int, user: User_db, db: Session, view: OrderView | None, status: OrderStatus | None, page: int, page_size: int):
    business = search_by_id(business_id, db, user)
    if business is None:
        return None
    expire_overdue_orders(business, db)
    statuses = [status] if status is not None else (ACTIVE_STATUSES if view == OrderView.active else CLOSED_STATUSES)
    query = (
        db.query(Order_db)
        .options(selectinload(Order_db.items))  # loads all items in one extra query, not one per order
        .filter(Order_db.business_id == business.id, Order_db.status.in_(statuses))
    )
    if all(s in ACTIVE_STATUSES for s in statuses):
        # Active work: oldest first (the kitchen attends them in arrival order), not paginated
        orders = query.order_by(Order_db.created_at.asc(), Order_db.id.asc()).all()
        return {"items": orders, "page": None, "page_size": None, "total": len(orders)}
    # Closed orders: newest first, paginated
    total = query.count()
    orders = (
        query.order_by(Order_db.created_at.desc(), Order_db.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": orders, "page": page, "page_size": page_size, "total": total}

def search_order(business_id: int, order_id: int, user: User_db, db: Session):
    # The order is reached ONLY through a business owned by the user
    business = search_by_id(business_id, db, user)
    if business is None:
        return None
    expire_overdue_orders(business, db)  # first expire, then the caller validates (e.g. a status transition)
    return db.query(Order_db).filter(Order_db.id == order_id, Order_db.business_id == business.id).first()

def change_order_status(business_id: int, order_id: int, new_status: OrderStatus, user: User_db, db: Session):
    order = search_order(business_id, order_id, user, db)
    if order is None:
        return ChangeStatusResult.not_found, None
    read_status = order.status
    if new_status not in ALLOWED_TRANSITIONS[read_status]:
        return ChangeStatusResult.invalid_transition, order
    # Everything that changes goes in the SAME UPDATE, so the row is never half-updated
    values = {Order_db.status: new_status}
    if new_status == OrderStatus.ready:
        values[Order_db.ready_at] = utc_now()
    if new_status == OrderStatus.cancelled:
        values[Order_db.cancel_reason] = CancelReason.owner
    changed = conditional_status_update(order.id, read_status, values, db)
    db.commit()
    db.refresh(order)  # reload what is really in the DB now (ours, or the other request's change)
    if not changed:
        return ChangeStatusResult.concurrent_change, order
    return ChangeStatusResult.changed, order
