from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import numpy as np
import hdbscan
from collections import Counter
import json

from src.services.gpt_service import GPTservice
from src.models.news import News
from sqlalchemy import text


class ClusteringService:
    def __init__(self, mysql_db: Session, pg_db: Session):
        """
        :param mysql_db: сессия MySQL (основная база со статьями)
        :param pg_db: сессия Postgres (для эмбеддингов и кластеров)
        """
        self.mysql_db = mysql_db
        self.pg_db = pg_db
        self.gpt = GPTservice()

    # ============================
    #   ЭМБЕДДИНГИ
    # ============================
    def fetch_recent_news(self, hours: int = 24) -> List[News]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.mysql_db.query(News)
            .filter(News.published_at >= cutoff)
            .filter(News.has_summary.is_(True))
            .all()
        )

    def embedding_exists(self, news_id: int) -> bool:
        sql = text("SELECT 1 FROM news_embeddings WHERE news_id = :news_id")
        row = self.pg_db.execute(sql, {"news_id": news_id}).fetchone()
        return row is not None

    def save_embedding(self, news_id: int, title: str, summary: str, embedding: List[float]):
        insert_sql = text("""
            INSERT INTO news_embeddings (news_id, title, summary, embedding, created_at)
            VALUES (:news_id, :title, :summary, :embedding, NOW())
        """)
        self.pg_db.execute(insert_sql, {
            "news_id": news_id,
            "title": title,
            "summary": summary,
            "embedding": embedding
        })
        self.pg_db.commit()
        print(f"[OK] Embedding сохранён для news_id={news_id}")

    def process_recent_news(self, hours: int = 24):
        articles = self.fetch_recent_news(hours=hours)
        for art in articles:
            try:
                if self.embedding_exists(art.id):
                    print(f"[SKIP] Embedding уже существует для news_id={art.id}")
                    continue

                text_for_emb = art.summary_ru or art.title
                embedding = self.gpt.get_embedding(text_for_emb)
                self.save_embedding(art.id, art.title, text_for_emb, embedding)

            except Exception as e:
                print(f"[ERR] news_id={art.id}: {e}")

    # ============================
    #   КЛАСТЕРИЗАЦИЯ
    # ============================
    def fetch_embeddings_with_summaries(self, hours: int = 24):
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        sql = text("""
            SELECT news_id, title, summary, embedding
            FROM news_embeddings
            WHERE created_at >= :cutoff
        """)
        rows = self.pg_db.execute(sql, {"cutoff": cutoff}).fetchall()
        if not rows:
            return [], np.array([]), []

        ids, vectors, articles_info = [], [], []
        for r in rows:
            ids.append(r.news_id)
            articles_info.append({
                "id": r.news_id,
                "title": r.title,
                "summary": r.summary
            })
            if isinstance(r.embedding, str):
                vec = np.fromstring(r.embedding.strip("[]"), sep=",")
            else:
                vec = np.array(r.embedding, dtype=float)
            vectors.append(vec)

        return ids, np.vstack(vectors), articles_info

    def validate_cluster_with_gpt(self, cluster_label: int, articles: List[Dict]) -> List[Dict]:
        """
        Отправляет один HDBSCAN-кластер в GPT,
        модель внутри может выделить несколько подтем.
        :return: список мини-кластеров [{"theme": ..., "article_ids": [...]}, ...]
        """
        if not articles or len(articles) < 3:
            return []

        cluster_data = [
            {
                "id": art["id"],
                "title": art["title"],
                "summary": art["summary"][:200] + "..." if len(art["summary"]) > 200 else art["summary"]
            }
            for art in articles
        ]

        prompt = f"""
Проанализируй список новостных статей и разбей их на смысловые кластеры по событиям.

Статьи:
{json.dumps(cluster_data, ensure_ascii=False, indent=2)}

Правила:
1. ...
5. Если подходящих групп нет — верни пустой JSON: {{}}

Формат ответа СТРОГО JSON:
{{
  "clusters": [
    {{
      "theme": "Официальный визит Токаева в Кыргызстан",
      "article_ids": [111, 112]
    }}
  ]
}}
"""

        try:
            response = self.gpt.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=600
            )
            result_text = response.choices[0].message.content.strip()

            print(f"===== GPT RAW RESPONSE (cluster {cluster_label}) =====")
            print(result_text)
            print("=====================================================")

            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].strip()

            try:
                result = json.loads(result_text)
            except json.JSONDecodeError as e:
                print(f"[WARN] JSON parse error (cluster {cluster_label}): {e}")
                return []

            clusters = []
            for cl in result.get("clusters", []):
                if len(cl.get("article_ids", [])) >= 3:
                    clusters.append({
                        "theme": cl["theme"],
                        "article_ids": cl["article_ids"]
                    })
            return clusters

        except Exception as e:
            print(f"[WARN] Ошибка валидации кластера {cluster_label} через GPT: {e}")
            return []

    def run_clustering(self, hours: int = 24, min_cluster_size: int = 3, min_samples: int = 2):
        news_ids, vectors, articles_info = self.fetch_embeddings_with_summaries(hours=hours)
        if len(news_ids) < min_cluster_size:
            print(f"⚠️ Недостаточно статей для кластеризации ({len(news_ids)} < {min_cluster_size})")
            return

        print(f"🔄 Начинаем кластеризацию {len(news_ids)} статей...")

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric="euclidean",
            cluster_selection_epsilon=0.3
        )
        labels = clusterer.fit_predict(vectors)

        cluster_articles, label_counts = {}, Counter(labels)
        for label in label_counts:
            if label == -1:
                continue
            cluster_mask = labels == label
            cluster_arts = [articles_info[i] for i, mask in enumerate(cluster_mask) if mask]
            if len(cluster_arts) >= min_cluster_size:
                cluster_articles[label] = cluster_arts

        noise_count = label_counts.get(-1, 0)
        print(f"📊 HDBSCAN результат: {len(cluster_articles)} кластеров для валидации, {noise_count} шумовых точек")

        if not cluster_articles:
            print("✅ Не найдено кластеров для валидации")
            return

        saved_clusters = 0
        for label, articles in cluster_articles.items():
            print(f"🤖 Отправляем кластер {label} на валидацию в GPT...")
            validated = self.validate_cluster_with_gpt(label, articles)

            if not validated:
                print(f"⚠️ Кластер {label} не дал валидных подтем")
                continue

            for idx, cluster_data in enumerate(validated):
                article_ids, theme = cluster_data["article_ids"], cluster_data["theme"]

                insert_cluster_sql = text("""
                    INSERT INTO news_clusters (label, theme)
                    VALUES (:label, :theme)
                    RETURNING cluster_id
                """)
                res = self.pg_db.execute(insert_cluster_sql, {
                    "label": f"gpt_validated_{datetime.now().strftime('%Y%m%d_%H%M')}_{label}_{idx}",
                    "theme": theme
                })
                cluster_id = res.scalar()

                for news_id in article_ids:
                    insert_item_sql = text("""
                        INSERT INTO news_cluster_items (cluster_id, news_id)
                        VALUES (:cluster_id, :news_id)
                    """)
                    self.pg_db.execute(insert_item_sql, {
                        "cluster_id": cluster_id,
                        "news_id": news_id
                    })

                print(f"✅ Сохранён кластер {cluster_id}: {len(article_ids)} статей")
                print(f"   📝 Тема: {theme}")
                saved_clusters += 1

        self.pg_db.commit()
        print(f"🎯 Итого сохранено {saved_clusters} GPT-валидированных кластеров")
