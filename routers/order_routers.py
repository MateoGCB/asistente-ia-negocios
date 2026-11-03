from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
from models.user_models import User_db
from models.order_models import OrderStatus
from schemas.order_schemas import OrderView, OrderPage, OwnerOrder, OrderStatusUpdate
from services.order_services import (
    list_orders,
    search_order,
    change_order_status,
    ChangeStatusResult,
    ALLOWED_TRANSITIONS,
    )

# Owner endpoints: JWT required; a business (or order) that is not yours -> 404
router = APIRouter(prefix="/businesses/{business_id}/orders")

@router.get("", response_model=OrderPage)
def orders_list(
    business_id: int,
    view: OrderView | None = None,
    status: OrderStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User_db = Depends(get_current_user),
):
    if view is not None and status is not None:
        raise HTTPException(status_code=422, detail="Use either 'view' or 'status', not both")
    if view is None and status is None:
        view = OrderView.active  # default: what the kitchen needs to see right now
    result = list_orders(business_id, current_user, db, view, status, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return result

@router.get("/{order_id}", response_model=OwnerOrder)
def order_detail(business_id: int, order_id: int, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    order = search_order(business_id, order_id, current_user, db)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.patch("/{order_id}/status", response_model=OwnerOrder)
def order_status_change(business_id: int, order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    result, order = change_order_status(business_id, order_id, status_update.status, current_user, db)
    if result == ChangeStatusResult.not_found:
        raise HTTPException(status_code=404, detail="Order not found")
    if result == ChangeStatusResult.invalid_transition:
        allowed = sorted(s.value for s in ALLOWED_TRANSITIONS[order.status])
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order status from '{order.status.value}' to '{status_update.status.value}'. "
                   f"Allowed: {allowed if allowed else 'none (final status)'}",
        )
    if result == ChangeStatusResult.concurrent_change:
        raise HTTPException(
            status_code=409,
            detail=f"The order changed while you were editing it (it is now '{order.status.value}'). Please reload.",
        )
    return order
