import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv()
class Config:
    # MySQL через Docker на порту 3307
    SQLALCHEMY_DATABASE_URI = os.getenv("MYSQL_URI")
    POSTGRES_URI = os.getenv("POSTGRES_URI")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
