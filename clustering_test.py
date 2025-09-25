from src.services.clustering_service import ClusteringService
from src.database.db import get_db, get_db_pg
from dotenv import load_dotenv

def main():
    load_dotenv()
    mysql_db = next(get_db())
    pg_db = next(get_db_pg())

    service = ClusteringService(mysql_db, pg_db)

    # Тест 1: Генерация эмбеддингов
    print("=== Генерируем эмбеддинги ===")
    service.process_recent_news(hours=72)
    
    # Тест 2: Кластеризация
    print("\n=== Запускаем кластеризацию ===")
    service.run_clustering(hours=72, min_cluster_size=5, min_samples=3)
    
    # Тест 3: Проверяем результаты (через SQL)
    print("\n=== Проверяем результаты ===")
    from sqlalchemy import text
    
    # Смотрим последние кластеры
    sql = text("""
        SELECT c.cluster_id, c.label, COUNT(ci.news_id) as count
        FROM news_clusters c
        LEFT JOIN news_cluster_items ci ON c.cluster_id = ci.cluster_id
        WHERE c.created_at >= NOW() - INTERVAL '1 hour'
        GROUP BY c.cluster_id, c.label
        ORDER BY c.created_at DESC
    """)
    
    clusters = pg_db.execute(sql).fetchall()
    for cluster in clusters:
        print(f"Кластер {cluster.cluster_id}: {cluster.count} статей")
        
        # Показываем статьи кластера
        articles_sql = text("""
            SELECT ne.title 
            FROM news_cluster_items ci
            JOIN news_embeddings ne ON ci.news_id = ne.news_id
            WHERE ci.cluster_id = :cluster_id
            LIMIT 10
        """)
        articles = pg_db.execute(articles_sql, {"cluster_id": cluster.cluster_id}).fetchall()
        for art in articles:
            print(f"  - {art.title}")

if __name__ == "__main__":
    main()