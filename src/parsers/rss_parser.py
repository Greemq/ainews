from src.parsers.base_parser import BaseParser

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import calendar
import html
from src.models.source import Source
from src.services.news_service import NewsService

import feedparser
from dateutil import parser as dateparse


class RSSParser(BaseParser):
    UA = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def __init__(self, source: Source, service: NewsService):
        super().__init__(source, service)

    def parse(self):
        """
        Парсер RSS для Tengrinews (и совместимых фидов).
        На выход: [{title, content(html), url, published_at(UTC)}]
        """
        d = feedparser.parse(
            self.source.url,
            agent=self.UA,
            request_headers={
                "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"
            },
        )

        if getattr(d, "bozo", 0):
            logging.warning("feedparser bozo: %s", getattr(d, "bozo_exception", None))


        for e in d.entries[:20]:
            row = self._entry_to_row(e)
            if self.service.get_by_url(row["url"]) is not None:
                continue
            self.save_to_db(row)



    def _entry_to_row(self, e) -> Optional[Dict]:
        title = (e.get("title") or "").strip()
        url = (e.get("link") or "").strip()
        if not title or not url:
            return None

        # content:encoded -> entry.content[0].value
        content_html = ""
        if hasattr(e, "content") and e.content:
            content_html = e.content[0].get("value") or ""
        elif hasattr(e, "summary_detail") and e.summary_detail:
            content_html = e.summary_detail.get("value") or ""
        else:
            content_html = e.get("summary") or ""

        # нормализуем HTML-entities (часто в RSS)
        content_html = html.unescape(content_html).strip()

        # published_at → UTC
        published_at = self._to_datetime_utc(e)

        return {
            "title": title,
            "content": content_html,
            "url": url,
            "published_at": published_at,
        }

    @staticmethod
    def _to_datetime_utc(e) -> Optional[datetime]:
        """
        Преобразует published_/updated_ в tz-aware UTC.
        Предпочтение: published_parsed → updated_parsed → published → updated.
        """
        tm = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        if tm:
            # struct_time (обычно уже нормализован feedparser’ом)
            return datetime.fromtimestamp(calendar.timegm(tm), tz=timezone.utc)

        txt = e.get("published") or e.get("updated")
        if txt:
            dt = dateparse.parse(txt)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        return None
