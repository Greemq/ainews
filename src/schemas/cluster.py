# src/schemas/cluster.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class ClusterItemOut(BaseModel):
    id: int
    news_id: int

    class Config:
        from_attributes = True   # вместо orm_mode


class ClusterOut(BaseModel):
    cluster_id: int
    created_at: datetime
    label: Optional[str] = None
    theme: Optional[str] = None
    items: List[ClusterItemOut] = []

    class Config:
        from_attributes = True   # вместо orm_mode
