from sqlalchemy.orm import Session
from models.business_models import Business_db
from models.menu_models import MenuItem_db
from schemas.public_schemas import PublicMenu, PublicMenuItem
from services.business_services import query_active_businesses

def search_business_by_slug(slug: str, db: Session):
    # Archived businesses are filtered centrally: an archived slug gives the same 404 as an unknown one
    return query_active_businesses(db).filter(Business_db.slug == slug).first()

def get_public_menu(slug: str, db: Session):
    # Unknown slug and a branch without a menu return the same None: the router answers the same 404
    business = search_business_by_slug(slug, db)
    if business is None or business.menu is None:
        return None
    available_items = (
        db.query(MenuItem_db)
        .filter(MenuItem_db.menu_id == business.menu_id, MenuItem_db.available.is_(True))
        .order_by(MenuItem_db.id)
        .all()
    )
    return PublicMenu(
        business_name=business.name,
        menu_name=business.menu.name,
        items=[PublicMenuItem.model_validate(item, from_attributes=True) for item in available_items],
    )
