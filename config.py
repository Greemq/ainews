import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    # MySQL через Docker на порту 3307
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://user@127.0.0.1:3306/db"
    )

    # Postgres + pgvector через Docker на порту 5433
    POSTGRES_URI = os.getenv(
        "POSTGRES_URI",
        "postgresql+psycopg2://postgres@127.0.0.1:5432/db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
