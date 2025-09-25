# src/services/news_service.py
from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from src.models.category import Category


class CategoryService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self) -> Iterable[Category]:
        return self.db.query(Category).all()
    

    