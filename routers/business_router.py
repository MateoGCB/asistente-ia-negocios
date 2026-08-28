from fastapi import APIRouter, HTTPException, Depends 
from services.business_services import (
    create_business_id,
    search_by_id,
    list_all_businesses,
    update_bus,
    delete_business_by_id,
    )
from schemas.business_schemas import CreateBusiness, BusinessUpdate
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
from models.user_models import User_db

router = APIRouter()

@router.post("/businesses/")
def create_business(business: CreateBusiness,db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    business_obj = create_business_id(business,db,current_user)
    return business_obj

@router.get("/businesses/")
def get_businesses(db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    return list_all_businesses(db,current_user)

@router.get("/businesses/{business_id}")
def get_business(business_id: int, db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    search = search_by_id(business_id, db, current_user)
    if search is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return search

@router.delete("/businesses/{business_id}")
def delete_business(business_id: int, db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    deleted = delete_business_by_id(business_id, db, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"message": "Business deleted successfully"}

@router.patch("/businesses/{business_id}")
def update_business(business_id : int, business_update : BusinessUpdate, db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    update_model = update_bus(business_id, business_update, db, current_user)
    if update_model is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return update_model

