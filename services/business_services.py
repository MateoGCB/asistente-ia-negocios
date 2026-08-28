
from schemas.business_schemas import CreateBusiness, Business, BusinessUpdate
from models.business_models import Business_db
from models.user_models import User_db
from sqlalchemy.orm import Session



def create_business_id(business:CreateBusiness, db:Session, user_auth:User_db):
    business_obj = Business_db(name=business.name, industry=business.industry, owner_id=user_auth.id)
    db.add(business_obj)
    db.commit()
    db.refresh(business_obj)
    return business_obj

def search_by_id(business_id: int, db: Session, user:User_db):
    return db.query(Business_db).filter(Business_db.id == business_id, Business_db.owner_id == user.id).first()


def list_all_businesses(db: Session,user:User_db):
    return db.query(Business_db).filter(Business_db.owner_id == user.id).all()

def update_bus (business_id : int, business_update : BusinessUpdate, db:Session, user:User_db):
    stored_business_data = search_by_id(business_id, db, user)
    if stored_business_data is None:
        return None
    update_data = business_update.model_dump(exclude_unset=True)
    for campo, valor in update_data.items():
        setattr(stored_business_data, campo, valor)
    db.commit()
    db.refresh(stored_business_data)
    return stored_business_data


def delete_business_by_id(business_id: int, db:Session, user:User_db):
    obj = search_by_id(business_id, db, user)
    if not obj:
        return False   
    db.delete(obj)
    db.commit()
    return True

