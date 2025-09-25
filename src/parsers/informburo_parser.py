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


class InformburoParser(BaseParser):
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
        if not s:
            return None

        tz_astana = timezone(timedelta(hours=5))
        now_local = datetime.now(tz_astana)
        s_norm = s.strip().replace("\xa0", " ").lower().replace("ё", "е")

        # --- СЕГОДНЯ ---
        # вариант: "сегодня, 13:51"
        m = re.search(r"[сc]егодня[^0-9]*?(\d{1,2}):(\d{2})", s_norm)
        # вариант: "13:51, сегодня"
        if not m:
            m = re.search(r"(\d{1,2}):(\d{2})\s*,\s*[сc]егодня", s_norm)
        if m:
            hh, mm = map(int, m.groups()[-2:])  # последние 2 группы — это HH, MM
            d = now_local.date()
            dt_local = datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz_astana)
            return dt_local.astimezone(timezone.utc)

        # --- Полный формат: "HH:MM, 15 августа 2025" ---
        m = re.search(r"(\d{1,2}):(\d{2}),\s*(\d{1,2})\s+([а-я]+)\s+(\d{4})", s_norm)
        if not m:
            return None
        hh, mm, dd, mon, yyyy = m.groups()
        month = cls._MONTHS_RU.get(mon) or next((v for k, v in cls._MONTHS_RU.items() if mon.startswith(k[:4])), None)
        if not month:
            return None
        dt_local = datetime(int(yyyy), month, int(dd), int(hh), int(mm), tzinfo=tz_astana)
        return dt_local.astimezone(timezone.utc)

    def parse(self) -> List[Dict]:
        html = self.fetch_html(self.source.url)
        soup = BeautifulSoup(html, "lxml")
        base = self.source.url

        items: List[Dict] = []
        current_date_heading = None
        # каждая карточка — ссылка-обёртка
        for li in soup.select('.uk-nav.uk-nav-default > li'):
            # 1) Заголовок даты
            dateheading = li.select_one('.date-heading') or li.find('h2', class_='date-heading')
            if dateheading:
                current_date_heading = dateheading.get_text(strip=True)
                continue

            # 2) Берём <a> именно в текстовой колонке, а не у миниатюры
            a_text = li.select_one('.uk-width-expand > a')
            if not a_text:
                # fallback: второй <a> в li (если структура неожиданно другая)
                anchors = li.select('a')
                a_text = anchors[1] if len(anchors) > 1 else None
            if not a_text:
                continue

            # 3) Чистый заголовок: только прямой текстовый узел якоря
            title = (a_text.find(text=True, recursive=False) or '').strip()
            if not title:  # на случай, если вдруг вернулся пустой узел
                title = a_text.get_text(' ', strip=True)

            url = urljoin(base, a_text.get('href'))
            time_el = li.select_one('time.article-time')
            time_txt = time_el.get_text(strip=True) if time_el else ''

            # 4) Нормализуем время для парсера
            if current_date_heading:
                if current_date_heading.lower() == 'сегодня':
                    normalized_time = f'{time_txt}, сегодня'
                elif re.search(r'\d{4}', current_date_heading):
                    normalized_time = f'{time_txt}, {current_date_heading}'
                else:
                    normalized_time = f'{time_txt}, {current_date_heading} {datetime.now().year}'
            else:
                normalized_time = time_txt or ''

            published_at = self._parse_ru_dt(normalized_time) if time_txt else None

            items.append({
                'title': title,
                'url': url,
                'published_at': published_at,
            })
        # return items
    
        for item in items:
            if self.service.get_by_url(item["url"]) is not None:
                break

            html = self.fetch_html(item["url"])
            soup = BeautifulSoup(html, "lxml")
            parts = soup.select(".article-excerpt, .article > :not(.read-more)")
            content = "\n\n".join(el.get_text(" ", strip=True) for el in parts)
            item["content"] = content
            self.save_to_db(item)