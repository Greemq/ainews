from src.parsers.base_parser import BaseParser
from typing import List, Dict, Optional
from bs4 import BeautifulSoup  # pip install beautifulsoup4 lxml
from urllib.parse import urljoin
from datetime import datetime, timezone, timedelta
import re

try:
    from zoneinfo import ZoneInfo  # py3.9+
except ImportError:
    ZoneInfo = None


class KazinformParser(BaseParser):
    UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    _MONTHS_RU = {
        "января": 1, "январь": 1,
        "февраля": 2, "февраль": 2,
        "марта": 3,  "март": 3,
        "апреля": 4, "апрель": 4,
        "мая": 5,    "май": 5,
        "июня": 6,   "июнь": 6,
        "июля": 7,   "июль": 7,
        "августа": 8,"август": 8,
        "сентября": 9,"сентябрь": 9,
        "октября": 10,"октябрь": 10,
        "ноября": 11,"ноябрь": 11,
        "декабря": 12,"декабрь": 12,
    }

    @classmethod
    def _parse_ru_dt(cls, s: str) -> Optional[datetime]:
        """
        '13:51, 15 Август 2025' или '13:51, 15 августа 2025' (Asia/Almaty, UTC+5) -> UTC datetime
        """
        if not s:
            return None
        s = s.strip().replace("\xa0", " ")
        m = re.search(r"(\d{1,2}):(\d{2}),\s*(\d{1,2})\s+([А-Яа-яЁё]+)\s+(\d{4})", s)
        if not m:
            return None

        hh, mm, dd, mon, yyyy = m.groups()
        mon = mon.lower().replace("ё", "е")
        month = cls._MONTHS_RU.get(mon)
        if not month:
            return None

        # локальное время Астаны (UTC+5)
        tz_astana = timezone(timedelta(hours=5))
        dt_local = datetime(int(yyyy), month, int(dd), int(hh), int(mm), tzinfo=tz_astana)

        # конвертируем в UTC
        return dt_local.astimezone(timezone.utc)

    def parse(self) -> List[Dict]:
        html = self.fetch_html(self.source.url)
        soup = BeautifulSoup(html, "lxml")
        base = self.source.url

        items: List[Dict] = []
        # каждая карточка — ссылка-обёртка
        for a in soup.select(".allNewsCard a[href]"):
            title_el = a.select_one(".allNewsCard_title")
            time_el = a.select_one(".allNewsCard_time")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            url = urljoin(base, a["href"])
            published_at = self._parse_ru_dt(time_el.get_text(strip=True)) if time_el else None

            items.append({
                "title": title,
                "url": url,
                "published_at": published_at,  # UTC-aware или None
            })

        for item in items:
            if self.service.get_by_url(item["url"]) is not None:
                break

            html = self.fetch_html(item["url"])
            soup = BeautifulSoup(html, "lxml")
            parts = soup.select(".article__description, .article__body-text")
            content = "\n\n".join(el.get_text(" ", strip=True) for el in parts)
            item["content"] = content
            self.save_to_db(item)
