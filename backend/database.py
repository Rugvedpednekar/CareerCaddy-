from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import get_database_url

DATABASE_URL = get_database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    from . import models
    Base.metadata.create_all(bind=engine)
