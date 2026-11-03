from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
from schemas.menu_schemas import MenuItemCreate, MenuItemUpdate, MenuItem, MenuCreate, Menu
from models.user_models import User_db
from services.menu_services import (
    create_menu,
    create_item_menu,
    list_menu_items,
    update_menu_item,
    delete_menu_item,
    )

router = APIRouter(prefix="/menus")

@router.post("/", response_model=Menu, status_code=201)
def menu_create(menu: MenuCreate, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    return create_menu(menu, db, current_user)

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

@router.delete("/{menu_id}/items/{item_id}")
def item_delete(menu_id: int, item_id: int, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    deleted = delete_menu_item(item_id, menu_id, db, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted successfully"}
