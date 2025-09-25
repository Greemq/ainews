# src/api/clusters.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from src.database.db import get_db_pg
from src.services.cluster_service import ClusterService
from src.schemas.cluster import ClusterOut

router = APIRouter(prefix="/clusters", tags=["Clusters"])


@router.get("/", response_model=list[ClusterOut])
def get_clusters(
    db: Session = Depends(get_db_pg),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
):
    service = ClusterService(db)
    offset = (page - 1) * per_page
    return service.get_all(limit=per_page, offset=offset)


@router.get("/{cluster_id}", response_model=ClusterOut)
def get_cluster(cluster_id: int, db: Session = Depends(get_db_pg)):
    service = ClusterService(db)
    cluster = service.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster
