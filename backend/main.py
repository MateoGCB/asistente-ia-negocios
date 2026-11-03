import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import business_router, user_routers, menu_routers, public_routers, order_routers
from database import Base, engine
from models import business_models, user_models, menu_models, order_models

DEFAULT_CORS_ORIGINS = ["http://localhost:5173"]  # Vite dev server
CORS_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
CORS_HEADERS = ["Authorization", "Content-Type"]

def parse_cors_origins(raw: str | None) -> list[str]:
    # "a, b ,,c" -> ["a", "b", "c"]. A wildcard is NEVER accepted: only explicit origins.
    # Empty, only spaces/commas, or only "*" -> the default.
    origins = [origin.strip() for origin in (raw or "").split(",")]
    origins = [origin for origin in origins if origin and origin != "*"]
    return origins or list(DEFAULT_CORS_ORIGINS)

def configure_cors(app: FastAPI) -> None:
    # Read at call time (the .env was already loaded by database.py), so tests can try other values
    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_cors_origins(os.environ.get("CORS_ORIGINS")),
        allow_credentials=False,  # the JWT travels in the Authorization header, not in cookies
        allow_methods=CORS_METHODS,
        allow_headers=CORS_HEADERS,
    )

Base.metadata.create_all(bind=engine)

app = FastAPI()
configure_cors(app)
app.include_router(business_router.router)
app.include_router(user_routers.router)
app.include_router(menu_routers.router)
app.include_router(public_routers.router)
app.include_router(order_routers.router)
