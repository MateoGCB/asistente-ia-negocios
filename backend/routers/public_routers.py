from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas.public_schemas import PublicMenu
from schemas.order_schemas import OrderCreate, PublicOrder
from services.public_services import get_public_menu
from services.order_services import create_order, CreateOrderError

# Public endpoints: NO get_current_user. Anything returned here is visible to anyone.
router = APIRouter(prefix="/public")

@router.get("/{slug}/menu", response_model=PublicMenu)
def public_menu(slug: str, db: Session = Depends(get_db)):
    menu = get_public_menu(slug, db)
    if menu is None:
        raise HTTPException(status_code=404, detail="Menu not found")
    return menu

@router.post("/{slug}/orders", response_model=PublicOrder, status_code=201)
def public_order_create(slug: str, order_data: OrderCreate, db: Session = Depends(get_db)):
    result = create_order(slug, order_data, db)
    if result == CreateOrderError.business_not_found:
        raise HTTPException(status_code=404, detail="Menu not found")
    if result == CreateOrderError.items_unavailable:
        raise HTTPException(status_code=409, detail="One or more items are not available")
    if result == CreateOrderError.total_too_high:
        raise HTTPException(status_code=422, detail="The order total exceeds the maximum allowed (10000000.00)")
    if result == CreateOrderError.number_conflict:
        raise HTTPException(status_code=409, detail="Could not create the order, please try again")
    return result
