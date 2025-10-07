# src/api/news.py
from http.client import HTTPException
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional,List
from datetime import datetime

from src.database.db import get_db
from src.services.news_service import NewsService
from src.schemas.news import NewsOut, PaginatedNews

router = APIRouter(prefix="/news", tags=["News"])


@router.get("/", response_model=PaginatedNews)
def get_news(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    category_ids: Optional[List[int]] = Query(None, alias="category_ids[]"),
    source_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
):
    service = NewsService(db)
    return service.get_paginated(
        page=page,
        per_page=per_page,
        category_ids=category_ids,
        source_id=source_id,
        date_from=date_from,
        date_to=date_to,
    )

@router.get("/{news_id}", response_model=NewsOut)
def get_news_by_id(news_id: int, db: Session = Depends(get_db)):
    service = NewsService(db)
    news = service.get(news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news