from sqlalchemy.orm import Session
from models.menu_models import MenuItem_db, Menu_db
from schemas.menu_schemas import MenuItemCreate, MenuItemUpdate, MenuCreate
from models.user_models import User_db

def create_menu(menu: MenuCreate, db: Session, user_auth: User_db):
    menu_obj = Menu_db(name=menu.name, owner_id=user_auth.id)
    db.add(menu_obj)
    db.commit()
    db.refresh(menu_obj)
    return menu_obj

def search_menu_by_id(menu_id: int, db: Session, user: User_db):
    return db.query(Menu_db).filter(Menu_db.id == menu_id, Menu_db.owner_id == user.id).first()

def create_item_menu(item: MenuItemCreate, db: Session, id_menu: int, user: User_db):
    menu = search_menu_by_id(id_menu, db, user)
    if menu is None:
        return None
    item_obj = MenuItem_db(name=item.name, description=item.description, price=item.price, category=item.category, menu_id=id_menu)
    db.add(item_obj)
    db.commit()
    db.refresh(item_obj)
    return item_obj

def list_menu_items(id_menu: int, db: Session, user: User_db):
    menu = search_menu_by_id(id_menu, db, user)
    if menu is None:
        return None
    return menu.items

def search_item_by_id(item_id: int, id_menu: int, db: Session, user: User_db):
    # The item is always reached through a menu owned by the user
    return (
        db.query(MenuItem_db)
        .join(Menu_db, MenuItem_db.menu_id == Menu_db.id)
        .filter(MenuItem_db.id == item_id, MenuItem_db.menu_id == id_menu, Menu_db.owner_id == user.id)
        .first()
    )

def update_menu_item(item_id: int, id_menu: int, item_update: MenuItemUpdate, db: Session, user: User_db):
    stored_item = search_item_by_id(item_id, id_menu, db, user)
    if stored_item is None:
        return None
    update_data = item_update.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in update_data.items():
        setattr(stored_item, field, value)
    db.commit()
    db.refresh(stored_item)
    return stored_item

def delete_menu_item(item_id: int, id_menu: int, db: Session, user: User_db):
    stored_item = search_item_by_id(item_id, id_menu, db, user)
    if stored_item is None:
        return False
    db.delete(stored_item)
    db.commit()
    return True
