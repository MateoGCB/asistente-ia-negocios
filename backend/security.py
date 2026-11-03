import os
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from fastapi import Depends, HTTPException
from jose import JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user_models import User_db
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db


# The .env is loaded by database.py (imported above, so it always runs before this line)
# Fails on startup (KeyError) if SECRET_KEY is missing, instead of running with an insecure default
SECRET_KEY = os.environ["SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

bearer_scheme = HTTPBearer()


def find_user_by_email(email: str, db: Session) -> User_db | None:
    # Case-insensitive on BOTH sides: new users are stored in lowercase, but older rows may
    # still have capitals; this way they keep working without migrating the data.
    # The single place where users are looked up by email (register, login, token).
    return db.query(User_db).filter(func.lower(User_db.email) == email.lower()).first()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    if not isinstance(email, str):
        # A token without a text "sub" can never belong to a user
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = find_user_by_email(email, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return user