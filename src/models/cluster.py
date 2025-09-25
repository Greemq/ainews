# src/models/cluster.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import Base  # именно Base, не BaseModel (см. news.py)

class NewsCluster(Base):
    __tablename__ = "news_clusters"

    cluster_id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False)
    label = Column(String(255), nullable=True)
    theme = Column(String(255), nullable=True)

    items = relationship("NewsClusterItem", back_populates="cluster")


class NewsClusterItem(Base):
    __tablename__ = "news_cluster_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("news_clusters.cluster_id"), nullable=False)
    news_id = Column(Integer, nullable=False)

    cluster = relationship("NewsCluster", back_populates="items")
