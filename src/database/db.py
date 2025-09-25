from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import news, source, category 
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


engine_pg = create_engine(Config.POSTGRES_URI, echo=False)
SessionLocalPG = sessionmaker(autocommit=False, autoflush=False, bind=engine_pg)

def get_db_pg():
    db = SessionLocalPG()
    try:
        yield db
    finally:
        db.close()