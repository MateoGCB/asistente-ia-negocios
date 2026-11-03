from fastapi import APIRouter, HTTPException, Depends 
from services.business_services import (
    create_business_id,
    search_by_id,
    list_all_businesses,
    update_bus,
    archive_business_by_id,
    unassign_menu,
    )
from schemas.business_schemas import CreateBusiness, Business, BusinessUpdate
from schemas.common_schemas import Message
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
from models.user_models import User_db

router = APIRouter()

@router.post("/businesses/", response_model=Business, status_code=201)
def create_business(business: CreateBusiness,db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    business_obj = create_business_id(business,db,current_user)
    if business_obj is None:
        raise HTTPException(status_code=409, detail="Could not generate a unique slug for this business, please try again")
    return business_obj

@router.get("/businesses/", response_model=list[Business])
def get_businesses(db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    return list_all_businesses(db,current_user)

@router.get("/businesses/{business_id}", response_model=Business)
def get_business(business_id: int, db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    search = search_by_id(business_id, db, current_user)
    if search is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return search

@router.delete("/businesses/{business_id}", response_model=Message)
def delete_business(business_id: int, db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    # Soft delete: the business is archived (its orders and its slug are kept), not removed
    archived = archive_business_by_id(business_id, db, current_user)
    if not archived:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"message": "Business archived successfully"}

@router.delete("/businesses/{business_id}/menu", response_model=Message)
def remove_business_menu(business_id: int, db: Session = Depends(get_db), current_user: User_db = Depends(get_current_user)):
    # Only detaches the menu (menu_id = NULL); the menu and its items are kept. Idempotent.
    if not unassign_menu(business_id, db, current_user):
        raise HTTPException(status_code=404, detail="Business not found")
    return {"message": "Menu removed from business"}

@router.patch("/businesses/{business_id}", response_model=Business)
def update_business(business_id : int, business_update : BusinessUpdate, db: Session= Depends(get_db),current_user: User_db = Depends(get_current_user)):
    update_model = update_bus(business_id, business_update, db, current_user)
    if update_model is None:
        raise HTTPException(status_code=404, detail="Business or menu not found")
    return update_model

