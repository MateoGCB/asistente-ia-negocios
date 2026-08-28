
# services/user_services.py
from sqlalchemy.orm import Session
from models.user_models import User_db
from schemas.user_schemas import UserCreate
from  security import pwd_context



def hash_password(password: str):
    pass_hash = pwd_context.hash(password)
    return pass_hash

def verify_password(plain_password: str, hashed_password: str):
    veri = pwd_context.verify(plain_password, hashed_password)
    return veri 

def create_user(user:UserCreate,db:Session):
    exist = db.query(User_db).filter(User_db.email == user.email).first()
    if exist is not None: 
        return None
    hashed = hash_password(user.password)
    new_user = User_db(name=user.name, email=user.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_user(email: str, password:str ,db:Session):
    exist = db.query(User_db).filter(User_db.email == email).first()
    if exist is None:
        return None
    if not verify_password(password, exist.hashed_password):
        return None
    return exist