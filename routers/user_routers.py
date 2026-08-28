# routers/user_router.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas.user_schemas import UserCreate, User, UserLogin
from security import create_access_token
from services.user_services import (
    create_user,
    authenticate_user
    )
router = APIRouter()

@router.post("/auth/register", response_model=User)
def user_create(user:UserCreate, db:Session=Depends(get_db)):
    user_new= create_user(user,db)
    if user_new is None:
        raise HTTPException(status_code=409, detail="Email in use; please try another one.")
    return  user_new

@router.post("/auth/login")
def user_login(credential:UserLogin,db:Session=Depends(get_db)):
    user = authenticate_user(credential.email, credential.password, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

