import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load .env here: database.py is imported before security.py, so loading it later would ignore
# DATABASE_URL. Variables already defined in the environment win over the .env (override=False).
load_dotenv()

# Optional override (used by the test suite so it never touches the real database)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./businesses.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread":False})
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()