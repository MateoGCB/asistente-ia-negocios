from fastapi import FastAPI
from routers import business_router, user_routers, menu_routers, public_routers, order_routers
from database import Base, engine
from models import business_models, user_models, menu_models, order_models

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(business_router.router)
app.include_router(user_routers.router)
app.include_router(menu_routers.router)
app.include_router(public_routers.router)
app.include_router(order_routers.router)

