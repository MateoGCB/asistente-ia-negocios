import re
import unicodedata
from schemas.business_schemas import CreateBusiness, Business, BusinessUpdate
from models.business_models import Business_db
from models.user_models import User_db
from services.menu_services import search_menu_by_id
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from utils.datetime_utils import utc_now

FALLBACK_SLUG = "sucursal"
SLUG_MAX_ATTEMPTS = 2  # first try + one retry

def slugify(text: str) -> str:
    # "Pizzería Popular Centro" -> "pizzeria-popular-centro"
    # NFKD splits "í" into "i" + accent mark; encoding to ASCII drops the mark (and emojis)
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    # Any run of characters that is not a-z or 0-9 becomes a single hyphen
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug or FALLBACK_SLUG

def generate_unique_slug(name: str, db: Session) -> str:
    # Slugs are public URLs, so they must be unique across ALL users, not per owner
    base_slug = slugify(name)
    slug = base_slug
    suffix = 2
    # Queries Business_db directly (NOT query_active_businesses): archived slugs are never reused
    while db.query(Business_db).filter(Business_db.slug == slug).first() is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug

def create_business_id(business:CreateBusiness, db:Session, user_auth:User_db):
    # Two requests can compute the same free slug at the same time; the UNIQUE constraint
    # rejects the second INSERT. In that case: recompute the slug and retry ONCE.
    for _ in range(SLUG_MAX_ATTEMPTS):
        business_obj = Business_db(
            name=business.name,
            industry=business.industry,
            slug=generate_unique_slug(business.name, db),
            pickup_timeout_hours=business.pickup_timeout_hours,
            owner_id=user_auth.id,
        )
        db.add(business_obj)
        try:
            db.commit()
        except IntegrityError as error:
            db.rollback()
            if "business.slug" not in str(error.orig):
                raise  # a different integrity problem: do not hide it
            continue
        db.refresh(business_obj)
        return business_obj
    return None

def query_active_businesses(db: Session):
    # THE single place where archived businesses are filtered out. Every lookup that should treat
    # an archived business as non-existent (by id, list, by slug) must start from this query.
    # Exception on purpose: generate_unique_slug queries Business_db directly (archived slugs stay taken).
    return db.query(Business_db).filter(Business_db.deleted_at.is_(None))

def search_by_id(business_id: int, db: Session, user:User_db):
    return query_active_businesses(db).filter(Business_db.id == business_id, Business_db.owner_id == user.id).first()


def list_all_businesses(db: Session,user:User_db):
    return query_active_businesses(db).filter(Business_db.owner_id == user.id).all()

def update_bus (business_id : int, business_update : BusinessUpdate, db:Session, user:User_db):
    stored_business_data = search_by_id(business_id, db, user)
    if stored_business_data is None:
        return None
    update_data = business_update.model_dump(exclude_unset=True, exclude_none=True)
    # A menu can only be assigned if it belongs to the same user
    if "menu_id" in update_data and search_menu_by_id(update_data["menu_id"], db, user) is None:
        return None
    for campo, valor in update_data.items():
        setattr(stored_business_data, campo, valor)
    db.commit()
    db.refresh(stored_business_data)
    return stored_business_data


def archive_business_by_id(business_id: int, db:Session, user:User_db):
    # Soft delete with a conditional UPDATE: WHERE id = ? AND owner_id = ? AND deleted_at IS NULL.
    # Already archived, not yours or non-existent -> 0 rows -> False (404). Two simultaneous archives: one wins.
    archived_rows = (
        db.query(Business_db)
        .filter(Business_db.id == business_id, Business_db.owner_id == user.id, Business_db.deleted_at.is_(None))
        .update({Business_db.deleted_at: utc_now()}, synchronize_session=False)
    )
    db.commit()
    return archived_rows == 1

