from __future__ import annotations

import asyncio
from urllib.parse import urljoin, urlparse

from crawltop.core.cleaner import ContentCleaner
from crawltop.core.http import HttpClientFactory
from crawltop.core.parser import HtmlParser


class CrawlResult:
    __slots__ = ("url", "status_code", "title", "text", "links", "error")

    def __init__(
        self,
        url: str,
        status_code: int | None = None,
        title: str | None = None,
        text: str = "",
        links: list[str] | None = None,
        error: str | None = None,
    ):
        self.url = url
        self.status_code = status_code
        self.title = title
        self.text = text
        self.links = links or []
        self.error = error

    @property
    def ok(self) -> bool:
        return self.error is None and (self.status_code or 0) < 400


class CrawlerService:
    def __init__(self, user_agent: str, max_concurrency: int = 10):
        self.user_agent = user_agent
        self.max_concurrency = max_concurrency
        self.parser = HtmlParser()
        self.cleaner = ContentCleaner()
        self._sem = asyncio.Semaphore(max_concurrency)

    async def fetch_one(self, url: str) -> CrawlResult:
        async with self._sem:
            try:
                async with HttpClientFactory.create(self.user_agent) as client:
                    response = await client.get(url)
                    html = response.text
                    parsed = self.parser.parse(html, url)
                    text = self.cleaner.clean(html) or parsed.text
                    links = [
                        urljoin(url, href)
                        for href in parsed.links
                        if href and not href.startswith(("#", "javascript:", "mailto:", "tel:"))
                    ]
                    return CrawlResult(
                        url=url,
                        status_code=response.status_code,
                        title=parsed.title,
                        text=text,
                        links=list(dict.fromkeys(links)),  # dedupe preserve order
                    )
            except Exception as exc:  # noqa: BLE001
                return CrawlResult(url=url, error=str(exc))

    @staticmethod
    def same_domain(base: str, url: str) -> bool:
        try:
            return urlparse(base).netloc == urlparse(url).netloc
        except Exception:  # noqa: BLE001
            return False
