import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:mysql@localhost/news_db"
    )
    POSTGRES_URI = "postgresql+psycopg2://postgres:123@localhost:5433/newsdb"
    SQLALCHEMY_TRACK_MODIFICATIONS = False