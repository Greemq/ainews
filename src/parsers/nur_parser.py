from src.parsers.base_parser import BaseParser
from typing import List, Dict, Optional
from bs4 import BeautifulSoup  # pip install beautifulsoup4 lxml
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import re

class NurParser(BaseParser):
    UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    _MONTHS_RU = {
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
        "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    }

    @staticmethod
    def _parse_iso_utc(s: str) -> Optional[datetime]:
        # Пример: 2025-08-15T11:15:00.000Z -> UTC
        if not s:
            return None
        try:
            if s.endswith("Z"):
                s = s.replace("Z", "+00:00")
            return datetime.fromisoformat(s).astimezone(timezone.utc)
        except Exception:
            return None

    @classmethod
    def _parse_ru_dt(cls, s: str) -> Optional[datetime]:
        """
        Поддерживает:
        - 'Сегодня, 16:15' / '16:15, Сегодня'
        - 'Вчера, 11:22'  / '11:22, Вчера'
        - '13 августа 2025, 18:25'
        Возвращает TZ-aware datetime в UTC.
        """
        if not s:
            return None

        tz_astana = timezone(timedelta(hours=5))
        now_local = datetime.now(tz=tz_astana)
        s_norm = s.strip().replace("\xa0", " ").lower().replace("ё", "е")

        # СЕГОДНЯ
        m = re.search(r"[сc]егодня[^0-9]*?(\d{1,2}):(\d{2})", s_norm) \
            or re.search(r"(\d{1,2}):(\d{2})\s*,\s*[сc]егодня", s_norm)
        if m:
            hh, mm = map(int, m.groups()[-2:])
            d = now_local.date()
            return datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz_astana).astimezone(timezone.utc)

        # ВЧЕРА
        m = re.search(r"вчера[^0-9]*?(\d{1,2}):(\d{2})", s_norm) \
            or re.search(r"(\d{1,2}):(\d{2})\s*,\s*вчера", s_norm)
        if m:
            hh, mm = map(int, m.groups()[-2:])
            d = (now_local - timedelta(days=1)).date()
            return datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz_astana).astimezone(timezone.utc)

        # ПОЛНЫЙ: '13 августа 2025, 18:25'
        m = re.search(r"(\d{1,2})\s+([а-я]+)\s+(\d{4}),\s*(\d{1,2}):(\d{2})", s_norm)
        if m:
            dd, mon, yyyy, hh, mm = m.groups()
            month = cls._MONTHS_RU.get(mon)
            if not month:
                return None
            dt_local = datetime(int(yyyy), month, int(dd), int(hh), int(mm), tzinfo=tz_astana)
            return dt_local.astimezone(timezone.utc)

        # альтернативный формат 'HH:MM, 15 августа 2025' (на всякий случай)
        m = re.search(r"(\d{1,2}):(\d{2}),\s*(\d{1,2})\s+([а-я]+)\s+(\d{4})", s_norm)
        if m:
            hh, mm, dd, mon, yyyy = m.groups()
            month = cls._MONTHS_RU.get(mon)
            if not month:
                return None
            dt_local = datetime(int(yyyy), month, int(dd), int(hh), int(mm), tzinfo=tz_astana)
            return dt_local.astimezone(timezone.utc)

        return None

    def parse(self) -> List[Dict]:
        html = self.fetch_html(self.source.url, as_bytes=True)
        soup = BeautifulSoup(html, "lxml")
        base = self.source.url

        items: List[Dict] = []

        # Карточки: <article class="article-card ..."> внутри — <a.article-card__title>, <time.article-card__date>
        for card in soup.select("article.article-card"):
            a = card.select_one("a.article-card__title")
            t = card.select_one("time.article-card__date")
            if not a:
                continue

            title = a.get_text(strip=True)
            url = urljoin(base, a.get("href", ""))

            published_at = None
            if t:
                iso = t.get("datetime")
                published_at = self._parse_iso_utc(iso) if iso else self._parse_ru_dt(t.get_text(strip=True))

            items.append({
                "title": title,
                "url": url,
                "published_at": published_at,  # UTC-aware или None
            })


        for item in items:
            if self.service.get_by_url(item["url"]) is not None:
                break

            html = self.fetch_html(item["url"], as_bytes=True)
            soup = BeautifulSoup(html, "lxml")
            parts = soup.select(".formatted-body__paragraph")
            content = "\n\n".join(el.get_text(" ", strip=True) for el in parts)
            item["content"] = content
            self.save_to_db(item)

