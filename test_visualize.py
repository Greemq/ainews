import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import umap
from sqlalchemy import text
from src.database.db import get_db_pg


def fetch_embeddings(pg_db, hours: int = 24):
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    sql = text("""
        SELECT news_id, embedding
        FROM news_embeddings
        WHERE created_at >= :cutoff
    """)
    rows = pg_db.execute(sql, {"cutoff": cutoff}).fetchall()

    ids, vectors = [], []
    for r in rows:
        ids.append(r.news_id)
        if isinstance(r.embedding, str):
            vec = np.fromstring(r.embedding.strip("[]"), sep=",")
        else:
            vec = np.array(r.embedding, dtype=float)
        vectors.append(vec)

    return ids, np.vstack(vectors)


def visualize_embeddings(vectors, labels=None, method="umap"):
    if method == "umap":
        reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine")
        reduced = reducer.fit_transform(vectors)
    else:  # tsne
        reducer = TSNE(n_components=2, perplexity=30, n_iter=1000)
        reduced = reducer.fit_transform(vectors)

    plt.figure(figsize=(10, 8))
    if labels is None:
        plt.scatter(reduced[:, 0], reduced[:, 1], s=20, alpha=0.7)
    else:
        scatter = plt.scatter(reduced[:, 0], reduced[:, 1], c=labels, cmap="tab20", s=20, alpha=0.7)
        plt.legend(*scatter.legend_elements(), title="Cluster")

    plt.title(f"Embeddings visualization ({method})")
    plt.show()


if __name__ == "__main__":
    pg_db = next(get_db_pg())
    ids, vectors = fetch_embeddings(pg_db, hours=24)

    print(f"Взято {len(ids)} статей, размер эмбеддинга = {vectors.shape}")

    # если хочешь без кластеров
    visualize_embeddings(vectors, method="umap")

    # или если у тебя уже есть метки HDBSCAN
    # from src.services.clustering_service import ClusteringService
    # labels = HDBSCAN(...).fit_predict(vectors)
    # visualize_embeddings(vectors, labels, method="umap")
