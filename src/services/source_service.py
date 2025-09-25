# src/services/news_service.py
from __future__ import annotations

from typing import Optional, Sequence, Dict, Any, Iterable, Tuple
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.source import Source


class SourceService:
    def __init__(self, db: Session):
        self.db = db

    # ======== READ ========
    def get(self, news_id: int) -> Optional[Source]:
        return self.db.get(Source, news_id)
    
    def get_all(self) -> Iterable[Source]:
        return self.db.query(Source).all()
    
    def save(self, source: Source) -> Source:
        try:
            self.db.add(source)
            self.db.commit()
            return source
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Source with URL {source.url} already exists.")

    