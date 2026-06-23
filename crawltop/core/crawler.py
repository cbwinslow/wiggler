from urllib.parse import urljoin

from crawltop.core.cleaner import ContentCleaner
from crawltop.core.http import HttpClientFactory
from crawltop.core.parser import HtmlParser


class CrawlResult:
    def __init__(self, url: str, status_code: int, title: str | None, text: str, links: list[str]):
        self.url = url
        self.status_code = status_code
        self.title = title
        self.text = text
        self.links = links


class CrawlerService:
    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self.parser = HtmlParser()
        self.cleaner = ContentCleaner()

    async def fetch_one(self, url: str) -> CrawlResult:
        async with HttpClientFactory.create(self.user_agent) as client:
            response = await client.get(url)
            response.raise_for_status()
            parsed = self.parser.parse(response.text, url)
            cleaned_text = self.cleaner.clean(response.text) or parsed.text
            normalized_links = [urljoin(url, href) for href in parsed.links]
            return CrawlResult(
                url=url,
                status_code=response.status_code,
                title=parsed.title,
                text=cleaned_text,
                links=normalized_links,
            )
