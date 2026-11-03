
# services/user_services.py
from sqlalchemy.orm import Session
from models.user_models import User_db
from schemas.user_schemas import UserCreate
from  security import pwd_context, find_user_by_email



def hash_password(password: str):
    pass_hash = pwd_context.hash(password)
    return pass_hash

def verify_password(plain_password: str, hashed_password: str):
    veri = pwd_context.verify(plain_password, hashed_password)
    return veri

def create_user(user:UserCreate,db:Session):
    # user.email arrives already normalized (lowercase) by the schema
    exist = find_user_by_email(user.email, db)
    if exist is not None:
        return None
    hashed = hash_password(user.password)
    new_user = User_db(name=user.name, email=user.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(email: str, password:str ,db:Session):
    exist = find_user_by_email(email, db)
    if exist is None:
        return None
    if not verify_password(password, exist.hashed_password):
        return None
    return exist