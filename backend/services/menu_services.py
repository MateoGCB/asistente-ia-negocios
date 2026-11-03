import enum
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session
from models.business_models import Business_db
from models.menu_models import MenuItem_db, Menu_db
from models.order_models import OrderItem_db
from schemas.menu_schemas import MenuItemCreate, MenuItemUpdate, MenuCreate
from models.user_models import User_db

class DeleteItemResult(str, enum.Enum):
    deleted = "deleted"
    not_found = "not_found"
    in_use = "in_use"

class DeleteMenuResult(str, enum.Enum):
    deleted = "deleted"
    not_found = "not_found"
    in_use = "in_use"  # used by at least one ACTIVE business

def create_menu(menu: MenuCreate, db: Session, user_auth: User_db):
    menu_obj = Menu_db(name=menu.name, owner_id=user_auth.id)
    db.add(menu_obj)
    db.commit()
    db.refresh(menu_obj)
    return menu_obj

def search_menu_by_id(menu_id: int, db: Session, user: User_db):
    return db.query(Menu_db).filter(Menu_db.id == menu_id, Menu_db.owner_id == user.id).first()

def list_menus(db: Session, user: User_db):
    # ONE aggregated query (not one per menu). LEFT JOIN so a menu without items still appears with 0.
    return (
        db.query(Menu_db.id, Menu_db.name, func.count(MenuItem_db.id).label("items_count"))
        .outerjoin(MenuItem_db, MenuItem_db.menu_id == Menu_db.id)
        .filter(Menu_db.owner_id == user.id)
        .group_by(Menu_db.id, Menu_db.name)
        .order_by(Menu_db.id)
        .all()
    )

def delete_menu(id_menu: int, db: Session, user: User_db) -> DeleteMenuResult:
    # 1) Previous read, only to tell 404 from 409. Missing and foreign menus look the same.
    if search_menu_by_id(id_menu, db, user) is None:
        return DeleteMenuResult.not_found

    # 2) Everything else in ONE transaction. Order: archived businesses, items, menu (foreign keys).
    # Archived businesses may still point to the menu: detach them (they are not shown anywhere).
    db.execute(
        update(Business_db)
        .where(Business_db.menu_id == id_menu, Business_db.deleted_at.is_not(None))
        .values(menu_id=None)
    )
    db.execute(delete(MenuItem_db).where(MenuItem_db.menu_id == id_menu))
    # 3) The menu is deleted with a CONDITIONAL DELETE: the "no ACTIVE business uses it" check is part
    # of the same statement, so no business can start using it between the check and the delete.
    # (In SQLite the first write above already took the write lock until commit.)
    used_by_active_business = (
        select(Business_db.id)
        .where(Business_db.menu_id == id_menu, Business_db.deleted_at.is_(None))
        .exists()
    )
    deleted = db.execute(
        delete(Menu_db).where(Menu_db.id == id_menu, Menu_db.owner_id == user.id, ~used_by_active_business)
    ).rowcount
    if deleted != 1:
        db.rollback()  # undoes the detached businesses and the deleted items too: nothing changes
        if search_menu_by_id(id_menu, db, user) is None:
            return DeleteMenuResult.not_found  # deleted by a simultaneous request
        return DeleteMenuResult.in_use
    db.commit()
    return DeleteMenuResult.deleted

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

def delete_menu_item(item_id: int, id_menu: int, db: Session, user: User_db) -> DeleteItemResult:
    # Ownership is checked FIRST: another user gets "not found", never learns about our orders
    stored_item = search_item_by_id(item_id, id_menu, db, user)
    if stored_item is None:
        return DeleteItemResult.not_found
    # An item that appears in past orders is kept; the owner should set available=False instead
    used_in_orders = db.query(OrderItem_db).filter(OrderItem_db.menu_item_id == item_id).first() is not None
    if used_in_orders:
        return DeleteItemResult.in_use
    db.delete(stored_item)
    db.commit()
    return DeleteItemResult.deleted
