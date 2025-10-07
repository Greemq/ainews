from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.models.base import BaseModel


class News(BaseModel):
    __tablename__ = "news"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    url = Column(String(512), nullable=True, unique=True)

    title_ru = Column(String(255), nullable=True)
    title_kz = Column(String(255), nullable=True)
    title_en = Column(String(255), nullable=True)

    summary_ru = Column(Text, nullable=True)
    summary_kz = Column(Text, nullable=True)
    summary_en = Column(Text, nullable=True)

    has_summary = Column(Boolean, default=False)
    image_url = Column(String(255), nullable=True)

    published_at = Column(DateTime, nullable=True)

    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    source = relationship("Source", back_populates="news")
    categories = relationship("Category", secondary="news_categories", back_populates="news")



