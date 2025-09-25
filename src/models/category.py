from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import BaseModel


class Category(BaseModel):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)

    news = relationship("News", secondary="news_categories", back_populates="categories")

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}