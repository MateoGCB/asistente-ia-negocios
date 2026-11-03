from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
from schemas.menu_schemas import MenuItemCreate, MenuItemUpdate, MenuItem, MenuCreate, Menu, MenuSummary
from schemas.common_schemas import Message
from models.user_models import User_db
from services.menu_services import (
    create_menu,
    list_menus,
    delete_menu,
    DeleteMenuResult,
    create_item_menu,
    list_menu_items,
    update_menu_item,
    delete_menu_item,
    DeleteItemResult,
    )

router = APIRouter(prefix="/menus")

@router.post("/", response_model=Menu, status_code=201)
def menu_create(menu: MenuCreate, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    return create_menu(menu, db, current_user)

@router.get("/", response_model=list[MenuSummary])
def menus_list(db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    return list_menus(db, current_user)

@router.delete("/{menu_id}", response_model=Message)
def menu_delete(menu_id: int, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    result = delete_menu(menu_id, db, current_user)
    if result == DeleteMenuResult.not_found:
        raise HTTPException(status_code=404, detail="Menu not found")
    if result == DeleteMenuResult.in_use:
        raise HTTPException(
            status_code=409,
            detail="This menu is used by one or more active businesses. Remove it from them first (DELETE /businesses/{business_id}/menu).",
        )
    return {"message": "Menu deleted successfully"}

@router.post("/{menu_id}/items", response_model=MenuItem, status_code=201)
def item_create(menu_id: int, item: MenuItemCreate, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    item_obj = create_item_menu(item, db, menu_id, current_user)
    if item_obj is None:
        raise HTTPException(status_code=404, detail="Menu not found")
    return item_obj

@router.get("/{menu_id}/items", response_model=list[MenuItem])
def items_list(menu_id: int, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    items = list_menu_items(menu_id, db, current_user)
    if items is None:
        raise HTTPException(status_code=404, detail="Menu not found")
    return items

@router.patch("/{menu_id}/items/{item_id}", response_model=MenuItem)
def item_update(menu_id: int, item_id: int, item_update: MenuItemUpdate, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    item_obj = update_menu_item(item_id, menu_id, item_update, db, current_user)
    if item_obj is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item_obj

@router.delete("/{menu_id}/items/{item_id}", response_model=Message)
def item_delete(menu_id: int, item_id: int, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    result = delete_menu_item(item_id, menu_id, db, current_user)
    if result == DeleteItemResult.not_found:
        raise HTTPException(status_code=404, detail="Item not found")
    if result == DeleteItemResult.in_use:
        raise HTTPException(
            status_code=409,
            detail="This item appears in existing orders and cannot be deleted. Mark it as unavailable (available=false) instead.",
        )
    return {"message": "Item deleted successfully"}
