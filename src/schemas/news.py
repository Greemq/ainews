# src/schemas/news.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class CategoryOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class SourceOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class NewsOut(BaseModel):
    id: int
    title: str
    title_ru: Optional[str]
    title_kz: Optional[str]
    title_en: Optional[str]

    summary_ru: Optional[str]
    summary_kz: Optional[str]
    summary_en: Optional[str]

    url: Optional[str]
    published_at: Optional[datetime]
    has_summary: bool

    source: Optional[SourceOut]
    categories: List[CategoryOut] = []

    image_url:Optional[str]

    class Config:
        orm_mode = True


class PaginatedNews(BaseModel):
    page: int
    per_page: int
    total: int
    items: List[NewsOut]
    has_next: bool
