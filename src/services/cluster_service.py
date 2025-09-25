# src/services/cluster_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.models.cluster import NewsCluster, NewsClusterItem

class ClusterService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, limit: int = 20, offset: int = 0):
        return (
            self.db.query(NewsCluster)
            .outerjoin(NewsClusterItem, NewsCluster.cluster_id == NewsClusterItem.cluster_id)
            .group_by(NewsCluster.cluster_id)
            .order_by(func.count(NewsClusterItem.id).desc())  # 👈 сортировка по числу новостей
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get(self, cluster_id: int):
        return (
            self.db.query(NewsCluster)
            .filter_by(cluster_id=cluster_id)
            .first()
        )
