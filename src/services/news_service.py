# src/services/news_service.py
from __future__ import annotations

from ast import List
from typing import Optional, Sequence, Dict, Any, Iterable, Tuple
from datetime import datetime,timedelta

from sqlalchemy import select, or_,exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.news import News
from src.models.category import Category
import os
import random

import logging
class NewsService:
    def __init__(self, db: Session):
        self.db = db
        self.image_files = [
            "news_1759743147.png",
            "news_1759743183.png",
            "news_1759743285.png",
            "news_1759743328.png",
        ]
        self.image_path = "/images/news/" 

    # ======== READ ========
    def get(self, news_id: int) -> Optional[News]:
        news = self.db.get(News, news_id)
        if news:
            # временно добавляем рандомное изображение
            setattr(news, "image_url", self.image_path + random.choice(self.image_files))
        return news
    
    def get_all(self) -> Iterable[News]:
        return self.db.query(News).all()

    def get_by_url(self, url: str) -> Optional[News]:
        stmt = select(News).where(News.url == url)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def get_pending_summaries(self) -> list[News]:
        now_utc = datetime.utcnow()
        one_day_ago = now_utc - timedelta(days=1)

        stmt = (
            select(News)
            .where(
                or_(News.has_summary.is_(False), News.has_summary.is_(None))
            )
            .where(News.published_at >= one_day_ago)
        )
        return self.db.execute(stmt).scalars().all()
    
    def save(self, news: News) -> News:
        try:
            self.db.add(news)
            self.db.commit()
            return news
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"News with URL {news.url} already exists.")
        
    
    def get_paginated(
        self,
        page: int = 1,
        per_page: int = 10,
        category_ids: Optional[List[int]] = None,
        source_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        query = self.db.query(News)

        # ✅ только те, у кого есть summary
        query = query.filter(News.has_summary.is_(True))

        if category_ids:
            query = query.filter(
                News.categories.any(Category.id.in_(category_ids))
            )
        if source_id:
            query = query.filter(News.source_id == source_id)
        if date_from:
            query = query.filter(News.published_at >= date_from)
        if date_to:
            query = query.filter(News.published_at <= date_to)


        total = query.count()
        items = (
            query.order_by(News.published_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )


        for news in items:
            setattr(news, "image_url", self.image_path + random.choice(self.image_files))
        return {
            "page": page,
            "per_page": per_page,
            "total": total,
            "items": items,
            "has_next": (page * per_page) < total
        }
