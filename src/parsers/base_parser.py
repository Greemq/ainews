from abc import ABC, abstractmethod
from src.models.source import Source
from src.services.news_service import NewsService
import requests
from typing import Optional, Dict
import time



class BaseParser(ABC):
     # Статусы, при которых имеет смысл повторить запрос
    _RETRY_STATUS = {429, 500, 502, 503, 504}

    # Базовые заголовки. Если в наследнике есть атрибут UA — он будет подставлен.
    _DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-KZ,ru;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    def __init__(self, source: Source, service: NewsService):
        self.source = source
        self.service = service

         # Сессия для переиспользования TCP-соединений
        self._session = requests.Session()
        self._session.headers.update(self._DEFAULT_HEADERS)

        # Если у наследника определён UA (как в RSSParser.UA) — подставим его
        if hasattr(self, "UA") and isinstance(getattr(self, "UA"), str):
            self._session.headers["User-Agent"] = getattr(self, "UA")
    
    @abstractmethod
    def parse(self):
        """Метод для парсинга новостей с портала."""
        pass
    
    def save_to_db(self, news_data):
        """Сохранение данных в базу."""
        from src.models.news import News
        news = News(
            title=news_data["title"],
            content=news_data.get("content"),
            url=news_data["url"],
            published_at=news_data.get("published_at"),
            source_id=self.source.id
        )
        self.service.save(news)

    # ===== Новый метод =====
    def fetch_html(
        self,
        url: str,
        as_bytes: bool = False,
        *,
        timeout: float = 15.0,
        retries: int = 2,
        backoff: float = 0.6,
        extra_headers: Optional[Dict[str, str]] = None,
        allow_404: bool = False,
    ) -> str:
        """
        Забирает HTML-документ по URL и возвращает как строку.
        - timeout: таймаут одного запроса (сек)
        - retries: число повторных попыток при временных ошибках/429/5xx
        - backoff: экспоненциальная задержка между повторами (сек)
        - extra_headers: доп. заголовки для конкретного запроса
        - allow_404: если True, при 404 вернёт пустую строку вместо исключения
        """
        headers = dict(self._session.headers)
        if extra_headers:
            headers.update(extra_headers)

        last_exc: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                resp = self._session.get(url, headers=headers, timeout=timeout, allow_redirects=True)

                if resp.status_code == 404 and allow_404:
                    return ""

                # Повтор при временных статусах
                if resp.status_code in self._RETRY_STATUS and attempt < retries:
                    time.sleep(backoff * (2 ** attempt))
                    continue

                resp = self._session.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                resp.raise_for_status()

                if as_bytes:
                    return resp.content

                # Корректируем кодировку, если сервер её не указал
                if not resp.encoding:
                    resp.encoding = resp.apparent_encoding or "utf-8"

                return resp.text

            except requests.RequestException as e:
                last_exc = e
                if attempt < retries:
                    time.sleep(backoff * (2 ** attempt))
                    continue
                # На последней попытке — пробрасываем понятную ошибку
                raise RuntimeError(f"Failed to fetch HTML from {url}: {e}") from e