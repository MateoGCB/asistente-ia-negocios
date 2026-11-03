from fastapi import FastAPI
from routers import business_router, user_routers, menu_routers
from database import Base, engine
from models import business_models, user_models, menu_models

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(business_router.router)
app.include_router(user_routers.router)
app.include_router(menu_routers.router)

